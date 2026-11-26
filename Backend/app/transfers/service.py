"""Customer transfer drafts, reads, confirmation and cancellation.

Top-level services complete the transaction that identity resolution already started; helpers
only flush. Scope always comes from the server-resolved principal, never from request IDs.

Confirmation and cancellation follow the global lock order (`app.transfers.locking`):
confirmation takes the recipient-policy advisory lock, then the sender and recipient accounts in
UUID order; cancellation takes only the sender account. Both then lock the caller's due transfers
together with the current transfer in UUID order and expire the due ones before deciding. Every
decision uses database time read after those locks. When a 409 references a newly persisted
assessment or a reconciled expiry, that state is committed before the conflict is raised.

Rulings where the docs are silent:
- A self-transfer (sender == recipient) is 422 VALIDATION_ERROR. It is checked before any lookup,
  so the response reveals nothing about either ID.
- The sender must be a wallet owned by the calling customer and the recipient must be in
  `recipient_scope` (the sandbox's seeded ownerless accounts). Anything else, including another
  customer's wallet or another sandbox's account, is the same 404 NOT_FOUND.
- Creating a draft neither checks nor reserves funds; confirmation does.
- A replay returns the stored transfer as it is now, whatever its status, and never extends its
  deadline. The idempotency key is the database constraint (sandbox, sender, client_request_id).
  A replay, like every transfer read, first reconciles the caller's passed deadlines.
- listTransfers is the caller's own sent transfers, newest created_at first, then id descending.
- Confirmation persists the assessment it acted on (HOLD, executed ALLOW/WARN, or the fresh WARN
  returned with 409 ACKNOWLEDGEMENT_REQUIRED), so Transfer.assessment explains the outcome.
  Insufficient funds (409 INSUFFICIENT_FUNDS) persists no assessment and changes nothing.
- An acknowledgement is current only if it is an assessment of this transfer, unexpired at the
  locked decision time, with the same policy version and facts fingerprint. Any other ID,
  including an unknown one or another transfer's, is treated as missing (409, not 404).
- Confirming SUCCEEDED or RISK_HELD returns the stored transfer; confirming CANCELED, REJECTED or
  EXPIRED is 409 STATE_CONFLICT with the current transfer. READY is 409 STATE_CONFLICT until
  operator clearance and its reconfirmation rules exist (Task 8); no READY row can exist before.
- Cancel of DRAFT, RISK_HELD or READY returns 200 CANCELED; cancel of CANCELED returns the same
  stored result; cancel of SUCCEEDED, REJECTED or EXPIRED is 409 STATE_CONFLICT.
- Audit event types: TRANSFER_SUCCEEDED, TRANSFER_HELD, TRANSFER_CANCELED (customer actor) and
  TRANSFER_EXPIRED (SYSTEM), target_type TRANSFER, with the request ID.
"""

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app import models
from app.api.pagination import PageParams
from app.api.schemas import CreateTransfer, Transfer, TransferList
from app.auth.principal import Principal
from app.demo.queries import recipient_scope
from app.errors import ApplicationError
from app.operations.audit import append_audit
from app.risk.facts import RiskFacts, collect_facts, fingerprint_facts
from app.risk.service import (
    DEFAULT_ASSESSMENT_LIFETIME,
    RiskDecision,
    evaluate_risk,
    record_assessment,
    state_conflict,
)
from app.transfers import serialization
from app.transfers.expiry import ACTIVE_STATUSES, lock_sender_transfers, reconcile_actor_accounts
from app.transfers.locking import database_clock, lock_accounts, lock_recipient_policy
from app.transfers.ownership import not_found, owned_transfer, sent_by

__all__ = [
    "cancel_transfer",
    "confirm_transfer",
    "create_transfer",
    "get_transfer",
    "list_transfers",
    "not_found",
    "owned_transfer",
    "sent_by",
]

DEFAULT_DRAFT_LIFETIME = timedelta(minutes=30)
DEFAULT_HOLD_LIFETIME = timedelta(minutes=15)
IDEMPOTENCY_KEY = ("sandbox_id", "sender_account_id", "client_request_id")


def reconcile_caller(session: Session, principal: Principal) -> None:
    """Commit the expiry of the caller's passed deadlines before anything is shown or decided."""
    if reconcile_actor_accounts(
        session, principal.sandbox_id, principal.actor_id, request_id=principal.request_id
    ):
        session.commit()


def create_transfer(
    session: Session,
    principal: Principal,
    command: CreateTransfer,
    *,
    draft_lifetime: timedelta = DEFAULT_DRAFT_LIFETIME,
) -> Transfer:
    """Create an immutable DRAFT, or return the existing one for an exact replay.

    Race-safe: INSERT ... ON CONFLICT DO NOTHING on the key, then read the row that won. A
    concurrent duplicate waits on the unique index until the winner commits, then replays it.
    """
    if command.sender_account_id == command.recipient_account_id:
        raise ApplicationError(
            422, "VALIDATION_ERROR", "Sender and recipient accounts must be different."
        )
    sender = session.scalar(
        select(models.Account).where(
            models.Account.id == command.sender_account_id,
            models.Account.sandbox_id == principal.sandbox_id,
            models.Account.owner_actor_id == principal.actor_id,
        )
    )
    recipient = session.scalar(
        select(models.Account).where(
            models.Account.id == command.recipient_account_id, *recipient_scope(principal)
        )
    )
    if sender is None or recipient is None:
        raise not_found()

    inserted_id = session.execute(
        insert(models.Transfer)
        .values(
            sandbox_id=principal.sandbox_id,
            sender_account_id=sender.id,
            recipient_account_id=recipient.id,
            client_request_id=command.client_request_id,
            amount_vnd=command.amount_vnd,
            expires_at=func.now() + draft_lifetime,
        )
        .on_conflict_do_nothing(index_elements=list(IDEMPOTENCY_KEY))
        .returning(models.Transfer.id)
    ).scalar_one_or_none()
    transfer = session.scalars(
        select(models.Transfer).where(
            models.Transfer.sandbox_id == principal.sandbox_id,
            models.Transfer.sender_account_id == sender.id,
            models.Transfer.client_request_id == command.client_request_id,
        )
    ).one()
    replayed = inserted_id is None
    if replayed and (transfer.recipient_account_id, transfer.amount_vnd) != (
        recipient.id,
        command.amount_vnd,
    ):
        raise ApplicationError(
            409,
            "IDEMPOTENCY_CONFLICT",
            "This client_request_id was already used for a different transfer. "
            "Use a new key for a new transfer.",
        )
    if replayed:
        reconcile_caller(session, principal)
    view = serialization.load_transfer_view(session, transfer, replayed=replayed)
    session.commit()
    return view


def get_transfer(session: Session, principal: Principal, transfer_id: UUID) -> Transfer:
    transfer = owned_transfer(session, principal, transfer_id)
    reconcile_caller(session, principal)
    return serialization.load_transfer_view(session, transfer)


def list_transfers(session: Session, principal: Principal, page: PageParams) -> TransferList:
    reconcile_caller(session, principal)
    scope = sent_by(principal)
    total = session.execute(
        select(func.count()).select_from(models.Transfer).where(*scope)
    ).scalar_one()
    transfers = session.scalars(
        select(models.Transfer)
        .where(*scope)
        .order_by(models.Transfer.created_at.desc(), models.Transfer.id.desc())
        .limit(page.limit)
        .offset(page.offset)
    ).all()
    return TransferList(
        items=serialization.transfer_views(session, principal.sandbox_id, transfers),
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


# Confirmation and cancellation


def _completed(session: Session, transfer: models.Transfer) -> Transfer:
    """Project the locked transfer, then commit everything decided under the locks."""
    view = serialization.load_transfer_view(session, transfer)
    session.commit()
    return view


def _committed(session: Session, error: ApplicationError) -> ApplicationError:
    """Commit the reconciled or assessed state the conflict response refers to, then raise it."""
    session.commit()
    return error


def _insufficient_funds() -> ApplicationError:
    return ApplicationError(
        409, "INSUFFICIENT_FUNDS", "Available funds do not cover this transfer amount."
    )


def _available(account: models.Account) -> int:
    return account.balance_vnd - account.reserved_vnd


def _is_current_acknowledgement(
    session: Session,
    transfer: models.Transfer,
    assessment_id: UUID | None,
    facts: RiskFacts,
    now: datetime,
) -> bool:
    if assessment_id is None:
        return False
    acknowledged = session.scalar(
        select(models.RiskAssessment).where(
            models.RiskAssessment.id == assessment_id,
            models.RiskAssessment.sandbox_id == transfer.sandbox_id,
            models.RiskAssessment.transfer_id == transfer.id,
        )
    )
    return (
        acknowledged is not None
        and acknowledged.expires_at > now
        and acknowledged.policy_version == facts.policy_version
        and acknowledged.facts_fingerprint == fingerprint_facts(facts)
    )


def _hold(
    session: Session,
    principal: Principal,
    sender: models.Account,
    transfer: models.Transfer,
    facts: RiskFacts,
    assessment: models.RiskAssessment,
    now: datetime,
    lifetime: timedelta,
) -> None:
    """Reserve the amount once and start the review deadline. Funds were checked."""
    amount = transfer.amount_vnd
    sender.reserved_vnd += amount
    transfer.status = "RISK_HELD"
    transfer.reserved_amount_vnd = amount
    transfer.held_at = now
    transfer.expires_at = now + lifetime
    append_audit(
        session,
        principal,
        "TRANSFER_HELD",
        "TRANSFER",
        transfer.id,
        {
            "from_status": "DRAFT",
            "amount_vnd": amount,
            "reserved_vnd": amount,
            "restriction_id": facts.restriction_id,
            "assessment_id": assessment.id,
            "policy_version": facts.policy_version,
            "deadline": transfer.expires_at,
        },
    )
    session.flush()


def _post(
    session: Session,
    principal: Principal,
    sender: models.Account,
    recipient: models.Account,
    transfer: models.Transfer,
    decision: RiskDecision,
    assessment: models.RiskAssessment,
    acknowledged_assessment_id: UUID | None,
    now: datetime,
) -> None:
    """Write the one debit/credit pair, move both cached balances and mark SUCCEEDED.

    Executes from available funds (a DRAFT; funds were checked). READY confirmation (Task 8)
    executes from the transfer's own reservation instead and must release it in the same step.
    """
    amount = transfer.amount_vnd
    sender.balance_vnd -= amount
    recipient.balance_vnd += amount
    session.add_all(
        [
            models.LedgerEntry(
                sandbox_id=transfer.sandbox_id,
                account_id=sender.id,
                transfer_id=transfer.id,
                kind="TRANSFER_DEBIT",
                amount_vnd=-amount,
                created_at=now,
            ),
            models.LedgerEntry(
                sandbox_id=transfer.sandbox_id,
                account_id=recipient.id,
                transfer_id=transfer.id,
                kind="TRANSFER_CREDIT",
                amount_vnd=amount,
                created_at=now,
            ),
        ]
    )
    transfer.status = "SUCCEEDED"
    transfer.completed_at = now
    append_audit(
        session,
        principal,
        "TRANSFER_SUCCEEDED",
        "TRANSFER",
        transfer.id,
        {
            "from_status": "DRAFT",
            "amount_vnd": amount,
            "decision": decision.decision,
            "assessment_id": assessment.id,
            "acknowledged_assessment_id": (
                acknowledged_assessment_id if decision.decision == "WARN" else None
            ),
            "policy_version": assessment.policy_version,
        },
    )
    session.flush()


def confirm_transfer(
    session: Session,
    principal: Principal,
    transfer_id: UUID,
    acknowledged_assessment_id: UUID | None,
    *,
    hold_lifetime: timedelta = DEFAULT_HOLD_LIFETIME,
    assessment_lifetime: timedelta = DEFAULT_ASSESSMENT_LIFETIME,
) -> Transfer:
    """Execute, hold or refuse the caller's transfer according to current risk and funds."""
    owned = owned_transfer(session, principal, transfer_id)
    sandbox_id, sender_id, recipient_id = (
        owned.sandbox_id,
        owned.sender_account_id,
        owned.recipient_account_id,
    )
    lock_recipient_policy(session, sandbox_id, recipient_id)
    accounts = lock_accounts(session, sandbox_id, [sender_id, recipient_id])
    sender, recipient = accounts[sender_id], accounts[recipient_id]
    now = database_clock(session)
    rows, _ = lock_sender_transfers(
        session, sender, now, include=[owned.id], request_id=principal.request_id
    )
    transfer = rows[owned.id]

    if transfer.status in ("SUCCEEDED", "RISK_HELD"):
        return _completed(session, transfer)
    if transfer.status != "DRAFT":
        raise _committed(
            session,
            state_conflict(session, transfer, f"This transfer is {transfer.status}."),
        )

    facts = collect_facts(session, transfer, now=now)
    decision = evaluate_risk(facts)
    if decision.decision == "HOLD":
        if _available(sender) < transfer.amount_vnd:
            raise _committed(session, _insufficient_funds())
        assessment = record_assessment(
            session, transfer, facts, decision, lifetime=assessment_lifetime, now=now
        )
        _hold(session, principal, sender, transfer, facts, assessment, now, hold_lifetime)
        return _completed(session, transfer)

    if decision.decision == "WARN" and not _is_current_acknowledgement(
        session, transfer, acknowledged_assessment_id, facts, now
    ):
        fresh = record_assessment(
            session, transfer, facts, decision, lifetime=assessment_lifetime, now=now
        )
        raise _committed(
            session,
            ApplicationError(
                409,
                "ACKNOWLEDGEMENT_REQUIRED",
                "Review the current assessment before continuing.",
                assessment=serialization.assessment_view(fresh),
            ),
        )
    if _available(sender) < transfer.amount_vnd:
        raise _committed(session, _insufficient_funds())
    assessment = record_assessment(
        session, transfer, facts, decision, lifetime=assessment_lifetime, now=now
    )
    _post(
        session,
        principal,
        sender,
        recipient,
        transfer,
        decision,
        assessment,
        acknowledged_assessment_id,
        now,
    )
    return _completed(session, transfer)


def cancel_transfer(session: Session, principal: Principal, transfer_id: UUID) -> Transfer:
    """Cancel the caller's active transfer, releasing its reservation exactly once."""
    owned = owned_transfer(session, principal, transfer_id)
    sender = lock_accounts(session, owned.sandbox_id, [owned.sender_account_id])[
        owned.sender_account_id
    ]
    now = database_clock(session)
    rows, _ = lock_sender_transfers(
        session, sender, now, include=[owned.id], request_id=principal.request_id
    )
    transfer = rows[owned.id]

    if transfer.status == "CANCELED":
        return _completed(session, transfer)
    if transfer.status not in ACTIVE_STATUSES:
        raise _committed(
            session,
            state_conflict(session, transfer, f"This transfer is already {transfer.status}."),
        )
    released, from_status = transfer.reserved_amount_vnd, transfer.status
    sender.reserved_vnd -= released
    transfer.reserved_amount_vnd = 0
    transfer.status = "CANCELED"
    transfer.completed_at = now
    append_audit(
        session,
        principal,
        "TRANSFER_CANCELED",
        "TRANSFER",
        transfer.id,
        {
            "reason": "CUSTOMER_REQUEST",
            "from_status": from_status,
            "amount_vnd": transfer.amount_vnd,
            "released_vnd": released,
        },
    )
    session.flush()
    return _completed(session, transfer)
