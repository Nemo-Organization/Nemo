"""SQLAlchemy mappings for the 19 Guardian tables (docs/guardian/schema.sql).

The migration `0001_guardian` is the schema authority. These mappings mirror its columns, types,
nullability, defaults, keys and indexes so the ORM and Alembic comparisons agree. CHECK constraints
live only in the migration; tests prove PostgreSQL enforces them. Never use `create_all`.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    PrimaryKeyConstraint,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

GEN_UUID = text("gen_random_uuid()")
NOW = text("now()")


def _id() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, server_default=GEN_UUID)


def _sandbox_id() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True), ForeignKey("sandboxes.id", ondelete="CASCADE"), nullable=False
    )


def _uuid(nullable: bool = False) -> Any:
    return mapped_column(UUID(as_uuid=True), nullable=nullable)


def _text(nullable: bool = False, **kwargs: Any) -> Any:
    return mapped_column(Text, nullable=nullable, **kwargs)


def _vnd(nullable: bool = False, **kwargs: Any) -> Any:
    return mapped_column(BigInteger, nullable=nullable, **kwargs)


def _time(nullable: bool = False, **kwargs: Any) -> Any:
    return mapped_column(DateTime(timezone=True), nullable=nullable, **kwargs)


def _scoped_fk(columns: list[str], table: str) -> ForeignKeyConstraint:
    """Composite (sandbox_id, x) -> table(sandbox_id, id) keeps every reference in one sandbox."""
    return ForeignKeyConstraint(["sandbox_id", *columns], [f"{table}.sandbox_id", f"{table}.id"])


class Sandbox(Base):
    __tablename__ = "sandboxes"

    id: Mapped[uuid.UUID] = _id()
    scenario: Mapped[str] = _text()
    created_at: Mapped[datetime] = _time(server_default=NOW)
    expires_at: Mapped[datetime] = _time(server_default=text("now() + '24:00:00'::interval"))


class Actor(Base):
    __tablename__ = "actors"
    __table_args__ = (UniqueConstraint("sandbox_id", "id"),)

    id: Mapped[uuid.UUID] = _id()
    sandbox_id: Mapped[uuid.UUID] = _sandbox_id()
    role: Mapped[str] = _text()
    display_name: Mapped[str] = _text()


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (_scoped_fk(["actor_id"], "actors"),)

    id: Mapped[uuid.UUID] = _id()
    sandbox_id: Mapped[uuid.UUID] = _sandbox_id()
    actor_id: Mapped[uuid.UUID | None] = _uuid(nullable=True)
    kind: Mapped[str] = _text()
    token_hash: Mapped[str] = _text(unique=True)
    csrf_hash: Mapped[str] = _text()
    expires_at: Mapped[datetime] = _time()
    revoked_at: Mapped[datetime | None] = _time(nullable=True)


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("sandbox_id", "id"),
        UniqueConstraint("sandbox_id", "bank_code", "account_identifier"),
        _scoped_fk(["owner_actor_id"], "actors"),
    )

    id: Mapped[uuid.UUID] = _id()
    sandbox_id: Mapped[uuid.UUID] = _sandbox_id()
    owner_actor_id: Mapped[uuid.UUID | None] = _uuid(nullable=True)
    bank_code: Mapped[str] = _text()
    account_identifier: Mapped[str] = _text()
    display_name: Mapped[str] = _text()
    balance_vnd: Mapped[int] = _vnd(server_default=text("0"))
    reserved_vnd: Mapped[int] = _vnd(server_default=text("0"))
    created_at: Mapped[datetime] = _time(server_default=NOW)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("sandbox_id", "id"),
        UniqueConstraint("sandbox_id", "order_reference"),
        _scoped_fk(["customer_actor_id"], "actors"),
    )

    id: Mapped[uuid.UUID] = _id()
    sandbox_id: Mapped[uuid.UUID] = _sandbox_id()
    customer_actor_id: Mapped[uuid.UUID] = _uuid()
    order_reference: Mapped[str] = _text()
    merchant_name: Mapped[str] = _text()
    original_amount_vnd: Mapped[int] = _vnd()
    return_fee_vnd: Mapped[int | None] = _vnd(nullable=True)
    fee_source: Mapped[str | None] = _text(nullable=True)
    fee_verified_at: Mapped[datetime | None] = _time(nullable=True)


class Refund(Base):
    __tablename__ = "refunds"
    __table_args__ = (
        UniqueConstraint("sandbox_id", "id"),
        UniqueConstraint("sandbox_id", "order_id"),
        _scoped_fk(["order_id"], "orders"),
        _scoped_fk(["account_id"], "accounts"),
    )

    id: Mapped[uuid.UUID] = _id()
    sandbox_id: Mapped[uuid.UUID] = _sandbox_id()
    order_id: Mapped[uuid.UUID] = _uuid()
    account_id: Mapped[uuid.UUID] = _uuid()
    amount_vnd: Mapped[int] = _vnd()
    status: Mapped[str] = _text(server_default=text("'APPROVED'::text"))
    settled_at: Mapped[datetime | None] = _time(nullable=True)


class Transfer(Base):
    __tablename__ = "transfers"
    __table_args__ = (
        UniqueConstraint("sandbox_id", "id"),
        UniqueConstraint("sandbox_id", "sender_account_id", "client_request_id"),
        _scoped_fk(["sender_account_id"], "accounts"),
        _scoped_fk(["recipient_account_id"], "accounts"),
        _scoped_fk(["reviewed_by"], "actors"),
        ForeignKeyConstraint(
            ["sandbox_id", "cleared_restriction_id"],
            ["recipient_restrictions.sandbox_id", "recipient_restrictions.id"],
            name="cleared_restriction_scope_fk",
        ),
        Index(
            "transfers_sender_history",
            "sandbox_id",
            "sender_account_id",
            text("created_at DESC"),
            postgresql_where=text("status = 'SUCCEEDED'"),
        ),
        Index(
            "transfers_due_expiry",
            "expires_at",
            postgresql_where=text("status IN ('DRAFT', 'RISK_HELD', 'READY')"),
        ),
    )

    id: Mapped[uuid.UUID] = _id()
    sandbox_id: Mapped[uuid.UUID] = _sandbox_id()
    sender_account_id: Mapped[uuid.UUID] = _uuid()
    recipient_account_id: Mapped[uuid.UUID] = _uuid()
    client_request_id: Mapped[uuid.UUID] = _uuid()
    amount_vnd: Mapped[int] = _vnd()
    status: Mapped[str] = _text(server_default=text("'DRAFT'::text"))
    reserved_amount_vnd: Mapped[int] = _vnd(server_default=text("0"))
    created_at: Mapped[datetime] = _time(server_default=NOW)
    expires_at: Mapped[datetime] = _time(server_default=text("now() + '00:30:00'::interval"))
    held_at: Mapped[datetime | None] = _time(nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = _uuid(nullable=True)
    review_reason: Mapped[str | None] = _text(nullable=True)
    cleared_restriction_id: Mapped[uuid.UUID | None] = _uuid(nullable=True)
    completed_at: Mapped[datetime | None] = _time(nullable=True)


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        _scoped_fk(["account_id"], "accounts"),
        _scoped_fk(["transfer_id"], "transfers"),
        _scoped_fk(["refund_id"], "refunds"),
        UniqueConstraint("sandbox_id", "transfer_id", "kind"),
        UniqueConstraint("sandbox_id", "refund_id"),
        Index(
            "one_opening_per_account",
            "sandbox_id",
            "account_id",
            unique=True,
            postgresql_where=text("kind = 'OPENING'"),
        ),
    )

    id: Mapped[uuid.UUID] = _id()
    sandbox_id: Mapped[uuid.UUID] = _sandbox_id()
    account_id: Mapped[uuid.UUID] = _uuid()
    transfer_id: Mapped[uuid.UUID | None] = _uuid(nullable=True)
    refund_id: Mapped[uuid.UUID | None] = _uuid(nullable=True)
    kind: Mapped[str] = _text()
    amount_vnd: Mapped[int] = _vnd()
    created_at: Mapped[datetime] = _time(server_default=NOW)


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    __table_args__ = (
        UniqueConstraint("sandbox_id", "id"),
        _scoped_fk(["transfer_id"], "transfers"),
        Index("risk_assessments_transfer", "sandbox_id", "transfer_id", text("assessed_at DESC")),
    )

    id: Mapped[uuid.UUID] = _id()
    sandbox_id: Mapped[uuid.UUID] = _sandbox_id()
    transfer_id: Mapped[uuid.UUID] = _uuid()
    decision: Mapped[str] = _text()
    behavior_signal: Mapped[str] = _text()
    recipient_signal: Mapped[str] = _text()
    policy_version: Mapped[str] = _text()
    facts_fingerprint: Mapped[str] = _text()
    reasons: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    facts: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    assessed_at: Mapped[datetime] = _time(server_default=NOW)
    expires_at: Mapped[datetime] = _time(server_default=text("now() + '00:05:00'::interval"))


class AiRun(Base):
    __tablename__ = "ai_runs"
    __table_args__ = (
        UniqueConstraint("sandbox_id", "id"),
        UniqueConstraint("sandbox_id", "owner_actor_id", "client_request_id"),
        _scoped_fk(["owner_actor_id"], "actors"),
        _scoped_fk(["transfer_id"], "transfers"),
        _scoped_fk(["order_id"], "orders"),
        Index("ai_runs_actor", "sandbox_id", "owner_actor_id", text("created_at DESC")),
    )

    id: Mapped[uuid.UUID] = _id()
    sandbox_id: Mapped[uuid.UUID] = _sandbox_id()
    owner_actor_id: Mapped[uuid.UUID] = _uuid()
    client_request_id: Mapped[uuid.UUID] = _uuid()
    kind: Mapped[str] = _text()
    transfer_id: Mapped[uuid.UUID | None] = _uuid(nullable=True)
    order_id: Mapped[uuid.UUID | None] = _uuid(nullable=True)
    input_text: Mapped[str | None] = _text(nullable=True)
    input_digest: Mapped[str] = _text()
    evidence_object_key: Mapped[str | None] = _text(nullable=True)
    evidence_mime: Mapped[str | None] = _text(nullable=True)
    status: Mapped[str] = _text(server_default=text("'PENDING'::text"))
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    provider: Mapped[str | None] = _text(nullable=True)
    model: Mapped[str | None] = _text(nullable=True)
    prompt_version: Mapped[str] = _text()
    error_code: Mapped[str | None] = _text(nullable=True)
    created_at: Mapped[datetime] = _time(server_default=NOW)
    finished_at: Mapped[datetime | None] = _time(nullable=True)


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("sandbox_id", "id"),
        UniqueConstraint("sandbox_id", "reporter_actor_id", "client_request_id"),
        _scoped_fk(["reporter_actor_id"], "actors"),
        _scoped_fk(["recipient_account_id"], "accounts"),
        _scoped_fk(["transfer_id"], "transfers"),
        _scoped_fk(["analysis_id"], "ai_runs"),
        _scoped_fk(["reviewed_by"], "actors"),
        Index("reports_queue", "sandbox_id", "status", "created_at"),
        Index("reports_recipient", "sandbox_id", "recipient_account_id"),
    )

    id: Mapped[uuid.UUID] = _id()
    sandbox_id: Mapped[uuid.UUID] = _sandbox_id()
    reporter_actor_id: Mapped[uuid.UUID] = _uuid()
    client_request_id: Mapped[uuid.UUID] = _uuid()
    recipient_account_id: Mapped[uuid.UUID] = _uuid()
    transfer_id: Mapped[uuid.UUID | None] = _uuid(nullable=True)
    analysis_id: Mapped[uuid.UUID | None] = _uuid(nullable=True)
    narrative: Mapped[str] = _text()
    status: Mapped[str] = _text(server_default=text("'RECEIVED'::text"))
    reviewed_by: Mapped[uuid.UUID | None] = _uuid(nullable=True)
    resolution_reason: Mapped[str | None] = _text(nullable=True)
    created_at: Mapped[datetime] = _time(server_default=NOW)


class Partner(Base):
    __tablename__ = "partners"
    __table_args__ = (UniqueConstraint("sandbox_id", "id"), UniqueConstraint("sandbox_id", "name"))

    id: Mapped[uuid.UUID] = _id()
    sandbox_id: Mapped[uuid.UUID] = _sandbox_id()
    name: Mapped[str] = _text()


class DataBatch(Base):
    __tablename__ = "data_batches"
    __table_args__ = (UniqueConstraint("sandbox_id", "id"), _scoped_fk(["partner_id"], "partners"))

    id: Mapped[uuid.UUID] = _id()
    sandbox_id: Mapped[uuid.UUID] = _sandbox_id()
    partner_id: Mapped[uuid.UUID] = _uuid()
    label: Mapped[str] = _text()
    issued_at: Mapped[datetime] = _time()


class TraceReference(Base):
    __tablename__ = "trace_references"
    __table_args__ = (
        UniqueConstraint("sandbox_id", "code"),
        UniqueConstraint("sandbox_id", "id"),
        _scoped_fk(["batch_id"], "data_batches"),
        _scoped_fk(["order_id"], "orders"),
        Index("trace_references_batch", "sandbox_id", "batch_id"),
    )

    id: Mapped[uuid.UUID] = _id()
    sandbox_id: Mapped[uuid.UUID] = _sandbox_id()
    batch_id: Mapped[uuid.UUID] = _uuid()
    order_id: Mapped[uuid.UUID] = _uuid()
    code: Mapped[str] = _text()


class PartnerAccessEvent(Base):
    __tablename__ = "partner_access_events"
    __table_args__ = (
        UniqueConstraint("sandbox_id", "id"),
        _scoped_fk(["partner_id"], "partners"),
        _scoped_fk(["batch_id"], "data_batches"),
        Index("access_batch_time", "sandbox_id", "batch_id", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = _id()
    sandbox_id: Mapped[uuid.UUID] = _sandbox_id()
    partner_id: Mapped[uuid.UUID] = _uuid()
    batch_id: Mapped[uuid.UUID] = _uuid()
    action: Mapped[str] = _text()
    occurred_at: Mapped[datetime] = _time()


class RecipientRestriction(Base):
    __tablename__ = "recipient_restrictions"
    __table_args__ = (
        UniqueConstraint("sandbox_id", "id"),
        _scoped_fk(["recipient_account_id"], "accounts"),
        _scoped_fk(["created_by"], "actors"),
        _scoped_fk(["revoked_by"], "actors"),
        Index(
            "one_active_restriction",
            "sandbox_id",
            "recipient_account_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

    id: Mapped[uuid.UUID] = _id()
    sandbox_id: Mapped[uuid.UUID] = _sandbox_id()
    recipient_account_id: Mapped[uuid.UUID] = _uuid()
    action: Mapped[str] = _text()
    status: Mapped[str] = _text(server_default=text("'ACTIVE'::text"))
    reason: Mapped[str] = _text()
    created_by: Mapped[uuid.UUID] = _uuid()
    created_at: Mapped[datetime] = _time(server_default=NOW)
    expires_at: Mapped[datetime] = _time()
    revoked_by: Mapped[uuid.UUID | None] = _uuid(nullable=True)
    revoked_at: Mapped[datetime | None] = _time(nullable=True)
    revocation_reason: Mapped[str | None] = _text(nullable=True)


class RestrictionReport(Base):
    __tablename__ = "restriction_reports"
    __table_args__ = (
        PrimaryKeyConstraint("sandbox_id", "restriction_id", "report_id"),
        _scoped_fk(["restriction_id"], "recipient_restrictions"),
        _scoped_fk(["report_id"], "reports"),
    )

    sandbox_id: Mapped[uuid.UUID] = _sandbox_id()
    restriction_id: Mapped[uuid.UUID] = _uuid()
    report_id: Mapped[uuid.UUID] = _uuid()


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("sandbox_id", "id"),
        UniqueConstraint("sandbox_id", "source_report_id", "batch_id", "recipient_actor_id"),
        _scoped_fk(["recipient_actor_id"], "actors"),
        _scoped_fk(["batch_id"], "data_batches"),
        _scoped_fk(["source_report_id"], "reports"),
        _scoped_fk(["created_by"], "actors"),
        Index(
            "notifications_customer", "sandbox_id", "recipient_actor_id", text("created_at DESC")
        ),
    )

    id: Mapped[uuid.UUID] = _id()
    sandbox_id: Mapped[uuid.UUID] = _sandbox_id()
    recipient_actor_id: Mapped[uuid.UUID] = _uuid()
    batch_id: Mapped[uuid.UUID] = _uuid()
    source_report_id: Mapped[uuid.UUID] = _uuid()
    title: Mapped[str] = _text()
    body: Mapped[str] = _text()
    created_by: Mapped[uuid.UUID] = _uuid()
    created_at: Mapped[datetime] = _time(server_default=NOW)
    read_at: Mapped[datetime | None] = _time(nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        _scoped_fk(["actor_id"], "actors"),
        Index("audit_events_timeline", "sandbox_id", text("created_at DESC")),
    )

    id: Mapped[uuid.UUID] = _id()
    sandbox_id: Mapped[uuid.UUID] = _sandbox_id()
    actor_id: Mapped[uuid.UUID | None] = _uuid(nullable=True)
    actor_kind: Mapped[str] = _text()
    event_type: Mapped[str] = _text()
    target_type: Mapped[str] = _text()
    target_id: Mapped[uuid.UUID | None] = _uuid(nullable=True)
    request_id: Mapped[str] = _text()
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = _time(server_default=NOW)
