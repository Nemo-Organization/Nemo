"""Disposable PostgreSQL fixtures.

Tests only ever use TEST_DATABASE_URL, never DATABASE_URL from .env. The schema reset below is
destructive, so it refuses any database whose name does not contain "test".
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def require_test_database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to a dedicated, disposable PostgreSQL test database")
    database = make_url(url).database or ""
    if "test" not in database.lower():
        raise RuntimeError(
            "Refusing to reset TEST_DATABASE_URL: its database name must contain 'test'."
        )
    return url


def alembic_config() -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    config.attributes["configure_logger"] = False
    return config


def upgrade_to_head(engine: Engine) -> None:
    with engine.begin() as connection:
        config = alembic_config()
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


@pytest.fixture(scope="session")
def pg_engine() -> Iterator[Engine]:
    engine = create_engine(require_test_database_url(), hide_parameters=True)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    upgrade_to_head(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(pg_engine: Engine) -> Iterator[Session]:
    """A session whose work is always rolled back; commits inside become savepoints."""
    connection = pg_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
