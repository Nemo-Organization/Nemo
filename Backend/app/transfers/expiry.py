"""Deadline reconciliation: a DRAFT, RISK_HELD or READY transfer past expires_at becomes EXPIRED.

Expiry is decided against database time read after the account lock is held. Every path uses
the same account-first routine: lock the sender account, then lock the sender's due transfer rows
(plus any transfer the caller is about to act on) in ascending UUID order, then expire each row
that is still active and due, releasing its reservation exactly once. Every writer of a sender's
transfers holds that sender's account lock, so the due set cannot change while it is reconciled.

Reads (/me, actor selection, transfer reads, assessment) first check without locks whether the
actor has any due row and lock only if one exists; they may commit the reconciliation but never
debit. Each expiry is audited as a SYSTEM `TRANSFER_EXPIRED` event carrying the request ID that
triggered it. Helpers flush and never commit, except `expire_due_transfers`, the top-level sweep.
"""

from collections.abc import Iterable
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app import models
from app.auth.principal import SystemPrincipal
from app.operations.audit import append_audit
from app.transfers.locking import database_clock, lock_accounts, lock_transfers

ACTIVE_STATUSES = ("DRAFT", "RISK_HELD", "READY")


def maintenance_request_id() -> str:
    return f"maintenance-{uuid4()}"


def is_due(transfer: models.Transfer, now: datetime) -> bool:
    return transfer.status in ACTIVE_STATUSES and transfer.expires_at <= now


def expire_transfer(
    session: Session,
    account: models.Account,
    transfer: models.Transfer,
    now: datetime,
    *,
    request_id: str,
) -> None:
    """Expire one locked, due transfer of the locked sender `account`, releasing it once."""
    released, from_status = transfer.reserved_amount_vnd, transfer.status
    account.reserved_vnd -= released
    transfer.reserved_amount_vnd = 0
    transfer.status = "EXPIRED"
    transfer.completed_at = now
    append_audit(
        session,
        SystemPrincipal(sandbox_id=transfer.sandbox_id, request_id=request_id),
        "TRANSFER_EXPIRED",
        "TRANSFER",
        transfer.id,
        {
            "reason": "DEADLINE_PASSED",
            "from_status": from_status,
            "amount_vnd": transfer.amount_vnd,
            "released_vnd": released,
            "deadline": transfer.expires_at,
        },
    )


def lock_sender_transfers(
    session: Session,
    account: models.Account,
    now: datetime,
    *,
    include: Iterable[UUID] = (),
    request_id: str,
) -> tuple[dict[UUID, models.Transfer], int]:
    """Lock the sender's due rows plus `include` in UUID order and expire those still due.

    The caller must hold the lock on `account` (the sender). Returns the locked rows and the
    number expired.
    """
    due_ids = session.scalars(
        select(models.Transfer.id).where(
            models.Transfer.sandbox_id == account.sandbox_id,
            models.Transfer.sender_account_id == account.id,
            models.Transfer.status.in_(ACTIVE_STATUSES),
            models.Transfer.expires_at <= now,
        )
    ).all()
    rows = lock_transfers(session, account.sandbox_id, [*due_ids, *include])
    expired = 0
    for transfer_id in sorted(rows):
        transfer = rows[transfer_id]
        if transfer.sender_account_id != account.id:
            raise ValueError("Only the locked sender's transfers can be reconciled.")
        if is_due(transfer, now):
            expire_transfer(session, account, transfer, now, request_id=request_id)
            expired += 1
    session.flush()
    return rows, expired


def reconcile_account_expiry(
    session: Session, account_id: UUID, now: datetime, *, request_id: str | None = None
) -> int:
    """Expire the account's due transfers as of `now` (database time). Returns how many.

    Acquires the account lock, or keeps it if the caller already holds it; pass a `now` read
    after that lock so a lock wait cannot leave a passed deadline unexpired.
    """
    sandbox_id = session.scalar(
        select(models.Account.sandbox_id).where(models.Account.id == account_id)
    )
    if sandbox_id is None:
        raise LookupError("Unknown account.")
    account = lock_accounts(session, sandbox_id, [account_id])[account_id]
    _, expired = lock_sender_transfers(
        session, account, now, request_id=request_id or maintenance_request_id()
    )
    return expired


def reconcile_actor_accounts(
    session: Session, sandbox_id: UUID, actor_id: UUID, *, request_id: str
) -> int:
    """Read preflight: expire the actor's due transfers before its money or transfers are shown.

    Takes no lock unless a due row exists. Locks every owned account in UUID order first.
    """
    owned = select(models.Account.id).where(
        models.Account.sandbox_id == sandbox_id, models.Account.owner_actor_id == actor_id
    )
    any_due = session.scalar(
        select(
            exists().where(
                models.Transfer.sandbox_id == sandbox_id,
                models.Transfer.sender_account_id.in_(owned),
                models.Transfer.status.in_(ACTIVE_STATUSES),
                models.Transfer.expires_at <= func.clock_timestamp(),
            )
        )
    )
    if not any_due:
        return 0
    account_ids = sorted(lock_accounts(session, sandbox_id, session.scalars(owned).all()))
    now = database_clock(session)
    return sum(
        reconcile_account_expiry(session, account_id, now, request_id=request_id)
        for account_id in account_ids
    )


def expire_due_transfers(
    session: Session, sandbox_id: UUID | None = None, *, request_id: str | None = None
) -> int:
    """Maintenance sweep of every due transfer, optionally limited to one sandbox.

    Top-level: each sender account is reconciled and committed in its own short transaction, so
    the sweep never holds more than one account lock. Repeated or overlapping sweeps converge.
    """
    request_id = request_id or maintenance_request_id()
    discovery = (
        select(models.Transfer.sandbox_id, models.Transfer.sender_account_id)
        .where(
            models.Transfer.status.in_(ACTIVE_STATUSES),
            models.Transfer.expires_at <= func.clock_timestamp(),
        )
        .distinct()
        .order_by(models.Transfer.sender_account_id)
    )
    if sandbox_id is not None:
        discovery = discovery.where(models.Transfer.sandbox_id == sandbox_id)
    senders = session.execute(discovery).all()
    total = 0
    for sender_sandbox_id, account_id in senders:
        lock_accounts(session, sender_sandbox_id, [account_id])
        total += reconcile_account_expiry(
            session, account_id, database_clock(session), request_id=request_id
        )
        session.commit()
    return total
