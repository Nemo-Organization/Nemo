"""Customer transfer drafts and reads.

Top-level services complete the transaction that identity resolution already started; helpers
only flush. Scope always comes from the server-resolved principal, never from request IDs.

Rulings where the docs are silent:
- A self-transfer (sender == recipient) is 422 VALIDATION_ERROR. It is checked before any lookup,
  so the response reveals nothing about either ID.
- The sender must be a wallet owned by the calling customer and the recipient must be in
  `recipient_scope` (the sandbox's seeded ownerless accounts). Anything else, including another
  customer's wallet or another sandbox's account, is the same 404 NOT_FOUND.
- Creating a draft neither checks nor reserves funds; confirmation does.
- A replay returns the stored transfer as it is now, whatever its status, and never extends its
  deadline. The idempotency key is the database constraint (sandbox, sender, client_request_id).
- listTransfers is the caller's own sent transfers, newest created_at first, then id descending.
"""

from datetime import timedelta
from uuid import UUID

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app import models
from app.api.pagination import PageParams
from app.api.schemas import CreateTransfer, Transfer, TransferList
from app.auth.principal import Principal
from app.demo.queries import recipient_scope
from app.errors import ApplicationError
from app.transfers import serialization

DEFAULT_DRAFT_LIFETIME = timedelta(minutes=30)
IDEMPOTENCY_KEY = ("sandbox_id", "sender_account_id", "client_request_id")


def not_found() -> ApplicationError:
    return ApplicationError(404, "NOT_FOUND", "Resource not found.")


def sent_by(principal: Principal) -> tuple[ColumnElement[bool], ...]:
    """Transfers sent from a wallet the calling customer owns, in its own sandbox."""
    own_wallets = select(models.Account.id).where(
        models.Account.sandbox_id == principal.sandbox_id,
        models.Account.owner_actor_id == principal.actor_id,
    )
    return (
        models.Transfer.sandbox_id == principal.sandbox_id,
        models.Transfer.sender_account_id.in_(own_wallets),
    )


def owned_transfer(session: Session, principal: Principal, transfer_id: UUID) -> models.Transfer:
    """The caller's own transfer, or 404 for missing and inaccessible IDs alike."""
    transfer = session.scalar(
        select(models.Transfer).where(models.Transfer.id == transfer_id, *sent_by(principal))
    )
    if transfer is None:
        raise not_found()
    return transfer


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
    view = serialization.load_transfer_view(session, transfer, replayed=replayed)
    session.commit()
    return view


def get_transfer(session: Session, principal: Principal, transfer_id: UUID) -> Transfer:
    return serialization.load_transfer_view(
        session, owned_transfer(session, principal, transfer_id)
    )


def list_transfers(session: Session, principal: Principal, page: PageParams) -> TransferList:
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
