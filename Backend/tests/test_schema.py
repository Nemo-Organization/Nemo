"""The initial migration must reproduce docs/guardian/schema.sql exactly and enforce its rules."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import Engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
from app.db import Base
from tests.conftest import require_test_database_url

SCHEMA_SQL = Path(__file__).resolve().parents[2] / "docs/guardian/schema.sql"
REFERENCE_SCHEMA = "guardian_reference"


def public_tables(connection) -> list[str]:
    return list(
        connection.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
                "AND table_name <> 'alembic_version' ORDER BY table_name"
            )
        ).scalars()
    )


def catalog(connection, schema: str) -> dict[str, list[tuple]]:
    """Columns, constraints and indexes of one schema, with schema names removed."""
    connection.execute(text(f"SET LOCAL search_path TO {schema}"))
    columns = connection.execute(
        text(
            "SELECT table_name, ordinal_position, column_name, data_type, is_nullable, "
            "column_default FROM information_schema.columns "
            "WHERE table_schema = :schema AND table_name <> 'alembic_version' "
            "ORDER BY table_name, ordinal_position"
        ),
        {"schema": schema},
    ).all()
    constraints = connection.execute(
        text(
            "SELECT rel.relname, con.conname, con.contype, pg_get_constraintdef(con.oid) "
            "FROM pg_constraint con JOIN pg_class rel ON rel.oid = con.conrelid "
            "JOIN pg_namespace ns ON ns.oid = rel.relnamespace "
            "WHERE ns.nspname = :schema AND rel.relname <> 'alembic_version' "
            "ORDER BY rel.relname, con.conname"
        ),
        {"schema": schema},
    ).all()
    indexes = connection.execute(
        text(
            "SELECT tablename, indexname, replace(indexdef, :prefix, '') FROM pg_indexes "
            "WHERE schemaname = :schema AND tablename <> 'alembic_version' "
            "ORDER BY tablename, indexname"
        ),
        {"schema": schema, "prefix": f"{schema}."},
    ).all()
    return {
        "columns": [tuple(row) for row in columns],
        "constraints": [tuple(row) for row in constraints],
        "indexes": [tuple(row) for row in indexes],
    }


def test_initial_migration_has_19_tables_and_161_columns(pg_engine: Engine):
    with pg_engine.connect() as connection:
        tables = public_tables(connection)
        columns = connection.execute(
            text(
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name <> 'alembic_version'"
            )
        ).scalar_one()
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()

    assert len(tables) == 19
    assert columns == 161
    assert revision == "0001_guardian"


def test_migration_matches_schema_sql(pg_engine: Engine):
    url = make_url(require_test_database_url()).set(drivername="postgresql")
    with psycopg.connect(url.render_as_string(hide_password=False), autocommit=True) as raw:
        raw.execute(f"DROP SCHEMA IF EXISTS {REFERENCE_SCHEMA} CASCADE")
        raw.execute(f"CREATE SCHEMA {REFERENCE_SCHEMA}")
        raw.execute(f"SET search_path TO {REFERENCE_SCHEMA}, public")
        raw.execute(SCHEMA_SQL.read_text(encoding="utf-8"))
    try:
        with pg_engine.begin() as connection:
            migrated = catalog(connection, "public")
        with pg_engine.begin() as connection:
            reference = catalog(connection, REFERENCE_SCHEMA)
    finally:
        with pg_engine.begin() as connection:
            connection.execute(text(f"DROP SCHEMA IF EXISTS {REFERENCE_SCHEMA} CASCADE"))

    assert migrated["columns"] == reference["columns"]
    assert migrated["constraints"] == reference["constraints"]
    assert migrated["indexes"] == reference["indexes"]


def test_models_match_migrated_columns(pg_engine: Engine):
    with pg_engine.connect() as connection:
        tables = public_tables(connection)
        differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)

    assert sorted(Base.metadata.tables) == tables
    assert differences == []


def make_sandbox(session: Session) -> models.Sandbox:
    sandbox = models.Sandbox(scenario="MAIN_REFUND")
    session.add(sandbox)
    session.flush()
    return sandbox


def make_customer(session: Session, sandbox: models.Sandbox) -> models.Actor:
    actor = models.Actor(sandbox_id=sandbox.id, role="CUSTOMER", display_name="Linh")
    session.add(actor)
    session.flush()
    return actor


def make_account(session: Session, sandbox: models.Sandbox, **values) -> models.Account:
    account = models.Account(
        sandbox_id=sandbox.id,
        bank_code="NEMO",
        account_identifier=values.pop("account_identifier", uuid.uuid4().hex[:12]),
        display_name="Synthetic account",
        **values,
    )
    session.add(account)
    session.flush()
    return account


def assert_violation(session: Session, row, error_type, constraint: str | None = None) -> None:
    with pytest.raises(IntegrityError) as caught:
        with session.begin_nested():
            session.add(row)
            session.flush()
    assert isinstance(caught.value.orig, error_type)
    if constraint is not None:
        assert caught.value.orig.diag.constraint_name == constraint


def test_cross_sandbox_fk_rejected(db_session: Session):
    first, second = make_sandbox(db_session), make_sandbox(db_session)
    customer = make_customer(db_session, first)

    foreign_owner = models.Account(
        sandbox_id=second.id,
        owner_actor_id=customer.id,
        bank_code="NEMO",
        account_identifier="foreign-owner",
        display_name="Wrong sandbox",
    )
    assert_violation(db_session, foreign_owner, psycopg.errors.ForeignKeyViolation)

    sender = make_account(db_session, first, owner_actor_id=customer.id, balance_vnd=100_000)
    other_recipient = make_account(db_session, second)
    transfer = models.Transfer(
        sandbox_id=first.id,
        sender_account_id=sender.id,
        recipient_account_id=other_recipient.id,
        client_request_id=uuid.uuid4(),
        amount_vnd=20_000,
    )
    assert_violation(db_session, transfer, psycopg.errors.ForeignKeyViolation)


def test_reservation_exceeds_balance_rejected(db_session: Session):
    sandbox = make_sandbox(db_session)
    overdrawn = models.Account(
        sandbox_id=sandbox.id,
        bank_code="NEMO",
        account_identifier="over-reserved",
        display_name="Over reserved",
        balance_vnd=100_000,
        reserved_vnd=100_001,
    )
    assert_violation(db_session, overdrawn, psycopg.errors.CheckViolation, "accounts_check")

    account = make_account(db_session, sandbox, balance_vnd=100_000, reserved_vnd=100_000)
    assert account.reserved_vnd == account.balance_vnd


def test_nullable_fee_requires_provenance(db_session: Session):
    sandbox = make_sandbox(db_session)
    customer = make_customer(db_session, sandbox)

    def order(reference: str, **fee) -> models.Order:
        return models.Order(
            sandbox_id=sandbox.id,
            customer_actor_id=customer.id,
            order_reference=reference,
            merchant_name="Synthetic shop",
            original_amount_vnd=500_000,
            **fee,
        )

    unknown_fee = order("SHOP-UNKNOWN")
    db_session.add(unknown_fee)
    db_session.flush()
    assert unknown_fee.return_fee_vnd is None

    assert_violation(
        db_session,
        order("SHOP-NO-SOURCE", return_fee_vnd=0),
        psycopg.errors.CheckViolation,
        "orders_check",
    )

    verified = order(
        "SHOP-VERIFIED",
        return_fee_vnd=0,
        fee_source="Synthetic merchant fee confirmation",
        fee_verified_at=datetime.now(UTC),
    )
    db_session.add(verified)
    db_session.flush()
    assert verified.return_fee_vnd == 0


def test_duplicate_ledger_and_active_restriction_rejected(db_session: Session):
    sandbox = make_sandbox(db_session)
    operator = models.Actor(sandbox_id=sandbox.id, role="OPERATOR", display_name="Ops")
    db_session.add(operator)
    account = make_account(db_session, sandbox, balance_vnd=100_000)

    db_session.add(
        models.LedgerEntry(
            sandbox_id=sandbox.id, account_id=account.id, kind="OPENING", amount_vnd=100_000
        )
    )
    db_session.flush()
    assert_violation(
        db_session,
        models.LedgerEntry(
            sandbox_id=sandbox.id, account_id=account.id, kind="OPENING", amount_vnd=5_000
        ),
        psycopg.errors.UniqueViolation,
        "one_opening_per_account",
    )

    def restriction(status: str = "ACTIVE", **revocation) -> models.RecipientRestriction:
        return models.RecipientRestriction(
            sandbox_id=sandbox.id,
            recipient_account_id=account.id,
            action="HOLD",
            status=status,
            reason="Reviewed synthetic near-miss reports",
            created_by=operator.id,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            **revocation,
        )

    db_session.add(
        restriction(
            "REVOKED",
            revoked_by=operator.id,
            revoked_at=datetime.now(UTC),
            revocation_reason="Superseded",
        )
    )
    db_session.add(restriction())
    db_session.flush()
    assert_violation(
        db_session, restriction(), psycopg.errors.UniqueViolation, "one_active_restriction"
    )
