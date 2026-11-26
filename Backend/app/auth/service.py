"""Hashed demo sessions, identity resolution and CSRF binding.

Session cookies carry 256-bit opaque random tokens. The database stores only SHA-256 hashes of
the token and of its CSRF token. The CSRF token is HMAC-SHA256 keyed by the session token over
a constant that differs for actor and controller credentials, so `/me` can re-derive it from
the HttpOnly cookie without storing plaintext or rotating state on GET, and one credential's
CSRF token never verifies against the other credential.

Validity is checked against database time. Helpers here only flush; the calling top-level
service commits.
"""

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, cast
from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.orm import Session

from app import models
from app.api import schemas
from app.auth.principal import DemoPrincipal, Principal, Role
from app.errors import ApplicationError

SessionKind = Literal["ACTOR", "DEMO_CONTROL"]

ACTOR_COOKIE = "guardian_session"
CONTROLLER_COOKIE = "guardian_demo"
CSRF_HEADER = "X-CSRF-Token"
MAX_CREDENTIAL_LENGTH = 256
_TOKEN_BYTES = 32
_CSRF_DOMAINS: dict[SessionKind, bytes] = {
    "ACTOR": b"guardian/csrf/v1/actor-session",
    "DEMO_CONTROL": b"guardian/csrf/v1/demo-controller",
}


@dataclass(frozen=True, slots=True)
class IssuedSession:
    """Plaintext credentials returned once to the HTTP layer; never persisted or logged."""

    token: str
    csrf_token: str
    max_age: int


def hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def derive_csrf(session_token: str, kind: SessionKind = "ACTOR") -> str:
    """Deterministic CSRF token bound to one session token and credential kind."""
    return hmac.new(session_token.encode("utf-8"), _CSRF_DOMAINS[kind], hashlib.sha256).hexdigest()


def database_now(session: Session) -> datetime:
    return session.execute(select(func.now())).scalar_one()


def session_expired() -> ApplicationError:
    return ApplicationError(
        401, "SESSION_EXPIRED", "Session is missing or expired. Start a new demo session."
    )


def csrf_failed() -> ApplicationError:
    return ApplicationError(403, "CSRF_FAILED", "CSRF token is missing or invalid.")


def issue_session(
    session: Session,
    *,
    sandbox_id: UUID,
    kind: SessionKind,
    actor_id: UUID | None,
    expires_at: datetime,
    now: datetime,
) -> IssuedSession:
    token = secrets.token_urlsafe(_TOKEN_BYTES)
    csrf_token = derive_csrf(token, kind)
    session.add(
        models.AuthSession(
            sandbox_id=sandbox_id,
            actor_id=actor_id,
            kind=kind,
            token_hash=hash_secret(token),
            csrf_hash=hash_secret(csrf_token),
            expires_at=expires_at,
        )
    )
    session.flush()
    max_age = max(0, int((expires_at - now).total_seconds()))
    return IssuedSession(token=token, csrf_token=csrf_token, max_age=max_age)


def revoke_actor_session(session: Session, *, sandbox_id: UUID, token: str | None) -> None:
    """Revoke the presented actor session if it belongs to this sandbox; otherwise no-op."""
    if not token or len(token) > MAX_CREDENTIAL_LENGTH:
        return
    session.execute(
        update(models.AuthSession)
        .where(
            models.AuthSession.token_hash == hash_secret(token),
            models.AuthSession.sandbox_id == sandbox_id,
            models.AuthSession.kind == "ACTOR",
            models.AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=func.now())
    )


def _authenticate(
    session: Session, cookie: str | None, kind: SessionKind
) -> tuple[models.AuthSession, models.Actor | None]:
    if not cookie or len(cookie) > MAX_CREDENTIAL_LENGTH:
        raise session_expired()
    now = func.now()
    statement = (
        select(models.AuthSession, models.Actor)
        .join(models.Sandbox, models.Sandbox.id == models.AuthSession.sandbox_id)
        .outerjoin(
            models.Actor,
            and_(
                models.Actor.sandbox_id == models.AuthSession.sandbox_id,
                models.Actor.id == models.AuthSession.actor_id,
            ),
        )
        .where(
            models.AuthSession.token_hash == hash_secret(cookie),
            models.AuthSession.kind == kind,
            models.AuthSession.revoked_at.is_(None),
            models.AuthSession.expires_at > now,
            models.Sandbox.expires_at > now,
        )
    )
    row = session.execute(statement).one_or_none()
    if row is None:
        raise session_expired()
    credential, actor = row
    if (kind == "ACTOR") != (actor is not None):
        raise session_expired()
    return credential, actor


def _verify_csrf(credential: models.AuthSession, presented: str | None) -> None:
    if not presented or len(presented) > MAX_CREDENTIAL_LENGTH:
        raise csrf_failed()
    if not hmac.compare_digest(hash_secret(presented), credential.csrf_hash):
        raise csrf_failed()


def _principal(actor: models.Actor | None, request_id: str) -> Principal:
    if actor is None:
        raise session_expired()
    return Principal(
        sandbox_id=actor.sandbox_id,
        actor_id=actor.id,
        role=cast(Role, actor.role),
        request_id=request_id,
    )


def resolve_actor(session: Session, cookie: str | None, *, request_id: str) -> Principal:
    """Authenticate an actor cookie for a read. Raises 401 SESSION_EXPIRED."""
    _, actor = _authenticate(session, cookie, "ACTOR")
    return _principal(actor, request_id)


def resolve_controller(session: Session, cookie: str | None, *, request_id: str) -> DemoPrincipal:
    """Authenticate a demo-controller cookie. Raises 401 SESSION_EXPIRED."""
    credential, _ = _authenticate(session, cookie, "DEMO_CONTROL")
    return DemoPrincipal(sandbox_id=credential.sandbox_id, request_id=request_id)


def authorize_actor_mutation(
    session: Session, cookie: str | None, csrf_token: str | None, *, request_id: str
) -> Principal:
    """Actor cookie plus that session's actor CSRF token (403 CSRF_FAILED otherwise)."""
    credential, actor = _authenticate(session, cookie, "ACTOR")
    _verify_csrf(credential, csrf_token)
    return _principal(actor, request_id)


def authorize_controller_mutation(
    session: Session, cookie: str | None, csrf_token: str | None, *, request_id: str
) -> DemoPrincipal:
    """Controller cookie plus the controller CSRF token (403 CSRF_FAILED otherwise)."""
    credential, _ = _authenticate(session, cookie, "DEMO_CONTROL")
    _verify_csrf(credential, csrf_token)
    return DemoPrincipal(sandbox_id=credential.sandbox_id, request_id=request_id)


# Serialization shared by bootstrap, actor selection and /me.


def mask_identifier(identifier: str) -> str:
    """Keep only the last four characters; the prefix length is not revealed."""
    return f"****{identifier[-4:]}" if len(identifier) > 4 else "****"


def actor_view(actor: models.Actor) -> schemas.Actor:
    return schemas.Actor(id=actor.id, role=cast(Role, actor.role), display_name=actor.display_name)


def account_view(account: models.Account) -> schemas.Account:
    return schemas.Account(
        id=account.id,
        display_name=account.display_name,
        bank_code=account.bank_code,
        masked_identifier=mask_identifier(account.account_identifier),
        balance_vnd=account.balance_vnd,
        reserved_vnd=account.reserved_vnd,
        available_vnd=account.balance_vnd - account.reserved_vnd,
    )


def build_me(session: Session, actor: models.Actor, actor_csrf_token: str) -> schemas.Me:
    accounts = session.scalars(
        select(models.Account)
        .where(
            models.Account.sandbox_id == actor.sandbox_id,
            models.Account.owner_actor_id == actor.id,
        )
        .order_by(models.Account.created_at, models.Account.id)
    ).all()
    return schemas.Me(
        sandbox_id=actor.sandbox_id,
        actor=actor_view(actor),
        accounts=[account_view(account) for account in accounts],
        actor_csrf_token=actor_csrf_token,
    )


def get_me(session: Session, principal: Principal, session_token: str) -> schemas.Me:
    """Current actor and owned accounts. Read-only: re-derives the actor CSRF token."""
    actor = session.get(models.Actor, principal.actor_id)
    if actor is None or actor.sandbox_id != principal.sandbox_id:
        raise session_expired()
    return build_me(session, actor, derive_csrf(session_token, "ACTOR"))
