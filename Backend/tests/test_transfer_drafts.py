"""Task 5: immutable transfer drafts, exact request replay and the caller's transfer reads.

Every test discovers fixture IDs through the API and checks persisted state through the
disposable PostgreSQL engine. Rulings encoded here: the idempotency key is (sandbox, sender
account, client_request_id); a self-transfer is 422 VALIDATION_ERROR before any lookup; a foreign
or unknown sender/recipient is an indistinguishable 404 NOT_FOUND; drafts do not check or reserve
funds; listTransfers returns the caller's own sent transfers, newest created_at first, then id
descending. Confirmation of an expired draft is completed in Task 7 (see the last test).
"""

import threading
import time
import uuid
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select, text, update
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app import models
from app.api.schemas import Transfer, TransferList
from app.demo import fixtures
from app.main import create_app
from tests.conftest import (
    API,
    TEST_ORIGIN,
    guardian_test_settings,
    require_test_database_url,
    start_demo,
)

ORIGIN = {"Origin": TEST_ORIGIN}
ME = f"{API}/me"
RECIPIENTS = f"{API}/recipients"
TRANSFERS = f"{API}/transfers"
DRAFT_LIFETIME = timedelta(minutes=30)
TRANSFER_FIELDS = {
    "id",
    "sender_account_id",
    "recipient",
    "amount_vnd",
    "status",
    "reserved_amount_vnd",
    "expires_at",
    "created_at",
    "completed_at",
    "assessment",
    "review_reason",
    "replayed",
}
OPENAPI = yaml.safe_load(
    (Path(__file__).resolve().parents[2] / "docs/guardian/openapi.yaml").read_text(encoding="utf-8")
)
SEEDED_TRANSFERS = len(fixtures.HISTORY)  # every customer's settled history in one sandbox
LINH_HISTORY = [h.amount_vnd for h in fixtures.HISTORY if h.sender == "LINH_WALLET"]


@dataclass
class Customer:
    """One browser acting as a selected customer, with its current actor CSRF token."""

    client: TestClient
    bootstrap: dict[str, Any]
    csrf: str
    wallet: dict[str, Any]

    @property
    def sandbox_id(self) -> uuid.UUID:
        return uuid.UUID(self.bootstrap["sandbox_id"])

    def draft(
        self,
        recipient_id: str,
        amount: Any = 20_000,
        *,
        key: str | None = None,
        sender_id: str | None = None,
    ):
        body = {
            "client_request_id": key or str(uuid.uuid4()),
            "sender_account_id": sender_id or self.wallet["id"],
            "recipient_account_id": recipient_id,
            "amount_vnd": amount,
        }
        return self.client.post(TRANSFERS, json=body, headers=writes(self.csrf))

    def recipient(self, symbol: str) -> dict[str, Any]:
        name = fixtures.ACCOUNTS[symbol].display_name
        listed = self.client.get(RECIPIENTS, params={"limit": 100})
        assert listed.status_code == 200, listed.text
        return next(item for item in listed.json()["items"] if item["display_name"] == name)


def writes(csrf: str | None) -> dict[str, str]:
    return {**ORIGIN, "X-CSRF-Token": csrf} if csrf is not None else dict(ORIGIN)


def error_code(response) -> str:
    return response.json()["error"]["code"]


def actor_named(bootstrap: dict[str, Any], name: str) -> dict[str, Any]:
    return next(actor for actor in bootstrap["actors"] if actor["display_name"] == name)


def as_actor(client: TestClient, bootstrap: dict[str, Any], name: str) -> Customer:
    response = client.post(
        f"{API}/demo/actors/select",
        json={"actor_id": actor_named(bootstrap, name)["id"]},
        headers=writes(bootstrap["controller_csrf_token"]),
    )
    assert response.status_code == 200, response.text
    me = response.json()
    wallet = me["accounts"][0] if me["accounts"] else {}
    return Customer(client, bootstrap, me["actor_csrf_token"], wallet)


def open_customer(client: TestClient, scenario: str = "MAIN_REFUND") -> Customer:
    """Start a sandbox in `client`; the initial actor is Linh."""
    bootstrap = start_demo(client, scenario)
    (wallet,) = client.get(ME).json()["accounts"]
    return Customer(client, bootstrap, bootstrap["actor_csrf_token"], wallet)


def instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    assert parsed.utcoffset() == timedelta(0), value
    return parsed


def transfers_of(db: Session, sandbox_id: uuid.UUID) -> list[models.Transfer]:
    return list(db.scalars(select(models.Transfer).where(models.Transfer.sandbox_id == sandbox_id)))


def money_state(pg_engine: Engine, sandbox_id: uuid.UUID) -> dict[str, Any]:
    """Balances, reservations, ledger rows and assessments of one sandbox."""
    with Session(pg_engine) as db:
        scoped = models.Account.sandbox_id == sandbox_id
        return {
            "accounts": {
                a.id: (a.balance_vnd, a.reserved_vnd)
                for a in db.scalars(select(models.Account).where(scoped))
            },
            "ledger": {
                e.id: (e.account_id, e.transfer_id, e.kind, e.amount_vnd)
                for e in db.scalars(
                    select(models.LedgerEntry).where(models.LedgerEntry.sandbox_id == sandbox_id)
                )
            },
            "assessments": db.scalar(
                select(func.count())
                .select_from(models.RiskAssessment)
                .where(models.RiskAssessment.sandbox_id == sandbox_id)
            ),
        }


def key_rows(pg_engine: Engine, customer: Customer, key: str) -> list[models.Transfer]:
    with Session(pg_engine) as db:
        return list(
            db.scalars(
                select(models.Transfer).where(
                    models.Transfer.sandbox_id == customer.sandbox_id,
                    models.Transfer.sender_account_id == uuid.UUID(customer.wallet["id"]),
                    models.Transfer.client_request_id == uuid.UUID(key),
                )
            )
        )


def test_new_draft_does_not_reserve(browser, pg_engine: Engine):
    linh = open_customer(browser())
    cafe = linh.recipient("CAFE")
    before = money_state(pg_engine, linh.sandbox_id)
    me_before = linh.client.get(ME).json()
    (wallet_before,) = me_before["accounts"]
    assert (
        wallet_before["balance_vnd"],
        wallet_before["reserved_vnd"],
        wallet_before["available_vnd"],
    ) == (10_000_000, 0, 10_000_000)
    key = str(uuid.uuid4())

    response = linh.draft(cafe["id"], 20_000, key=key)

    assert response.status_code == 201, response.text
    body = response.json()
    Transfer.model_validate(body)
    assert set(body) == TRANSFER_FIELDS, "required nullable fields stay present"
    assert body["sender_account_id"] == linh.wallet["id"]
    assert body["recipient"] == cafe, "server supplies the recipient identity"
    assert (
        body["amount_vnd"],
        body["status"],
        body["reserved_amount_vnd"],
        body["completed_at"],
        body["assessment"],
        body["review_reason"],
        body["replayed"],
    ) == (20_000, "DRAFT", 0, None, None, None, False)
    created_at, expires_at = instant(body["created_at"]), instant(body["expires_at"])
    assert expires_at - created_at == DRAFT_LIFETIME

    with Session(pg_engine) as db:
        row = db.get(models.Transfer, uuid.UUID(body["id"]))
        assert row is not None and row.sandbox_id == linh.sandbox_id
        assert (str(row.sender_account_id), str(row.recipient_account_id)) == (
            linh.wallet["id"],
            cafe["id"],
        )
        assert (str(row.client_request_id), row.amount_vnd, row.status) == (key, 20_000, "DRAFT")
        assert (row.reserved_amount_vnd, row.held_at, row.completed_at) == (0, None, None)
        assert (row.created_at, row.expires_at) == (created_at, expires_at)
        db_now = db.scalar(select(func.now()))
        assert row.created_at <= db_now < row.expires_at, "deadline uses database time"
        legs = db.scalars(
            select(models.LedgerEntry).where(models.LedgerEntry.transfer_id == row.id)
        ).all()
        assert legs == []

    # The maximum amount exceeds Linh's funds: a draft neither checks nor reserves money.
    large = linh.draft(cafe["id"], 1_000_000_000)
    assert large.status_code == 201, large.text
    assert (large.json()["status"], large.json()["reserved_amount_vnd"]) == ("DRAFT", 0)

    assert money_state(pg_engine, linh.sandbox_id) == before
    assert linh.client.get(ME).json() == me_before
    fetched = linh.client.get(f"{TRANSFERS}/{body['id']}")
    assert fetched.status_code == 200, fetched.text
    assert fetched.json() == body
    listed = linh.client.get(TRANSFERS).json()
    assert listed["total"] == len(LINH_HISTORY) + 2, "five settled history transfers, two drafts"
    assert [item["id"] for item in listed["items"][:2]] == [large.json()["id"], body["id"]]
    assert listed["items"][1] == body


def test_exact_draft_replay_is_200(browser, pg_engine: Engine):
    client = browser()
    linh = open_customer(client)
    cafe = linh.recipient("CAFE")
    key = str(uuid.uuid4())

    first = linh.draft(cafe["id"], 20_000, key=key)
    assert first.status_code == 201, first.text
    before = money_state(pg_engine, linh.sandbox_id)
    replay = linh.draft(cafe["id"], 20_000, key=key)

    assert replay.status_code == 200, replay.text
    Transfer.model_validate(replay.json())
    assert replay.json() == {**first.json(), "replayed": True}
    assert len(key_rows(pg_engine, linh, key)) == 1
    assert money_state(pg_engine, linh.sandbox_id) == before

    # The key belongs to the sender account, not to one actor session.
    as_actor(client, linh.bootstrap, "Ops")
    relogged = as_actor(client, linh.bootstrap, "Linh")
    assert relogged.csrf != linh.csrf and relogged.wallet == linh.wallet
    again = relogged.draft(cafe["id"], 20_000, key=key)
    assert again.status_code == 200, again.text
    assert again.json() == replay.json()
    fetched = relogged.client.get(f"{TRANSFERS}/{first.json()['id']}")
    assert fetched.json() == first.json(), "reads never report a replay"
    assert len(key_rows(pg_engine, linh, key)) == 1

    # The same client key from another sender or sandbox is a different logical request.
    an = as_actor(client, linh.bootstrap, "An")
    an_draft = an.draft(an.recipient("CAFE")["id"], 20_000, key=key)
    assert an_draft.status_code == 201, an_draft.text
    other = open_customer(browser())
    other_draft = other.draft(other.recipient("CAFE")["id"], 20_000, key=key)
    assert other_draft.status_code == 201, other_draft.text
    ids = {first.json()["id"], an_draft.json()["id"], other_draft.json()["id"]}
    assert len(ids) == 3
    assert len(key_rows(pg_engine, an, key)) == 1 and len(key_rows(pg_engine, other, key)) == 1


def test_changed_replay_is_409(browser, pg_engine: Engine):
    linh = open_customer(browser())
    cafe, new = linh.recipient("CAFE"), linh.recipient("NEW_RECIPIENT")
    key = str(uuid.uuid4())
    original = linh.draft(cafe["id"], 20_000, key=key)
    assert original.status_code == 201, original.text
    before = money_state(pg_engine, linh.sandbox_id)

    for recipient_id, amount in ((cafe["id"], 30_000), (new["id"], 20_000), (new["id"], 30_000)):
        changed = linh.draft(recipient_id, amount, key=key)
        assert changed.status_code == 409, (recipient_id, amount, changed.text)
        error = changed.json()["error"]
        assert error["code"] == "IDEMPOTENCY_CONFLICT"
        assert set(error) == {"code", "message", "request_id"}
        assert error["request_id"] == changed.headers["x-request-id"]

    (row,) = key_rows(pg_engine, linh, key)
    assert (str(row.recipient_account_id), row.amount_vnd, row.status) == (
        cafe["id"],
        20_000,
        "DRAFT",
    ), "a retry cannot edit an existing draft"
    assert money_state(pg_engine, linh.sandbox_id) == before
    replay = linh.draft(cafe["id"], 20_000, key=key)
    assert replay.status_code == 200 and replay.json()["id"] == original.json()["id"]


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


@pytest.mark.parametrize(
    ("second_amount", "expected_statuses"),
    [(20_000, [200, 201]), (30_000, [201, 409])],
    ids=["identical", "changed"],
)
def test_parallel_duplicate_drafts_create_one_row(
    bounded_app: FastAPI, pg_engine: Engine, second_amount: int, expected_statuses: list[int]
):
    first_client, second_client = TestClient(bounded_app), TestClient(bounded_app)
    linh = open_customer(first_client)
    second_client.cookies.set("guardian_session", first_client.cookies.get("guardian_session"))
    cafe = linh.recipient("CAFE")
    key = str(uuid.uuid4())
    bodies = [
        {
            "client_request_id": key,
            "sender_account_id": linh.wallet["id"],
            "recipient_account_id": cafe["id"],
            "amount_vnd": amount,
        }
        for amount in (20_000, second_amount)
    ]
    barrier = threading.Barrier(2, timeout=10)

    def send(client: TestClient, body: dict[str, Any]):
        barrier.wait()
        return client.post(TRANSFERS, json=body, headers=writes(linh.csrf))

    observer = pg_engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    blocked_sql = text(
        "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() "
        "AND wait_event_type = 'Lock' AND pid <> pg_backend_pid()"
    )
    try:
        with ThreadPoolExecutor(max_workers=2) as pool, pg_engine.connect() as gate:
            # The gate admits reads but blocks every INSERT into transfers, so both requests
            # pass any lookup phase before either can insert: a real check-then-insert race.
            with gate.begin() as gate_transaction:
                gate.execute(text("SET LOCAL lock_timeout = '5s'"))
                gate.execute(text("LOCK TABLE transfers IN SHARE MODE"))
                futures = [
                    pool.submit(send, client, body)
                    for client, body in zip((first_client, second_client), bodies, strict=True)
                ]
                wait_until(lambda: observer.execute(blocked_sql).scalar_one() >= 2)
                gate_transaction.rollback()
            responses = [future.result(timeout=20) for future in futures]
    finally:
        observer.close()
        first_client.close()
        second_client.close()

    assert sorted(r.status_code for r in responses) == expected_statuses, [
        r.text for r in responses
    ]
    rows = key_rows(pg_engine, linh, key)
    assert len(rows) == 1, "concurrent identical keys create exactly one draft"
    created = next(r for r in responses if r.status_code == 201).json()
    assert created["id"] == str(rows[0].id) and created["replayed"] is False
    assert rows[0].amount_vnd == created["amount_vnd"]
    other = next(r for r in responses if r.status_code != 201)
    if other.status_code == 200:
        assert other.json() == {**created, "replayed": True}
    else:
        assert error_code(other) == "IDEMPOTENCY_CONFLICT"
    with Session(pg_engine) as db:
        assert len(transfers_of(db, linh.sandbox_id)) == SEEDED_TRANSFERS + 1


def test_foreign_sender_or_recipient_is_404(browser, pg_engine: Engine):
    linh = open_customer(browser())
    other = open_customer(browser())
    cafe, other_cafe = linh.recipient("CAFE"), other.recipient("CAFE")
    an_id = uuid.UUID(actor_named(linh.bootstrap, "An")["id"])
    with Session(pg_engine) as db:
        an_wallet = db.scalar(select(models.Account).where(models.Account.owner_actor_id == an_id))
        assert an_wallet is not None
        an_history = db.scalars(
            select(models.Transfer).where(models.Transfer.sender_account_id == an_wallet.id)
        ).all()
        assert len(an_history) == 2
    other_draft = other.draft(other_cafe["id"])
    assert other_draft.status_code == 201
    before = {box: money_state(pg_engine, box) for box in (linh.sandbox_id, other.sandbox_id)}
    with Session(pg_engine) as db:
        counts_before = {box: len(transfers_of(db, box)) for box in before}

    unknown = str(uuid.uuid4())
    cases = {
        "same-sandbox customer's wallet as sender": (str(an_wallet.id), cafe["id"]),
        "other sandbox's wallet as sender": (other.wallet["id"], cafe["id"]),
        "unknown sender": (unknown, cafe["id"]),
        "other sandbox's recipient": (linh.wallet["id"], other_cafe["id"]),
        "customer wallet as recipient": (linh.wallet["id"], str(an_wallet.id)),
        "unknown recipient": (linh.wallet["id"], unknown),
        "both foreign": (other.wallet["id"], other_cafe["id"]),
    }
    messages = set()
    for label, (sender_id, recipient_id) in cases.items():
        denied = linh.draft(recipient_id, sender_id=sender_id)
        assert denied.status_code == 404, (label, denied.text)
        assert set(denied.json()["error"]) == {"code", "message", "request_id"}
        assert error_code(denied) == "NOT_FOUND", label
        messages.add(denied.json()["error"]["message"])
    assert len(messages) == 1, "missing and inaccessible resources are indistinguishable"

    for transfer_id in (str(an_history[0].id), other_draft.json()["id"], unknown):
        hidden = linh.client.get(f"{TRANSFERS}/{transfer_id}")
        assert hidden.status_code == 404, hidden.text
        assert error_code(hidden) == "NOT_FOUND"
        assert hidden.json()["error"]["message"] in messages
    malformed = linh.client.get(f"{TRANSFERS}/not-a-uuid")
    assert malformed.status_code == 422 and error_code(malformed) == "VALIDATION_ERROR"

    listed = {
        item["id"] for item in linh.client.get(TRANSFERS, params={"limit": 100}).json()["items"]
    }
    assert not listed & ({str(t.id) for t in an_history} | {other_draft.json()["id"]})
    assert {box: money_state(pg_engine, box) for box in before} == before
    with Session(pg_engine) as db:
        assert {box: len(transfers_of(db, box)) for box in before} == counts_before


def test_self_transfer_rejected(browser, pg_engine: Engine):
    linh = open_customer(browser())
    before = money_state(pg_engine, linh.sandbox_id)
    shared = str(uuid.uuid4())

    for sender_id in (linh.wallet["id"], shared):
        rejected = linh.draft(sender_id, sender_id=sender_id)
        assert rejected.status_code == 422, (sender_id, rejected.text)
        assert error_code(rejected) == "VALIDATION_ERROR"
    assert money_state(pg_engine, linh.sandbox_id) == before
    with Session(pg_engine) as db:
        assert len(transfers_of(db, linh.sandbox_id)) == SEEDED_TRANSFERS


def test_invalid_draft_input_is_422(browser, pg_engine: Engine):
    linh = open_customer(browser())
    cafe = linh.recipient("CAFE")
    valid = {
        "client_request_id": str(uuid.uuid4()),
        "sender_account_id": linh.wallet["id"],
        "recipient_account_id": cafe["id"],
        "amount_vnd": 20_000,
    }
    invalid_bodies = [
        {**valid, "amount_vnd": 0},
        {**valid, "amount_vnd": -1},
        {**valid, "amount_vnd": 1_000_000_001},
        {**valid, "amount_vnd": True},
        {**valid, "amount_vnd": 20_000.5},
        {**valid, "amount_vnd": 20_000.0},
        {**valid, "amount_vnd": "20000"},
        {**valid, "amount_vnd": None},
        {**valid, "client_request_id": "not-a-uuid"},
        {**valid, "recipient_account_id": None},
        {**valid, "status": "SUCCEEDED"},
        {**valid, "sandbox_id": str(linh.sandbox_id)},
        {key: value for key, value in valid.items() if key != "client_request_id"},
    ]
    for body in invalid_bodies:
        rejected = linh.client.post(TRANSFERS, json=body, headers=writes(linh.csrf))
        assert rejected.status_code == 422, (body, rejected.text)
        assert error_code(rejected) == "VALIDATION_ERROR"
    with Session(pg_engine) as db:
        assert len(transfers_of(db, linh.sandbox_id)) == SEEDED_TRANSFERS


def test_draft_mutation_requires_origin_csrf_and_customer(browser, pg_engine: Engine):
    client = browser()
    linh = open_customer(client)
    cafe = linh.recipient("CAFE")
    body = {
        "client_request_id": str(uuid.uuid4()),
        "sender_account_id": linh.wallet["id"],
        "recipient_account_id": cafe["id"],
        "amount_vnd": 20_000,
    }
    controller_csrf = linh.bootstrap["controller_csrf_token"]
    denials = [
        ({"X-CSRF-Token": linh.csrf}, 403, "ORIGIN_DENIED"),
        ({"Origin": "http://evil.example", "X-CSRF-Token": linh.csrf}, 403, "ORIGIN_DENIED"),
        (dict(ORIGIN), 403, "CSRF_FAILED"),
        (writes(controller_csrf), 403, "CSRF_FAILED"),
        (writes(linh.csrf[:-1] + ("1" if linh.csrf.endswith("0") else "0")), 403, "CSRF_FAILED"),
    ]
    for headers, status, code in denials:
        denied = client.post(TRANSFERS, json=body, headers=headers)
        assert (denied.status_code, error_code(denied)) == (status, code), headers
    anonymous = browser().post(TRANSFERS, json=body, headers=writes(linh.csrf))
    assert (anonymous.status_code, error_code(anonymous)) == (401, "SESSION_EXPIRED")

    created = client.post(TRANSFERS, json=body, headers=writes(linh.csrf))
    assert created.status_code == 201, created.text
    forged = client.post(
        TRANSFERS,
        json={**body, "client_request_id": str(uuid.uuid4())},
        headers={**writes(linh.csrf), "X-Actor-Role": "OPERATOR"},
    )
    assert forged.status_code == 201 and forged.json()["sender_account_id"] == linh.wallet["id"]

    ops = as_actor(client, linh.bootstrap, "Ops")
    forbidden = [
        client.post(
            TRANSFERS,
            json={**body, "client_request_id": str(uuid.uuid4())},
            headers=writes(ops.csrf),
        ),
        client.get(TRANSFERS),
        client.get(TRANSFERS, params={"limit": 0}),
        client.get(f"{TRANSFERS}/{created.json()['id']}"),
        client.get(f"{TRANSFERS}/not-a-uuid"),
    ]
    for response in forbidden:
        assert (response.status_code, error_code(response)) == (403, "FORBIDDEN"), response.text
    with Session(pg_engine) as db:
        assert len(transfers_of(db, linh.sandbox_id)) == SEEDED_TRANSFERS + 2


def test_transfer_list_is_owned_ordered_and_paginated(browser, pg_engine: Engine):
    client = browser()
    linh = open_customer(client)
    cafe = linh.recipient("CAFE")
    drafts = [linh.draft(cafe["id"], amount).json() for amount in (20_000, 30_000)]
    with Session(pg_engine) as db, db.begin():
        tie = db.scalar(select(func.now())) - timedelta(hours=12)
        tied = [
            models.Transfer(
                id=uuid.uuid4(),
                sandbox_id=linh.sandbox_id,
                sender_account_id=uuid.UUID(linh.wallet["id"]),
                recipient_account_id=uuid.UUID(cafe["id"]),
                client_request_id=uuid.uuid4(),
                amount_vnd=10_000,
                created_at=tie,
                expires_at=tie + DRAFT_LIFETIME,
            )
            for _ in range(2)
        ]
        db.add_all(tied)
    with Session(pg_engine) as db:
        own = [
            t
            for t in transfers_of(db, linh.sandbox_id)
            if str(t.sender_account_id) == linh.wallet["id"]
        ]
    expected = [str(t.id) for t in sorted(own, key=lambda t: (t.created_at, t.id), reverse=True)]
    assert len(expected) == len(LINH_HISTORY) + 4
    assert expected[:2] == [drafts[1]["id"], drafts[0]["id"]]

    full = client.get(TRANSFERS)
    assert full.status_code == 200, full.text
    TransferList.model_validate(full.json())
    page = full.json()
    assert (page["total"], page["limit"], page["offset"]) == (9, 20, 0)
    assert [item["id"] for item in page["items"]] == expected
    assert page["items"][:2] == [drafts[1], drafts[0]]
    for item in page["items"]:
        assert set(item) == TRANSFER_FIELDS
        assert item["sender_account_id"] == linh.wallet["id"] and item["recipient"] == cafe
        assert item["replayed"] is False and item["assessment"] is None
    settled = [item for item in page["items"] if item["status"] == "SUCCEEDED"]
    assert sorted(item["amount_vnd"] for item in settled) == LINH_HISTORY
    assert all(item["completed_at"] is not None for item in settled)
    assert client.get(TRANSFERS).json() == page, "repeat reads are identical"

    pages = [client.get(TRANSFERS, params={"limit": 4, "offset": o}).json() for o in (0, 4, 8)]
    assert [(p["total"], p["limit"], p["offset"]) for p in pages] == [(9, 4, o) for o in (0, 4, 8)]
    assert [item["id"] for p in pages for item in p["items"]] == expected
    beyond = client.get(TRANSFERS, params={"limit": 100, "offset": 50}).json()
    assert (beyond["total"], beyond["items"]) == (9, [])
    for query in ({"limit": 0}, {"limit": 101}, {"offset": -1}, {"limit": "ten"}):
        invalid = client.get(TRANSFERS, params=query)
        assert (invalid.status_code, error_code(invalid)) == (422, "VALIDATION_ERROR"), query

    an = as_actor(client, linh.bootstrap, "An")
    an_page = an.client.get(TRANSFERS).json()
    assert an_page["total"] == 2
    assert {item["sender_account_id"] for item in an_page["items"]} == {an.wallet["id"]}
    assert not {item["id"] for item in an_page["items"]} & set(expected)


def test_expired_draft_cannot_confirm(browser, pg_engine: Engine):
    """The deadline is fixed at creation in database time and never extended by a replay.

    Task 7 completes this test: confirming the expired draft returns 409 with EXPIRED state and
    writes no ledger entry. Until then it asserts the observable deadline behavior only.
    """
    linh = open_customer(browser())
    cafe = linh.recipient("CAFE")
    key = str(uuid.uuid4())
    created = linh.draft(cafe["id"], 20_000, key=key)
    assert created.status_code == 201, created.text
    assert instant(created.json()["expires_at"]) - instant(created.json()["created_at"]) == (
        DRAFT_LIFETIME
    )
    with pg_engine.begin() as connection:
        connection.execute(
            update(models.Transfer)
            .where(models.Transfer.id == uuid.UUID(created.json()["id"]))
            .values(expires_at=func.now() - timedelta(seconds=1))
        )
    (row,) = key_rows(pg_engine, linh, key)
    before = money_state(pg_engine, linh.sandbox_id)

    replay = linh.draft(cafe["id"], 20_000, key=key)

    assert replay.status_code == 200, replay.text
    assert replay.json()["id"] == created.json()["id"] and replay.json()["replayed"] is True
    assert instant(replay.json()["expires_at"]) == row.expires_at, "a replay never extends it"
    assert replay.json()["created_at"] == created.json()["created_at"]
    assert len(key_rows(pg_engine, linh, key)) == 1, "an expired key is not reissued"
    fetched = linh.client.get(f"{TRANSFERS}/{created.json()['id']}").json()
    with Session(pg_engine) as db:
        assert instant(fetched["expires_at"]) < db.scalar(select(func.now()))
    assert fetched["reserved_amount_vnd"] == 0
    assert money_state(pg_engine, linh.sandbox_id) == before


def test_task5_operations_match_contract(guardian_app):
    generated = TestClient(guardian_app).get("/openapi.json").json()["paths"]

    def parameters(operation: dict[str, Any]) -> dict[str, tuple[Any, ...]]:
        keys = ("type", "format", "minimum", "maximum", "default")
        return {
            p["name"]: (p["in"], p.get("required", False), *(p["schema"].get(k) for k in keys))
            for p in operation.get("parameters", [])
        }

    for path, method, model in (
        ("/transfers", "get", "TransferList"),
        ("/transfers", "post", "Transfer"),
        ("/transfers/{id}", "get", "Transfer"),
    ):
        operation = generated[f"{API}{path}"][method]
        contract = OPENAPI["paths"][path][method]
        assert operation["operationId"] == contract["operationId"]
        assert operation["tags"] == contract["tags"] == ["Customer"]
        assert operation["security"] == contract["security"] == [{"actorCookie": []}]
        assert parameters(operation) == parameters(contract), path
        for status in [code for code in contract["responses"] if code.startswith("2")]:
            schema = operation["responses"][status]["content"]["application/json"]["schema"]
            assert schema["$ref"] == f"#/components/schemas/{model}", (path, status)
    create = generated[f"{API}/transfers"]["post"]
    assert {"200", "201"} <= set(create["responses"])
    body = create["requestBody"]["content"]["application/json"]["schema"]
    assert create["requestBody"]["required"] is True
    assert body["$ref"] == "#/components/schemas/CreateTransfer"
