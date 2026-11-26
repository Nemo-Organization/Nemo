from datetime import timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Query, Request, Response

from app.api.pagination import PageParams
from app.api.schemas import (
    ConfirmTransfer,
    CreateTransfer,
    RiskAssessment,
    Transfer,
    TransferList,
)
from app.auth.dependencies import (
    CSRF_OPENAPI,
    ORIGIN_NOTE,
    CustomerReader,
    CustomerWriter,
    DbSession,
    settings_of,
)
from app.risk import service as risk_service
from app.transfers import service

router = APIRouter(tags=["Customer"])
Pagination = Annotated[PageParams, Query()]
TransferId = Annotated[UUID, Path(alias="id")]


@router.get(
    "/transfers",
    operation_id="listTransfers",
    response_model=TransferList,
    description="Transfers sent by the authenticated customer. CUSTOMER only. Newest "
    "created_at first, then ID descending; total counts the caller's transfers before paging. "
    "Passed deadlines are first reconciled to EXPIRED, releasing reservations.",
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
    "customer's or sandbox's transfer is 404. Passed deadlines are first reconciled to EXPIRED.",
)
def get_transfer(
    principal: CustomerReader, transfer_id: TransferId, session: DbSession
) -> Transfer:
    return service.get_transfer(session, principal, transfer_id)


@router.post(
    "/transfers/{id}/assess",
    operation_id="assessTransfer",
    response_model=RiskAssessment,
    openapi_extra=CSRF_OPENAPI,
    description="Evaluate independent recipient and behavioral signals without a model call. "
    "Customer-owned draft or active held/ready transfer only; other states and passed deadlines "
    "are 409 STATE_CONFLICT. Persists the assessment for five minutes and changes no balance, "
    f"reservation or transfer status. {ORIGIN_NOTE}",
)
def assess_transfer(
    principal: CustomerWriter, transfer_id: TransferId, request: Request, session: DbSession
) -> RiskAssessment:
    lifetime = timedelta(seconds=settings_of(request).assessment_ttl_seconds)
    return risk_service.assess_transfer(session, principal, transfer_id, lifetime=lifetime)


@router.post(
    "/transfers/{id}/confirm",
    operation_id="confirmTransfer",
    response_model=Transfer,
    openapi_extra=CSRF_OPENAPI,
    description="Re-evaluate under locks with database time. Returns SUCCEEDED (one debit and one "
    "credit) or RISK_HELD (amount reserved, 15-minute review deadline); inspect status. A current "
    "HOLD wins over any acknowledgement. WARN needs acknowledged_assessment_id of this "
    "transfer's unexpired assessment with matching facts, otherwise 409 ACKNOWLEDGEMENT_REQUIRED "
    "with the fresh assessment. 409 INSUFFICIENT_FUNDS changes nothing. A READY transfer "
    "(operator clearance) executes from its own reservation once current checks pass: only the "
    "exact cleared restriction is overridden, a different active HOLD returns RISK_HELD with no "
    "new reservation or deadline extension, and warnings still need acknowledgement. Repeating "
    "returns the stored SUCCEEDED or RISK_HELD transfer; EXPIRED, CANCELED or REJECTED is 409 "
    f"STATE_CONFLICT with current_transfer. {ORIGIN_NOTE}",
)
def confirm_transfer(
    principal: CustomerWriter,
    transfer_id: TransferId,
    body: ConfirmTransfer,
    request: Request,
    session: DbSession,
) -> Transfer:
    settings = settings_of(request)
    return service.confirm_transfer(
        session,
        principal,
        transfer_id,
        body.acknowledged_assessment_id,
        hold_lifetime=timedelta(seconds=settings.hold_ttl_seconds),
        assessment_lifetime=timedelta(seconds=settings.assessment_ttl_seconds),
    )


@router.post(
    "/transfers/{id}/cancel",
    operation_id="cancelTransfer",
    response_model=Transfer,
    openapi_extra=CSRF_OPENAPI,
    description="Cancel the caller's DRAFT, RISK_HELD or READY transfer and release its "
    "reservation exactly once. Repeated cancellation returns the same CANCELED transfer; another "
    f"terminal state (including a passed deadline) is 409 STATE_CONFLICT. {ORIGIN_NOTE}",
)
def cancel_transfer(
    principal: CustomerWriter, transfer_id: TransferId, session: DbSession
) -> Transfer:
    return service.cancel_transfer(session, principal, transfer_id)
