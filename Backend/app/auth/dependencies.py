"""FastAPI dependencies for Origin, cookie, CSRF and role checks, plus session-cookie writing.

Check order for mutations: exact Origin (403 ORIGIN_DENIED), then the endpoint's own credential
(401 SESSION_EXPIRED), then that credential's CSRF token (403 CSRF_FAILED). Role checks run after
authentication (403 FORBIDDEN) and before the endpoint's query parameters are validated. Role,
actor and sandbox headers sent by clients are never read.
"""

from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends, Request, Response, Security
from fastapi.security import APIKeyCookie
from sqlalchemy.orm import Session

from app.auth import service
from app.auth.principal import DemoPrincipal, Principal, Role
from app.db import get_session
from app.errors import ApplicationError
from app.settings import Settings

# Scheme names and fields equal the contract's securitySchemes (actorCookie, demoCookie).
actor_cookie = APIKeyCookie(name=service.ACTOR_COOKIE, scheme_name="actorCookie", auto_error=False)
controller_cookie = APIKeyCookie(
    name=service.CONTROLLER_COOKIE, scheme_name="demoCookie", auto_error=False
)

DbSession = Annotated[Session, Depends(get_session)]
ActorToken = Annotated[str | None, Security(actor_cookie)]
ControllerToken = Annotated[str | None, Security(controller_cookie)]

ORIGIN_NOTE = (
    "The Origin header must exactly equal the configured PUBLIC_APP_ORIGIN, including for manual "
    "or Swagger requests."
)
# The CSRF header is read directly so that a missing token is a 403 CSRF_FAILED, not a 422.
# This documents it as the contract's required header parameter.
CSRF_OPENAPI: dict[str, Any] = {
    "parameters": [
        {
            "name": service.CSRF_HEADER,
            "in": "header",
            "required": True,
            "schema": {"type": "string"},
            "description": "Use controller or actor CSRF matching this endpoint credential. "
            "Origin must match the configured browser origin.",
        }
    ]
}


def settings_of(request: Request) -> Settings:
    return request.app.state.settings


def require_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin is None or origin != settings_of(request).public_app_origin:
        raise ApplicationError(403, "ORIGIN_DENIED", "Request origin is not allowed.")


Origin = Annotated[None, Depends(require_origin)]


def current_actor(request: Request, session: DbSession, token: ActorToken) -> Principal:
    """Actor identity for reads (no Origin/CSRF requirement)."""
    return service.resolve_actor(session, token, request_id=request.state.request_id)


def actor_mutation(
    _origin: Origin, request: Request, session: DbSession, token: ActorToken
) -> Principal:
    """Actor identity for state-changing requests: Origin and actor CSRF required."""
    return service.authorize_actor_mutation(
        session,
        token,
        request.headers.get(service.CSRF_HEADER),
        request_id=request.state.request_id,
    )


def require_role(
    role: Role, *, via: Callable[..., Principal] = current_actor
) -> Callable[..., Principal]:
    """Dependency yielding the principal authenticated by `via`, which must hold `role`.

    `via` is `current_actor` for reads or `actor_mutation` for writes, so a missing session is
    still 401 and an authenticated caller with the other role is 403 FORBIDDEN.
    """

    def dependency(principal: Annotated[Principal, Depends(via)]) -> Principal:
        if principal.role != role:
            raise service.role_forbidden()
        return principal

    return dependency


CustomerReader = Annotated[Principal, Depends(require_role("CUSTOMER"))]
CustomerWriter = Annotated[Principal, Depends(require_role("CUSTOMER", via=actor_mutation))]


def controller_mutation(
    _origin: Origin, request: Request, session: DbSession, token: ControllerToken
) -> DemoPrincipal:
    """Demo-controller identity: Origin and controller CSRF required."""
    return service.authorize_controller_mutation(
        session,
        token,
        request.headers.get(service.CSRF_HEADER),
        request_id=request.state.request_id,
    )


def set_session_cookie(
    response: Response, name: str, issued: service.IssuedSession, settings: Settings
) -> None:
    response.set_cookie(
        name,
        issued.token,
        max_age=issued.max_age,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
