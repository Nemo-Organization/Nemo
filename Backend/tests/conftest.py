"""Disposable PostgreSQL fixtures.

Tests only ever use TEST_DATABASE_URL, never DATABASE_URL from .env. The schema reset below is
destructive, so it refuses any database whose name does not contain "test".
"""

import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.main import create_app
from app.settings import Settings

BACKEND_ROOT = Path(__file__).resolve().parents[1]
API = "/api/v1"
TEST_ORIGIN = "http://localhost:3000"


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


def guardian_test_settings(**overrides: Any) -> Settings:
    """Settings for an app bound to TEST_DATABASE_URL; never reads `.env`."""
    values: dict[str, Any] = {
        "app_env": "test",
        "database_url": require_test_database_url(),
        "public_app_origin": TEST_ORIGIN,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.fixture
def guardian_app(pg_engine: Engine) -> Iterator[FastAPI]:
    """A migrated-database app whose lifespan (engine) runs for the whole test."""
    app = create_app(guardian_test_settings())
    with TestClient(app):
        yield app


@pytest.fixture
def browser(guardian_app: FastAPI) -> Iterator[Callable[..., TestClient]]:
    """Factory of independent cookie jars, each simulating one browser on the shared app."""
    clients: list[TestClient] = []

    def open_browser(**options: Any) -> TestClient:
        client = TestClient(guardian_app, **options)
        clients.append(client)
        return client

    yield open_browser
    for client in clients:
        client.close()


def start_demo(client: TestClient, scenario: str = "MAIN_REFUND") -> dict[str, Any]:
    response = client.post(
        f"{API}/demo/sessions", json={"scenario": scenario}, headers={"Origin": TEST_ORIGIN}
    )
    assert response.status_code == 201, response.text
    return response.json()
