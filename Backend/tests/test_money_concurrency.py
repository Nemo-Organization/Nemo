"""Task 7: money commands racing on real PostgreSQL connections.

Each race starts its contenders as independent requests (separate TestClients on one app whose
pooled connections carry lock_timeout 5s / statement_timeout 15s) or direct service calls on
separate sessions. A gate transaction on an independent connection holds the contested row lock;
the test polls pg_stat_activity until every contender is waiting on a lock, then releases the
gate. Ordering never relies on a fixed sleep. After each race the cached money invariants are
checked directly in SQL.
"""

import threading
import time
import uuid
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import AbstractContextManager, contextmanager
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Connection, Engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.main import create_app
from app.transfers.expiry import expire_due_transfers
from app.transfers.locking import recipient_policy_key
from tests.conftest import guardian_test_settings, require_test_database_url
from tests.money_support import (
    ME,
    TERMINAL_EVENTS,
    TRANSFERS,
    Customer,
    as_actor,
    assert_money_invariants,
    audit_of,
    error_code,
    error_of,
    ledger_of,
    money,
    open_sandbox,
    pass_deadline,
    transfer_row,
    writes,
)

BLOCKED = text(
    "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() "
    "AND wait_event_type = 'Lock' AND pid <> pg_backend_pid()"
)


@pytest.fixture
def bounded_app(pg_engine: Engine) -> Iterator[FastAPI]:
    """An app whose pooled connections carry bounded lock and statement timeouts."""
    url = make_url(require_test_database_url()).update_query_dict(
        {"options": "-c lock_timeout=5000 -c statement_timeout=15000"}
    )
    app = create_app(guardian_test_settings(database_url=url.render_as_string(False)))
    with TestClient(app):
        with app.state.db_engine.connect() as connection:
            assert connection.execute(text("SHOW lock_timeout")).scalar_one() == "5s"
        yield app


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
    client.cookies.set("guardian_session", customer.client.cookies.get("guardian_session"))
    return Customer(client, customer.bootstrap, customer.csrf, customer.wallet_id)


@contextmanager
def row_gate(pg_engine: Engine, table: str, row_id: str) -> Iterator[Connection]:
    """Hold one row's lock in an independent transaction; commit it to release."""
    assert table in {"accounts", "transfers"}
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


def terminal_events(pg_engine: Engine, transfer_id: str) -> list[str]:
    return [
        e.event_type for e in audit_of(pg_engine, transfer_id) if e.event_type in TERMINAL_EVENTS
    ]


@pytest.mark.parametrize("symbol", ["CAFE", "RISK_RECIPIENT"], ids=["allow", "hold"])
def test_concurrent_confirm_is_once(bounded_app: FastAPI, pg_engine: Engine, symbol: str):
    linh = open_sandbox(TestClient(bounded_app))
    draft = linh.draft(symbol, 20_000)
    browsers = [same_actor(bounded_app, linh) for _ in range(2)]

    # The first confirm takes the recipient lock and waits on the gated sender account; the
    # second waits on the recipient lock.
    responses = race(
        pg_engine,
        row_gate(pg_engine, "accounts", linh.wallet_id),
        [lambda b=b: b.confirm(draft["id"]) for b in browsers],
    )

    assert [r.status_code for r in responses] == [200, 200], [r.text for r in responses]
    first, second = (r.json() for r in responses)
    assert first == second, "both callers see the one stored outcome"
    if symbol == "CAFE":
        assert first["status"] == "SUCCEEDED"
        assert len(ledger_of(pg_engine, draft["id"])) == 2, "exactly one debit/credit pair"
        assert money(linh.wallet()) == (9_980_000, 0, 9_980_000)
        assert terminal_events(pg_engine, draft["id"]) == ["TRANSFER_SUCCEEDED"]
    else:
        assert (first["status"], first["reserved_amount_vnd"]) == ("RISK_HELD", 20_000)
        assert ledger_of(pg_engine, draft["id"]) == []
        assert money(linh.wallet()) == (10_000_000, 20_000, 9_980_000), "reserved once"
        assert [e.event_type for e in audit_of(pg_engine, draft["id"])] == ["TRANSFER_HELD"]
    assert_money_invariants(pg_engine, linh.sandbox_id)
    for b in browsers:
        b.client.close()


@pytest.mark.parametrize(
    "second_symbol", ["NEW_RECIPIENT", "RISK_RECIPIENT"], ids=["two-debits", "debit-vs-hold"]
)
def test_competing_spends_cannot_overspend(
    bounded_app: FastAPI, pg_engine: Engine, second_symbol: str
):
    binh = as_actor(open_sandbox(TestClient(bounded_app)), "Binh")
    assert money(binh.wallet()) == (5_000_000, 0, 5_000_000)
    # Binh has no history (no behavioral warning); 3,000,000 + 3,000,000 exceeds 5,000,000.
    drafts = [binh.draft("CAFE", 3_000_000), binh.draft(second_symbol, 3_000_000)]
    browsers = [same_actor(bounded_app, binh) for _ in drafts]

    # Different recipients take different recipient locks; both wait on the sender account.
    responses = race(
        pg_engine,
        row_gate(pg_engine, "accounts", binh.wallet_id),
        [lambda b=b, d=d: b.confirm(d["id"]) for b, d in zip(browsers, drafts, strict=True)],
    )

    statuses = sorted(r.status_code for r in responses)
    assert statuses == [200, 409], [r.text for r in responses]
    winner = next(r for r in responses if r.status_code == 200).json()
    loser = next(r for r in responses if r.status_code == 409)
    assert error_code(loser) == "INSUFFICIENT_FUNDS"
    loser_id = next(d["id"] for d in drafts if d["id"] != winner["id"])
    assert transfer_row(pg_engine, loser_id).status == "DRAFT", "no partial write"
    assert ledger_of(pg_engine, loser_id) == []
    if winner["status"] == "SUCCEEDED":
        assert money(binh.wallet()) == (2_000_000, 0, 2_000_000)
    else:
        assert winner["status"] == "RISK_HELD"
        assert money(binh.wallet()) == (5_000_000, 3_000_000, 2_000_000)
    assert_money_invariants(pg_engine, binh.sandbox_id)
    for b in browsers:
        b.client.close()


@pytest.mark.parametrize("case", ["draft", "held", "held-past-deadline"])
def test_confirm_cancel_expiry_race(bounded_app: FastAPI, pg_engine: Engine, case: str):
    linh = open_sandbox(TestClient(bounded_app))
    # A bystander hold makes a double release visible as reserved drift, not only as a
    # violated CHECK constraint.
    bystander = linh.held("RISK_RECIPIENT", 30_000)
    if case == "draft":
        target = linh.draft("CAFE", 20_000)
    else:
        target = linh.held("RISK_RECIPIENT", 20_000)
    if case == "held-past-deadline":
        pass_deadline(pg_engine, target["id"])
    confirmer, canceller = (same_actor(bounded_app, linh) for _ in range(2))

    def sweep() -> int:
        with Session(bounded_app.state.db_engine) as session:
            return expire_due_transfers(session, linh.sandbox_id)

    contenders: list[Callable[[], Any]] = [
        lambda: confirmer.confirm(target["id"]),
        lambda: canceller.cancel(target["id"]),
    ]
    if case == "held-past-deadline":
        contenders.append(sweep)  # its discovery sees the due row, then waits on the account

    results = race(pg_engine, row_gate(pg_engine, "accounts", linh.wallet_id), contenders)
    confirmed, canceled = results[0], results[1]

    final = transfer_row(pg_engine, target["id"])
    events = terminal_events(pg_engine, target["id"])
    assert len(events) <= 1 and final.status not in {"DRAFT", "RISK_HELD", "READY"}
    if case == "draft":
        assert final.status in {"SUCCEEDED", "CANCELED"}
        winner, loser = (
            (confirmed, canceled) if final.status == "SUCCEEDED" else (canceled, confirmed)
        )
        assert winner.status_code == 200 and winner.json()["status"] == final.status
        assert (loser.status_code, error_code(loser)) == (409, "STATE_CONFLICT"), loser.text
        assert error_of(loser)["current_transfer"] == winner.json()
        assert len(ledger_of(pg_engine, target["id"])) == (2 if final.status == "SUCCEEDED" else 0)
        assert events == [f"TRANSFER_{final.status}"]
    elif case == "held":
        assert final.status == "CANCELED"
        assert canceled.status_code == 200 and canceled.json()["status"] == "CANCELED"
        if confirmed.status_code == 200:  # confirm ran first and returned the unchanged hold
            assert confirmed.json()["status"] == "RISK_HELD"
        else:
            assert error_code(confirmed) == "STATE_CONFLICT"
            assert error_of(confirmed)["current_transfer"] == canceled.json()
        assert events == ["TRANSFER_CANCELED"]
    else:
        assert final.status == "EXPIRED"
        for response in (confirmed, canceled):
            assert (response.status_code, error_code(response)) == (409, "STATE_CONFLICT")
            assert error_of(response)["current_transfer"]["status"] == "EXPIRED"
        assert results[2] in {0, 1}
        assert events == ["TRANSFER_EXPIRED"], "expired and released exactly once"
    assert ledger_of(pg_engine, bystander["id"]) == []
    assert money(linh.wallet())[1] == 30_000, "only the bystander's reservation remains"
    assert_money_invariants(pg_engine, linh.sandbox_id)
    for b in (confirmer, canceller):
        b.client.close()


def test_deadline_passing_while_queued_never_executes(bounded_app: FastAPI, pg_engine: Engine):
    linh = open_sandbox(TestClient(bounded_app))
    draft = linh.draft("CAFE", 20_000)
    queued = same_actor(bounded_app, linh)

    def deadline_now(gate: Connection) -> None:
        # The deadline passes after the confirm request started and while it waits in line.
        gate.execute(
            text("UPDATE transfers SET expires_at = clock_timestamp() WHERE id = :id"),
            {"id": uuid.UUID(draft["id"])},
        )

    (response,) = race(
        pg_engine,
        row_gate(pg_engine, "accounts", linh.wallet_id),
        [lambda: queued.confirm(draft["id"])],
        before_release=deadline_now,
    )

    assert (response.status_code, error_code(response)) == (409, "STATE_CONFLICT"), response.text
    assert error_of(response)["current_transfer"]["status"] == "EXPIRED"
    assert ledger_of(pg_engine, draft["id"]) == []
    assert money(linh.wallet()) == (10_000_000, 0, 10_000_000)
    assert_money_invariants(pg_engine, linh.sandbox_id)
    queued.client.close()


def test_reads_and_drafts_do_not_wait_for_confirm_locks(bounded_app: FastAPI, pg_engine: Engine):
    """A confirm holding the sender and recipient account locks blocks neither a new draft
    (whose foreign-key checks take FOR KEY SHARE on both accounts) nor a read with nothing due.
    """
    linh = open_sandbox(TestClient(bounded_app))
    draft = linh.draft("CAFE", 20_000)
    confirmer, reader = same_actor(bounded_app, linh), same_actor(bounded_app, linh)
    outcome: dict[str, Any] = {}

    def while_confirm_holds_accounts(_: Connection) -> None:
        outcome["draft"] = reader.client.post(
            TRANSFERS,
            json={
                "client_request_id": str(uuid.uuid4()),
                "sender_account_id": linh.wallet_id,
                "recipient_account_id": linh.recipient_id("CAFE"),
                "amount_vnd": 10_000,
            },
            headers=writes(linh.csrf),
        )
        outcome["me"] = reader.client.get(ME)

    # The gate holds the transfer row, so the confirm stops after its account locks.
    (confirmed,) = race(
        pg_engine,
        row_gate(pg_engine, "transfers", draft["id"]),
        [lambda: confirmer.confirm(draft["id"])],
        before_release=while_confirm_holds_accounts,
    )

    assert outcome["draft"].status_code == 201, outcome["draft"].text
    assert outcome["me"].status_code == 200, outcome["me"].text
    assert money(outcome["me"].json()["accounts"][0]) == (10_000_000, 0, 10_000_000)
    assert confirmed.status_code == 200 and confirmed.json()["status"] == "SUCCEEDED"
    assert_money_invariants(pg_engine, linh.sandbox_id)
    for b in (confirmer, reader):
        b.client.close()


def test_recipient_policy_lock_precedes_account_locks(bounded_app: FastAPI, pg_engine: Engine):
    """A confirmation queued behind a recipient-policy change holds no account lock yet.

    The gate holds the recipient's advisory lock, as a restriction create/revoke would. While
    the confirmation waits there, the same sender can still cancel another hold, which needs
    the sender account lock; it would wait if the advisory lock were taken after accounts.
    """
    linh = open_sandbox(TestClient(bounded_app))
    draft = linh.draft("CAFE", 20_000)
    other_hold = linh.held("RISK_RECIPIENT", 20_000)
    confirmer, canceller = same_actor(bounded_app, linh), same_actor(bounded_app, linh)
    key = recipient_policy_key(linh.sandbox_id, uuid.UUID(linh.recipient_id("CAFE")))
    outcome: dict[str, Any] = {}

    def while_confirm_waits_for_policy(_: Connection) -> None:
        outcome["cancel"] = canceller.cancel(other_hold["id"])

    (confirmed,) = race(
        pg_engine,
        advisory_gate(pg_engine, key),
        [lambda: confirmer.confirm(draft["id"])],
        before_release=while_confirm_waits_for_policy,
    )

    assert outcome["cancel"].status_code == 200, outcome["cancel"].text
    assert outcome["cancel"].json()["status"] == "CANCELED"
    assert confirmed.status_code == 200 and confirmed.json()["status"] == "SUCCEEDED"
    assert money(linh.wallet()) == (9_980_000, 0, 9_980_000)
    assert_money_invariants(pg_engine, linh.sandbox_id)
    for b in (confirmer, canceller):
        b.client.close()
