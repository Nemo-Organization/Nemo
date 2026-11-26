"""Top-level demo-controller services. Each completes its own transaction with one commit."""

from dataclasses import dataclass
from datetime import UTC, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.api.schemas import Bootstrap, Me, Scenario
from app.auth.principal import DemoPrincipal
from app.auth.service import (
    IssuedSession,
    actor_view,
    build_me,
    database_now,
    issue_session,
    revoke_actor_session,
)
from app.demo import fixtures
from app.errors import ApplicationError
from app.settings import Settings
from app.transfers.expiry import reconcile_actor_accounts

DEFAULT_LIFETIME = timedelta(hours=24)


@dataclass(frozen=True, slots=True)
class Lifetimes:
    sandbox: timedelta = DEFAULT_LIFETIME
    session: timedelta = DEFAULT_LIFETIME

    @classmethod
    def from_settings(cls, settings: Settings) -> "Lifetimes":
        return cls(
            sandbox=timedelta(seconds=settings.sandbox_ttl_seconds),
            session=timedelta(seconds=settings.session_ttl_seconds),
        )


DEFAULT_LIFETIMES = Lifetimes()


@dataclass(frozen=True, slots=True)
class DemoCreated:
    """Bootstrap body plus the two plaintext cookies the router sets exactly once."""

    bootstrap: Bootstrap
    controller: IssuedSession
    actor: IssuedSession


@dataclass(frozen=True, slots=True)
class ActorSelected:
    me: Me
    actor: IssuedSession


def create_sandbox(
    session: Session, scenario: Scenario, *, lifetimes: Lifetimes = DEFAULT_LIFETIMES
) -> DemoCreated:
    """Seed a fresh isolated sandbox, a controller session and an initial Linh session."""
    now = database_now(session)
    expires_at = now + lifetimes.sandbox
    seeded = fixtures.seed_sandbox(session, scenario, created_at=now, expires_at=expires_at)
    credential_expiry = min(now + lifetimes.session, expires_at)
    initial = seeded.actors[fixtures.INITIAL_ACTOR]
    controller = issue_session(
        session,
        sandbox_id=seeded.id,
        kind="DEMO_CONTROL",
        actor_id=None,
        expires_at=credential_expiry,
        now=now,
    )
    actor = issue_session(
        session,
        sandbox_id=seeded.id,
        kind="ACTOR",
        actor_id=initial.id,
        expires_at=credential_expiry,
        now=now,
    )
    actors = sorted(seeded.actors.values(), key=lambda a: (a.role, a.display_name, a.id))
    bootstrap = Bootstrap(
        sandbox_id=seeded.id,
        scenario=scenario,
        expires_at=expires_at.astimezone(UTC),
        actors=[actor_view(a) for a in actors],
        current_actor=actor_view(initial),
        controller_csrf_token=controller.csrf_token,
        actor_csrf_token=actor.csrf_token,
    )
    session.commit()
    return DemoCreated(bootstrap=bootstrap, controller=controller, actor=actor)


def select_actor(
    session: Session,
    controller: DemoPrincipal,
    actor_id: UUID,
    *,
    previous_actor_token: str | None = None,
    session_lifetime: timedelta = DEFAULT_LIFETIME,
) -> ActorSelected:
    """Issue a new actor session in the controller's sandbox and revoke the presented one."""
    actor = session.scalar(
        select(models.Actor).where(
            models.Actor.sandbox_id == controller.sandbox_id, models.Actor.id == actor_id
        )
    )
    if actor is None:
        raise ApplicationError(404, "NOT_FOUND", "Resource not found.")
    # The returned Me shows balances, so passed deadlines are reconciled first (same commit).
    reconcile_actor_accounts(
        session, controller.sandbox_id, actor.id, request_id=controller.request_id
    )
    now, sandbox_expires_at = session.execute(
        select(func.now(), models.Sandbox.expires_at).where(
            models.Sandbox.id == controller.sandbox_id
        )
    ).one()
    revoke_actor_session(session, sandbox_id=controller.sandbox_id, token=previous_actor_token)
    issued = issue_session(
        session,
        sandbox_id=controller.sandbox_id,
        kind="ACTOR",
        actor_id=actor.id,
        expires_at=min(now + session_lifetime, sandbox_expires_at),
        now=now,
    )
    me = build_me(session, actor, issued.csrf_token)
    session.commit()
    return ActorSelected(me=me, actor=issued)
