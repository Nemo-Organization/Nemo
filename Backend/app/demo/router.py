from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from app.api.schemas import Bootstrap, CreateDemo, Me, SelectActor
from app.auth.dependencies import (
    CSRF_OPENAPI,
    ORIGIN_NOTE,
    DbSession,
    controller_mutation,
    require_origin,
    set_session_cookie,
    settings_of,
)
from app.auth.principal import DemoPrincipal
from app.auth.service import ACTOR_COOKIE, CONTROLLER_COOKIE
from app.demo import service

router = APIRouter(tags=["Demo"])


@router.post(
    "/demo/sessions",
    operation_id="createDemo",
    status_code=201,
    response_model=Bootstrap,
    dependencies=[Depends(require_origin)],
    description="Creates fresh fixtures and sets guardian_demo and guardian_session cookies. "
    f"No CSRF token exists yet. {ORIGIN_NOTE} Fresh create is not a replay.",
)
def create_demo(
    body: CreateDemo, request: Request, response: Response, session: DbSession
) -> Bootstrap:
    settings = settings_of(request)
    created = service.create_sandbox(
        session, body.scenario, lifetimes=service.Lifetimes.from_settings(settings)
    )
    set_session_cookie(response, CONTROLLER_COOKIE, created.controller, settings)
    set_session_cookie(response, ACTOR_COOKIE, created.actor, settings)
    return created.bootstrap


@router.post(
    "/demo/actors/select",
    operation_id="selectActor",
    response_model=Me,
    openapi_extra=CSRF_OPENAPI,
    description="Select a seeded actor in the authenticated controller sandbox. Replaces and "
    f"revokes the presented actor cookie and returns the new actor CSRF token. {ORIGIN_NOTE}",
)
def select_demo_actor(
    controller: Annotated[DemoPrincipal, Depends(controller_mutation)],
    body: SelectActor,
    request: Request,
    response: Response,
    session: DbSession,
) -> Me:
    settings = settings_of(request)
    selected = service.select_actor(
        session,
        controller,
        body.actor_id,
        previous_actor_token=request.cookies.get(ACTOR_COOKIE),
        session_lifetime=service.Lifetimes.from_settings(settings).session,
    )
    set_session_cookie(response, ACTOR_COOKIE, selected.actor, settings)
    return selected.me
