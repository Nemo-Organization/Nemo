"""Read-only customer discovery: seeded transfer recipients and the caller's own orders.

Scope always comes from the server-resolved principal; routes admit only CUSTOMER principals.
Nothing here writes, flushes or commits, and full account identifiers never leave this module.
Totals count the authorized set before limit/offset are applied.

Rulings where the docs are silent:
- Recipients are the sandbox's seeded external accounts (owner_actor_id NULL). Customer wallets,
  including the caller's own, are never listed, so other customers' identities are not exposed.
- Orders have no creation timestamp. The contract's "newest first by timestamp then ID" uses
  fee_verified_at DESC with NULL (unknown fee) last, then id DESC.
"""

from datetime import UTC, datetime

from sqlalchemy import ColumnElement, and_, func, select
from sqlalchemy.orm import Session

from app import models
from app.api.pagination import PageParams
from app.api.schemas import Order, OrderList, Recipient, RecipientList, Refund
from app.auth.principal import Principal
from app.auth.service import mask_identifier


def recipient_scope(principal: Principal) -> tuple[ColumnElement[bool], ...]:
    """Accounts a customer may name as a recipient: seeded, ownerless, in its own sandbox."""
    return (
        models.Account.sandbox_id == principal.sandbox_id,
        models.Account.owner_actor_id.is_(None),
    )


def _utc(value: datetime | None) -> datetime | None:
    return None if value is None else value.astimezone(UTC)


def recipient_view(account: models.Account) -> Recipient:
    return Recipient(
        id=account.id,
        display_name=account.display_name,
        bank_code=account.bank_code,
        masked_identifier=mask_identifier(account.account_identifier),
    )


def refund_view(refund: models.Refund) -> Refund:
    return Refund(
        id=refund.id,
        order_id=refund.order_id,
        account_id=refund.account_id,
        amount_vnd=refund.amount_vnd,
        status=refund.status,
        settled_at=_utc(refund.settled_at),
    )


def order_view(order: models.Order, refund: models.Refund | None) -> Order:
    """Unknown fee stays null with null provenance; a verified zero fee stays 0."""
    return Order(
        id=order.id,
        order_reference=order.order_reference,
        merchant_name=order.merchant_name,
        original_amount_vnd=order.original_amount_vnd,
        return_fee_vnd=order.return_fee_vnd,
        fee_source=order.fee_source,
        fee_verified_at=_utc(order.fee_verified_at),
        refund=None if refund is None else refund_view(refund),
    )


def list_recipients(session: Session, principal: Principal, page: PageParams) -> RecipientList:
    scope = recipient_scope(principal)
    total = session.execute(
        select(func.count()).select_from(models.Account).where(*scope)
    ).scalar_one()
    accounts = session.scalars(
        select(models.Account)
        .where(*scope)
        .order_by(models.Account.display_name, models.Account.id)
        .limit(page.limit)
        .offset(page.offset)
    ).all()
    return RecipientList(
        items=[recipient_view(account) for account in accounts],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


def list_orders(session: Session, principal: Principal, page: PageParams) -> OrderList:
    owned = (
        models.Order.sandbox_id == principal.sandbox_id,
        models.Order.customer_actor_id == principal.actor_id,
    )
    total = session.execute(
        select(func.count()).select_from(models.Order).where(*owned)
    ).scalar_one()
    rows = session.execute(
        select(models.Order, models.Refund)
        .outerjoin(
            models.Refund,
            and_(
                models.Refund.sandbox_id == models.Order.sandbox_id,
                models.Refund.order_id == models.Order.id,
            ),
        )
        .where(*owned)
        .order_by(models.Order.fee_verified_at.desc().nulls_last(), models.Order.id.desc())
        .limit(page.limit)
        .offset(page.offset)
    ).all()
    return OrderList(
        items=[order_view(order, refund) for order, refund in rows],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )
