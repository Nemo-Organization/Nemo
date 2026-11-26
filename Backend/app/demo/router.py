from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request, Response

from app.api.pagination import PageParams
from app.api.schemas import (
    Bootstrap,
    CreateDemo,
    Me,
    OrderList,
    RecipientList,
    Refund,
    SelectActor,
)
from app.auth.dependencies import (
    CSRF_OPENAPI,
    ORIGIN_NOTE,
    CustomerReader,
    DbSession,
    controller_mutation,
    require_origin,
    set_session_cookie,
    settings_of,
)
from app.auth.principal import DemoPrincipal
from app.auth.service import ACTOR_COOKIE, CONTROLLER_COOKIE
from app.demo import queries, refunds, service

router = APIRouter(tags=["Demo"])
# Customer reads of seeded fixtures; the contract tags these operations "Customer".
customer_router = APIRouter(tags=["Customer"])
Pagination = Annotated[PageParams, Query()]
Controller = Annotated[DemoPrincipal, Depends(controller_mutation)]
RefundId = Annotated[UUID, Path(alias="id")]


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


@router.post(
    "/demo/refunds/{id}/settle",
    operation_id="settleDemoRefund",
    response_model=Refund,
    openapi_extra=CSRF_OPENAPI,
    description="Settle a seeded APPROVED refund once, including while outgoing funds are held. "
    "Repeat returns stored SETTLED result. Demo-controller cookie and controller CSRF only; an "
    "actor credential cannot settle. Credits the account once (REFUND_CREDIT): the balance "
    "rises and reservations are unchanged. Another sandbox's or an unknown refund is 404; a "
    f"refund inconsistent with its order is 409 STATE_CONFLICT. {ORIGIN_NOTE}",
)
def settle_demo_refund(controller: Controller, refund_id: RefundId, session: DbSession) -> Refund:
    return refunds.settle_refund(session, controller, refund_id)


@customer_router.get(
    "/recipients",
    operation_id="listRecipients",
    response_model=RecipientList,
    description="Seeded recipients in this sandbox, with masked identifiers. CUSTOMER only. "
    "Ordered by display_name then ID; the caller's own wallet is never listed.",
)
def list_recipients(
    principal: CustomerReader, page: Pagination, session: DbSession
) -> RecipientList:
    return queries.list_recipients(session, principal, page)


@customer_router.get(
    "/orders",
    operation_id="listOrders",
    response_model=OrderList,
    description="Customer-owned order and refund facts only. CUSTOMER only. An unknown fee is "
    "null with null provenance, distinct from a verified zero fee.",
)
def list_orders(principal: CustomerReader, page: Pagination, session: DbSession) -> OrderList:
    return queries.list_orders(session, principal, page)
