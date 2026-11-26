"""Customer ownership scope for transfers. Read-only and lock-free.

Kept apart from the transfer service so that risk assessment (which the service's confirmation
consumes) can resolve the caller's own transfer without an import cycle.
"""

from uuid import UUID

from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import Session

from app import models
from app.auth.principal import Principal
from app.errors import ApplicationError


def not_found() -> ApplicationError:
    return ApplicationError(404, "NOT_FOUND", "Resource not found.")


def own_wallet_ids(principal: Principal):
    """Subquery of wallet IDs the calling customer owns in its own sandbox."""
    return select(models.Account.id).where(
        models.Account.sandbox_id == principal.sandbox_id,
        models.Account.owner_actor_id == principal.actor_id,
    )


def sent_by(principal: Principal) -> tuple[ColumnElement[bool], ...]:
    """Transfers sent from a wallet the calling customer owns, in its own sandbox."""
    return (
        models.Transfer.sandbox_id == principal.sandbox_id,
        models.Transfer.sender_account_id.in_(own_wallet_ids(principal)),
    )


def owned_transfer(session: Session, principal: Principal, transfer_id: UUID) -> models.Transfer:
    """The caller's own transfer, or 404 for missing and inaccessible IDs alike."""
    transfer = session.scalar(
        select(models.Transfer).where(models.Transfer.id == transfer_id, *sent_by(principal))
    )
    if transfer is None:
        raise not_found()
    return transfer
