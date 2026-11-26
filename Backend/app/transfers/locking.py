"""Lock acquisition for money-changing work, always in one global order.

1. The recipient-policy advisory lock (confirmation; restriction create/revoke reuse it).
2. Account rows, in ascending UUID order.
3. Transfer (later also refund) rows, in ascending UUID order.

A caller may skip a level but never acquires an earlier level after a later one; in particular
no operation takes a recipient advisory lock after locking accounts. All locks are
transaction-scoped and released by the caller's commit or rollback. Helpers here never commit.

Rows are locked with `SELECT ... FOR NO KEY UPDATE`, the exclusive row lock PostgreSQL's own
UPDATE of non-key columns takes. It excludes every other money writer exactly like FOR UPDATE,
but unlike FOR UPDATE it does not conflict with the FOR KEY SHARE locks taken by foreign-key
checks. A concurrent draft insert (which key-share locks its sender, then its recipient) therefore
cannot deadlock against a confirmation that locked the same two accounts in UUID order.

The advisory key is the first eight bytes (big-endian, signed) of SHA-256 over a versioned
namespace and the 16-byte sandbox and recipient UUIDs. A hash collision only serializes two
unrelated recipients; it can never let two writers of the same recipient overlap.
"""

import hashlib
from collections.abc import Iterable
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models

RECIPIENT_POLICY_NAMESPACE = b"guardian/recipient-policy/v1\x00"


def recipient_policy_key(sandbox_id: UUID, recipient_id: UUID) -> int:
    digest = hashlib.sha256(
        RECIPIENT_POLICY_NAMESPACE + sandbox_id.bytes + recipient_id.bytes
    ).digest()
    return int.from_bytes(digest[:8], "big", signed=True)


def lock_recipient_policy(session: Session, sandbox_id: UUID, recipient_id: UUID) -> None:
    """Serialize against restriction changes for this recipient until the transaction ends."""
    session.execute(
        select(func.pg_advisory_xact_lock(recipient_policy_key(sandbox_id, recipient_id)))
    )


def lock_accounts(
    session: Session, sandbox_id: UUID, account_ids: Iterable[UUID]
) -> dict[UUID, models.Account]:
    """Lock the accounts in ascending UUID order and return their current committed rows."""
    ids = sorted(set(account_ids))
    rows = session.scalars(
        select(models.Account)
        .where(models.Account.sandbox_id == sandbox_id, models.Account.id.in_(ids))
        .order_by(models.Account.id)
        .with_for_update(key_share=True)
        .execution_options(populate_existing=True)
    ).all()
    locked = {row.id: row for row in rows}
    if len(locked) != len(ids):
        raise LookupError("An account to lock does not exist in this sandbox.")
    return locked


def lock_transfers(
    session: Session, sandbox_id: UUID, transfer_ids: Iterable[UUID]
) -> dict[UUID, models.Transfer]:
    """Lock the transfers in ascending UUID order and return their current committed rows.

    Callers must already hold the lock of every sender account involved.
    """
    ids = sorted(set(transfer_ids))
    if not ids:
        return {}
    rows = session.scalars(
        select(models.Transfer)
        .where(models.Transfer.sandbox_id == sandbox_id, models.Transfer.id.in_(ids))
        .order_by(models.Transfer.id)
        .with_for_update(key_share=True)
        .execution_options(populate_existing=True)
    ).all()
    locked = {row.id: row for row in rows}
    if len(locked) != len(ids):
        raise LookupError("A transfer to lock does not exist in this sandbox.")
    return locked


def database_clock(session: Session) -> datetime:
    """Current database time. Read it after acquiring locks so a lock wait cannot make it stale.

    `now()` is the transaction start, which may precede a long lock wait; deadlines and
    acknowledgement lifetimes are decided against the time the locked decision is made.
    """
    return session.execute(select(func.clock_timestamp())).scalar_one()
