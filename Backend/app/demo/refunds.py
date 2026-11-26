"""Controlled settlement of a seeded, pre-approved refund (settleDemoRefund).

A synthetic fixture event triggered only by the sandbox's demo controller; there is no external
payment integration. Lock order (`app.transfers.locking`): the refund's account, then that
account's due transfers (expired first, as every money write reconciles), then the refund row.
Refund settlement never takes a recipient advisory lock. Decisions use database time read after
the locks. The unique (sandbox, refund) ledger key is the final duplicate-credit guard.

Rulings where the docs are silent:
- A refund outside the controller's sandbox, or an unknown ID, is 404 NOT_FOUND.
- A refund that is not consistent with its order (the account's owner is not the order's
  customer, or the amount exceeds the order's original amount) is 409 STATE_CONFLICT and
  nothing is written. Seeded fixtures are always consistent.
- The first settlement and every repeat return 200 with the stored Refund; repeats write no
  ledger entry or audit event.
- Audit: REFUND_SETTLED, actor DEMO_CONTROL, target REFUND, with amount, account and order.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.api.schemas import Refund
from app.auth.principal import DemoPrincipal
from app.demo.queries import refund_view
from app.errors import ApplicationError
from app.operations.audit import append_audit
from app.transfers.expiry import lock_sender_transfers
from app.transfers.locking import database_clock, lock_accounts, lock_refund
from app.transfers.ownership import not_found


def _settleable(session: Session, refund: models.Refund, account: models.Account) -> bool:
    """The refund credits its order's customer, within the order's original amount."""
    order = session.scalar(
        select(models.Order).where(
            models.Order.sandbox_id == refund.sandbox_id, models.Order.id == refund.order_id
        )
    )
    return (
        order is not None
        and refund.account_id == account.id
        and account.owner_actor_id is not None
        and account.owner_actor_id == order.customer_actor_id
        and refund.amount_vnd <= order.original_amount_vnd
    )


def settle_refund(session: Session, controller: DemoPrincipal, refund_id: UUID) -> Refund:
    """Credit an APPROVED refund to its account exactly once; repeats return it as stored."""
    found = session.scalar(
        select(models.Refund).where(
            models.Refund.id == refund_id, models.Refund.sandbox_id == controller.sandbox_id
        )
    )
    if found is None:
        raise not_found()
    account = lock_accounts(session, found.sandbox_id, [found.account_id])[found.account_id]
    now = database_clock(session)
    lock_sender_transfers(session, account, now, request_id=controller.request_id)
    refund = lock_refund(session, found.sandbox_id, found.id)

    if refund.status == "SETTLED":
        view = refund_view(refund)
        session.commit()
        return view
    if refund.status != "APPROVED" or not _settleable(session, refund, account):
        session.commit()  # keep any reconciled expiry
        raise ApplicationError(409, "STATE_CONFLICT", "This refund cannot be settled.")

    amount = refund.amount_vnd
    account.balance_vnd += amount
    session.add(
        models.LedgerEntry(
            sandbox_id=refund.sandbox_id,
            account_id=account.id,
            refund_id=refund.id,
            kind="REFUND_CREDIT",
            amount_vnd=amount,
            created_at=now,
        )
    )
    refund.status = "SETTLED"
    refund.settled_at = now
    append_audit(
        session,
        controller,
        "REFUND_SETTLED",
        "REFUND",
        refund.id,
        {
            "amount_vnd": amount,
            "account_id": account.id,
            "order_id": refund.order_id,
            "balance_vnd": account.balance_vnd,
            "reserved_vnd": account.reserved_vnd,
        },
    )
    session.flush()
    view = refund_view(refund)
    session.commit()
    return view
