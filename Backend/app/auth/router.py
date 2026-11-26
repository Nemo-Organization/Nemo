from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.schemas import Me
from app.auth import service
from app.auth.dependencies import ActorToken, DbSession, current_actor
from app.auth.principal import Principal

router = APIRouter(tags=["Customer"])


@router.get(
    "/me",
    operation_id="getMe",
    response_model=Me,
    description="Current authenticated actor and owned accounts. Re-derives the actor CSRF "
    "token from the HttpOnly session cookie without changing session state.",
)
def get_me(
    principal: Annotated[Principal, Depends(current_actor)],
    token: ActorToken,
    session: DbSession,
) -> Me:
    if token is None:
        raise service.session_expired()
    return service.get_me(session, principal, token)
