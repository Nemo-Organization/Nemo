from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Query

from app.api.pagination import PageParams
from app.api.schemas import ReviewHold, Transfer, TransferList
from app.auth.dependencies import (
    CSRF_OPENAPI,
    ORIGIN_NOTE,
    DbSession,
    OperatorReader,
    OperatorWriter,
)
from app.operations import holds

router = APIRouter(tags=["Operations"])
Pagination = Annotated[PageParams, Query()]
TransferId = Annotated[UUID, Path(alias="id")]


@router.get(
    "/ops/holds",
    operation_id="listHolds",
    response_model=TransferList,
    description="OPERATOR only. Current RISK_HELD and READY transfers of this sandbox, after "
    "expiry reconciliation: passed deadlines are expired and their reservations released "
    "first. Newest created_at first, then ID descending; total counts before paging.",
)
def list_holds(principal: OperatorReader, page: Pagination, session: DbSession) -> TransferList:
    return holds.list_holds(session, principal, page)


@router.post(
    "/ops/transfers/{id}/review",
    operation_id="reviewHold",
    response_model=Transfer,
    openapi_extra=CSRF_OPENAPI,
    description="OPERATOR only. APPROVE turns RISK_HELD into READY and binds clearance to the "
    "recipient's current HOLD restriction (or, if none is active, the one that placed the "
    "hold). It keeps the reservation and original deadline and does not send money; the "
    "customer must confirm again. REJECT releases the reservation once and returns REJECTED. "
    "Repeating the same decision returns the stored result; any other state or decision, "
    "including a passed deadline, is 409 STATE_CONFLICT with current_transfer. Another "
    f"sandbox's or an unknown transfer is 404. {ORIGIN_NOTE}",
)
def review_hold(
    principal: OperatorWriter, transfer_id: TransferId, body: ReviewHold, session: DbSession
) -> Transfer:
    return holds.review_hold(session, principal, transfer_id, body)
