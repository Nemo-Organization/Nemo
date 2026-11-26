"""Shared race harness for money tests on real PostgreSQL connections. Not a test module.

Each race starts its contenders as independent requests (separate TestClients on the
`bounded_app` fixture, whose pooled connections carry lock_timeout 5s / statement_timeout 15s)
or direct service calls on separate sessions. A gate transaction on an independent connection
holds the contested lock; `race` polls pg_stat_activity until every contender is waiting on a
lock, then releases the gate. Ordering never relies on a fixed sleep.
"""

import threading
import time
import uuid
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import AbstractContextManager, contextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Connection, Engine, text

from app.auth.service import ACTOR_COOKIE
from tests.money_support import Customer

BLOCKED = text(
    "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() "
    "AND wait_event_type = 'Lock' AND pid <> pg_backend_pid()"
)
GATED_TABLES = frozenset({"accounts", "transfers", "refunds"})


def wait_until(predicate: Callable[[], bool], timeout: float = 10.0) -> None:
    """Poll an observable database condition; ordering never relies on a fixed sleep."""
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError("condition not reached before the deadline")
        time.sleep(0.01)


def same_actor(app: FastAPI, customer: Customer) -> Customer:
    """Another browser presenting the customer's actor cookie: an independent request."""
    client = TestClient(app)
    client.cookies.set(ACTOR_COOKIE, customer.client.cookies.get(ACTOR_COOKIE))
    return Customer(client, customer.bootstrap, customer.csrf, customer.wallet_id)


@contextmanager
def row_gate(pg_engine: Engine, table: str, row_id: str) -> Iterator[Connection]:
    """Hold one row's lock in an independent transaction; commit it to release."""
    assert table in GATED_TABLES
    connection = pg_engine.connect()
    transaction = connection.begin()
    try:
        connection.execute(text("SET LOCAL lock_timeout = '5s'"))
        connection.execute(
            text(f"SELECT id FROM {table} WHERE id = :id FOR UPDATE"), {"id": uuid.UUID(row_id)}
        )
        yield connection
    finally:
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@contextmanager
def advisory_gate(pg_engine: Engine, key: int) -> Iterator[Connection]:
    """Hold a transaction-scoped advisory lock (as a restriction change would); commit releases."""
    connection = pg_engine.connect()
    transaction = connection.begin()
    try:
        connection.execute(text("SET LOCAL lock_timeout = '5s'"))
        connection.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})
        yield connection
    finally:
        if transaction.is_active:
            transaction.rollback()
        connection.close()


def race(
    pg_engine: Engine,
    gate: AbstractContextManager[Connection],
    contenders: list[Callable[[], Any]],
    *,
    before_release: Callable[[Connection], None] | None = None,
) -> list[Any]:
    """Start every contender behind a barrier while the gate holds its lock.

    Release only after every contender is observed waiting on a lock, so the contenders really
    overlap inside the database.
    """
    barrier = threading.Barrier(len(contenders), timeout=10)

    def start(contender: Callable[[], Any]) -> Any:
        barrier.wait()
        return contender()

    observer = pg_engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    try:
        with ThreadPoolExecutor(max_workers=len(contenders)) as pool:
            with gate as connection:
                futures = [pool.submit(start, contender) for contender in contenders]
                wait_until(lambda: observer.execute(BLOCKED).scalar_one() >= len(contenders))
                if before_release is not None:
                    before_release(connection)
                connection.commit()
            return [future.result(timeout=30) for future in futures]
    finally:
        observer.close()
