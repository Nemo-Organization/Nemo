from datetime import timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Query, Request, Response

from app.api.pagination import PageParams
from app.api.schemas import CreateTransfer, Transfer, TransferList
from app.auth.dependencies import (
    CSRF_OPENAPI,
    ORIGIN_NOTE,
    CustomerReader,
    CustomerWriter,
    DbSession,
    settings_of,
)
from app.transfers import service

router = APIRouter(tags=["Customer"])
Pagination = Annotated[PageParams, Query()]
TransferId = Annotated[UUID, Path(alias="id")]


@router.get(
    "/transfers",
    operation_id="listTransfers",
    response_model=TransferList,
    description="Transfers sent by the authenticated customer. CUSTOMER only. Newest "
    "created_at first, then ID descending; total counts the caller's transfers before paging.",
)
def list_transfers(principal: CustomerReader, page: Pagination, session: DbSession) -> TransferList:
    return service.list_transfers(session, principal, page)


@router.post(
    "/transfers",
    operation_id="createTransfer",
    status_code=201,
    response_model=Transfer,
    responses={200: {"model": Transfer, "description": "Exact idempotent replay"}},
    openapi_extra=CSRF_OPENAPI,
    description="Immutable draft with a 30-minute lifetime. Does not reserve money. UUID client "
    "key replays identical input with 200; changed data returns 409. The sender must be the "
    "caller's own wallet and the recipient a seeded recipient of this sandbox; otherwise 404. "
    f"{ORIGIN_NOTE}",
)
def create_transfer(
    principal: CustomerWriter,
    body: CreateTransfer,
    request: Request,
    response: Response,
    session: DbSession,
) -> Transfer:
    lifetime = timedelta(seconds=settings_of(request).draft_ttl_seconds)
    transfer = service.create_transfer(session, principal, body, draft_lifetime=lifetime)
    if transfer.replayed:
        response.status_code = 200
    return transfer


@router.get(
    "/transfers/{id}",
    operation_id="getTransfer",
    response_model=Transfer,
    description="Customer-owned transfer with its latest assessment. CUSTOMER only; another "
    "customer's or sandbox's transfer is 404.",
)
def get_transfer(
    principal: CustomerReader, transfer_id: TransferId, session: DbSession
) -> Transfer:
    return service.get_transfer(session, principal, transfer_id)
