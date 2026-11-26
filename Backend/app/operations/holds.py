"""Operator hold queue and review: listHolds and reviewHold.

Scope is the operator principal's own sandbox; another sandbox's or an unknown transfer is 404.
A review follows the global lock order (`app.transfers.locking`): the recipient-policy advisory
lock (so the restriction read is ordered against restriction changes), the sender and recipient
accounts in UUID order, then the sender's due transfers together with the reviewed one in UUID
order, expiring the due ones first. Every decision uses database time read after those locks.
A reconciled expiry is committed before the 409 that reports it. Neither decision posts money.

Rulings where the docs are silent:
- listHolds lists every customer's RISK_HELD and READY transfers in the sandbox, newest
  created_at first, then id descending (the contract's list order), with total counted before
  paging. The sandbox's passed deadlines are expired first by the shared sweep, committed and
  audited as SYSTEM with the list request ID.
- APPROVE binds clearance to the recipient's current active HOLD restriction, read under the
  recipient lock. If no HOLD is currently active (the restriction was revoked or expired, or
  only a WARN remains), clearance binds to the restriction that placed the hold, taken from the
  transfer's latest HOLD assessment. Restrictions are immutable decisions and an inactive one
  never becomes active again, so that clearance overrides nothing: the customer's
  reconfirmation is judged on current facts, a WARN still needs acknowledgement and a later
  HOLD re-holds. This keeps the FALSE_POSITIVE path (revoke, then approve the hold, then
  reconfirm) working without letting approval override a decision the operator did not see.
- APPROVE keeps the reservation, held_at and the original deadline; it records no assessment.
- REJECT releases the transfer's reservation once and sets REJECTED and completed_at;
  reviewed_by and review_reason record the decision, cleared_restriction_id stays null.
- The review is idempotent by transfer ID and decision: APPROVE of READY and REJECT of REJECTED
  return the stored transfer whatever the reason (the first reason is kept). Every other
  combination, including REJECT of READY, any decision on DRAFT, SUCCEEDED, CANCELED or EXPIRED,
  and APPROVE of REJECTED, is 409 STATE_CONFLICT with the current transfer.
- Audit: TRANSFER_APPROVED and TRANSFER_REJECTED, actor OPERATOR, target TRANSFER, with the
  reason, from_status and restriction IDs (cleared and currently active) or released amount.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.api.pagination import PageParams
from app.api.schemas import ReviewHold, Transfer, TransferList
from app.auth.principal import Principal
from app.errors import ApplicationError
from app.operations.audit import append_audit
from app.risk.facts import RiskFacts, collect_facts
from app.risk.service import state_conflict
from app.transfers import serialization
from app.transfers.expiry import expire_due_transfers, lock_sender_transfers
from app.transfers.locking import database_clock, lock_accounts, lock_recipient_policy
from app.transfers.ownership import not_found

HELD_STATUSES = ("RISK_HELD", "READY")
# The state a decision produces; repeating the decision there returns the stored result.
DECIDED_STATUS = {"APPROVE": "READY", "REJECT": "REJECTED"}


def list_holds(session: Session, principal: Principal, page: PageParams) -> TransferList:
    """The sandbox's current RISK_HELD and READY transfers, after expiry reconciliation."""
    expire_due_transfers(session, principal.sandbox_id, request_id=principal.request_id)
    scope = (
        models.Transfer.sandbox_id == principal.sandbox_id,
        models.Transfer.status.in_(HELD_STATUSES),
    )
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


def _sandbox_transfer(session: Session, principal: Principal, transfer_id: UUID) -> models.Transfer:
    transfer = session.scalar(
        select(models.Transfer).where(
            models.Transfer.id == transfer_id,
            models.Transfer.sandbox_id == principal.sandbox_id,
        )
    )
    if transfer is None:
        raise not_found()
    return transfer


def _hold_source(session: Session, transfer: models.Transfer) -> UUID | None:
    """The restriction cited by the transfer's latest HOLD assessment (what placed the hold)."""
    restriction_id = session.scalar(
        select(models.RiskAssessment.facts["restriction_id"].astext)
        .where(
            models.RiskAssessment.sandbox_id == transfer.sandbox_id,
            models.RiskAssessment.transfer_id == transfer.id,
            models.RiskAssessment.decision == "HOLD",
        )
        .order_by(models.RiskAssessment.assessed_at.desc(), models.RiskAssessment.id.desc())
        .limit(1)
    )
    return None if restriction_id is None else UUID(restriction_id)


def _clearance_target(session: Session, transfer: models.Transfer, facts: RiskFacts) -> UUID | None:
    """The current active HOLD restriction, else the restriction that placed the hold."""
    if facts.restriction_action == "HOLD" and facts.restriction_id is not None:
        return facts.restriction_id
    return _hold_source(session, transfer)


def _approve(
    session: Session,
    principal: Principal,
    transfer: models.Transfer,
    command: ReviewHold,
    facts: RiskFacts,
    cleared: UUID,
) -> None:
    transfer.status = "READY"
    transfer.reviewed_by = principal.actor_id
    transfer.review_reason = command.reason
    transfer.cleared_restriction_id = cleared
    append_audit(
        session,
        principal,
        "TRANSFER_APPROVED",
        "TRANSFER",
        transfer.id,
        {
            "decision": "APPROVE",
            "reason": command.reason,
            "from_status": "RISK_HELD",
            "cleared_restriction_id": cleared,
            "current_restriction_id": facts.restriction_id,
            "current_restriction_action": facts.restriction_action,
            "amount_vnd": transfer.amount_vnd,
            "reserved_vnd": transfer.reserved_amount_vnd,
            "deadline": transfer.expires_at,
        },
    )
    session.flush()


def _reject(
    session: Session,
    principal: Principal,
    sender: models.Account,
    transfer: models.Transfer,
    command: ReviewHold,
    now: datetime,
) -> None:
    released = transfer.reserved_amount_vnd
    sender.reserved_vnd -= released
    transfer.reserved_amount_vnd = 0
    transfer.status = "REJECTED"
    transfer.completed_at = now
    transfer.reviewed_by = principal.actor_id
    transfer.review_reason = command.reason
    append_audit(
        session,
        principal,
        "TRANSFER_REJECTED",
        "TRANSFER",
        transfer.id,
        {
            "decision": "REJECT",
            "reason": command.reason,
            "from_status": "RISK_HELD",
            "amount_vnd": transfer.amount_vnd,
            "released_vnd": released,
        },
    )
    session.flush()


def review_hold(
    session: Session, principal: Principal, transfer_id: UUID, command: ReviewHold
) -> Transfer:
    """Approve (READY, no money moves) or reject (REJECTED, reservation released) one hold."""
    found = _sandbox_transfer(session, principal, transfer_id)
    sandbox_id, sender_id, recipient_id = (
        found.sandbox_id,
        found.sender_account_id,
        found.recipient_account_id,
    )
    lock_recipient_policy(session, sandbox_id, recipient_id)
    accounts = lock_accounts(session, sandbox_id, [sender_id, recipient_id])
    sender = accounts[sender_id]
    now = database_clock(session)
    rows, _ = lock_sender_transfers(
        session, sender, now, include=[found.id], request_id=principal.request_id
    )
    transfer = rows[found.id]

    if transfer.status == DECIDED_STATUS[command.decision]:
        return _completed(session, transfer)
    if transfer.status != "RISK_HELD":
        raise _committed(
            session,
            state_conflict(
                session, transfer, f"This transfer is {transfer.status} and cannot be reviewed."
            ),
        )

    if command.decision == "APPROVE":
        facts = collect_facts(session, transfer, now=now)
        cleared = _clearance_target(session, transfer, facts)
        if cleared is None:  # Every hold records its HOLD assessment; defensive only.
            raise _committed(
                session,
                state_conflict(session, transfer, "No restriction is recorded for this hold."),
            )
        _approve(session, principal, transfer, command, facts, cleared)
    else:
        _reject(session, principal, sender, transfer, command, now)
    return _completed(session, transfer)


def _completed(session: Session, transfer: models.Transfer) -> Transfer:
    """Project the locked transfer, then commit everything decided under the locks."""
    view = serialization.load_transfer_view(session, transfer)
    session.commit()
    return view


def _committed(session: Session, error: ApplicationError) -> ApplicationError:
    """Commit the reconciled state the conflict response refers to, then raise it."""
    session.commit()
    return error
