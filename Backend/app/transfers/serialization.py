"""Transfer and assessment DTO projection. Read-only: nothing here writes, flushes or commits.

`Transfer.assessment` is the latest persisted assessment of that transfer (assessed_at, then id,
descending), whether or not it is still within its five-minute lifetime, or null when none exists.
The nested recipient reuses the masked recipient projection, never the full account identifier.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.orm import Session

from app import models
from app.api import schemas
from app.demo.queries import recipient_view


def _utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


def assessment_view(row: models.RiskAssessment) -> schemas.RiskAssessment:
    return schemas.RiskAssessment(
        id=row.id,
        transfer_id=row.transfer_id,
        decision=row.decision,
        behavior_signal=row.behavior_signal,
        recipient_signal=row.recipient_signal,
        reasons=[schemas.RiskReason.model_validate(reason) for reason in row.reasons],
        policy_version=row.policy_version,
        assessed_at=_utc(row.assessed_at),
        expires_at=_utc(row.expires_at),
    )


def transfer_view(
    transfer: models.Transfer,
    recipient: models.Account,
    assessment: models.RiskAssessment | None,
    *,
    replayed: bool = False,
) -> schemas.Transfer:
    return schemas.Transfer(
        id=transfer.id,
        sender_account_id=transfer.sender_account_id,
        recipient=recipient_view(recipient),
        amount_vnd=transfer.amount_vnd,
        status=transfer.status,
        reserved_amount_vnd=transfer.reserved_amount_vnd,
        expires_at=_utc(transfer.expires_at),
        created_at=_utc(transfer.created_at),
        completed_at=None if transfer.completed_at is None else _utc(transfer.completed_at),
        assessment=None if assessment is None else assessment_view(assessment),
        review_reason=transfer.review_reason,
        replayed=replayed,
    )


def latest_assessments(
    session: Session, sandbox_id: UUID, transfer_ids: Sequence[UUID]
) -> dict[UUID, models.RiskAssessment]:
    """Newest assessment per transfer, in one query (DISTINCT ON transfer_id)."""
    if not transfer_ids:
        return {}
    rows = session.scalars(
        select(models.RiskAssessment)
        .where(
            models.RiskAssessment.sandbox_id == sandbox_id,
            models.RiskAssessment.transfer_id.in_(transfer_ids),
        )
        .order_by(
            models.RiskAssessment.transfer_id,
            models.RiskAssessment.assessed_at.desc(),
            models.RiskAssessment.id.desc(),
        )
        .ext(distinct_on(models.RiskAssessment.transfer_id))
    ).all()
    return {row.transfer_id: row for row in rows}


def transfer_views(
    session: Session, sandbox_id: UUID, transfers: Sequence[models.Transfer]
) -> list[schemas.Transfer]:
    """Project already-authorized transfers, loading recipients and latest assessments in bulk."""
    if not transfers:
        return []
    recipient_ids = {transfer.recipient_account_id for transfer in transfers}
    recipients = {
        account.id: account
        for account in session.scalars(
            select(models.Account).where(
                and_(
                    models.Account.sandbox_id == sandbox_id,
                    models.Account.id.in_(recipient_ids),
                )
            )
        )
    }
    assessments = latest_assessments(session, sandbox_id, [t.id for t in transfers])
    return [
        transfer_view(t, recipients[t.recipient_account_id], assessments.get(t.id))
        for t in transfers
    ]


def load_transfer_view(
    session: Session, transfer: models.Transfer, *, replayed: bool = False
) -> schemas.Transfer:
    (view,) = transfer_views(session, transfer.sandbox_id, [transfer])
    return view.model_copy(update={"replayed": replayed}) if replayed else view
