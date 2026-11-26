"""Task 8: controlled demo refund settlement (settleDemoRefund) through HTTP.

Rulings encoded here:
- Only the sandbox's demo-controller cookie with its controller CSRF token and the exact Origin
  can settle. An actor cookie or actor CSRF cannot (401 SESSION_EXPIRED without the controller
  cookie, 403 CSRF_FAILED with an actor token). A refund of another sandbox, or an unknown ID,
  is 404 NOT_FOUND.
- Settlement locks the refund's account, reconciles that account's passed deadlines, then locks
  the refund. It requires an order owned by the account's owner and an amount within the
  order's original amount; otherwise 409 STATE_CONFLICT and nothing is written.
- The first settlement credits the account once (one REFUND_CREDIT), sets SETTLED and settled_at
  in database time and audits REFUND_SETTLED as DEMO_CONTROL. A repeat returns the stored
  SETTLED refund with 200 and writes nothing. An outgoing hold neither blocks nor changes the
  credit: the balance rises and the reservation stays.
"""

import uuid
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Connection, Engine, func, insert, select, update
from sqlalchemy.orm import Session

from app import models
from app.api.schemas import Refund
from app.auth.service import ACTOR_COOKIE, CONTROLLER_COOKIE
from tests.conftest import API
from tests.money_support import (
    ORIGIN,
    Customer,
    actor_in,
    assert_money_invariants,
    assert_sanitized,
    audit_of,
    db_clock,
    error_code,
    error_of,
    instant,
    money,
    open_sandbox,
    operator_in,
    pass_deadline,
    transfer_row,
    with_controller,
    writes,
)
from tests.race_support import race, row_gate, same_actor

OPENAPI = yaml.safe_load(
    (Path(__file__).resolve().parents[2] / "docs/guardian/openapi.yaml").read_text(encoding="utf-8")
)
ORDERS = f"{API}/orders"
REFUND_ORDER_REFERENCE = "SHOP-4502"


def settle_path(refund_id: str) -> str:
    return f"{API}/demo/refunds/{refund_id}/settle"


def settle(client: TestClient, refund_id: str, csrf: str, *, headers: dict[str, str] | None = None):
    return client.post(settle_path(refund_id), headers=writes(csrf) if headers is None else headers)


def controller_csrf(customer: Customer) -> str:
    return customer.bootstrap["controller_csrf_token"]


def refund_of(customer: Customer) -> dict[str, Any]:
    """The customer's seeded refund as shown in its own order list."""
    response = customer.client.get(ORDERS, params={"limit": 100})
    assert response.status_code == 200, response.text
    order = next(
        item
        for item in response.json()["items"]
        if item["order_reference"] == REFUND_ORDER_REFERENCE
    )
    assert order["refund"] is not None
    return order["refund"]


def refund_entries(pg_engine: Engine, refund_id: str) -> list[tuple[str, str, int]]:
    with Session(pg_engine) as db:
        rows = db.scalars(
            select(models.LedgerEntry).where(models.LedgerEntry.refund_id == uuid.UUID(refund_id))
        ).all()
        return sorted((str(row.account_id), row.kind, row.amount_vnd) for row in rows)


def refund_row(pg_engine: Engine, refund_id: str) -> models.Refund:
    with Session(pg_engine) as db:
        row = db.get(models.Refund, uuid.UUID(refund_id))
        assert row is not None
        return row


def tamper_refund(pg_engine: Engine, refund_id: str, **values: Any) -> None:
    with pg_engine.begin() as connection:
        connection.execute(
            update(models.Refund).where(models.Refund.id == uuid.UUID(refund_id)).values(**values)
        )


def test_refund_once_while_outgoing_held(browser, pg_engine: Engine):
    linh = open_sandbox(browser())
    assert linh.confirm(linh.draft("CAFE", 20_000)["id"]).json()["status"] == "SUCCEEDED"
    held = linh.held("RISK_RECIPIENT", 20_000)
    assert money(linh.wallet()) == (9_980_000, 20_000, 9_960_000)
    refund = refund_of(linh)
    assert (refund["status"], refund["settled_at"], refund["amount_vnd"]) == (
        "APPROVED",
        None,
        500_000,
    )
    assert refund["account_id"] == linh.wallet_id

    before = db_clock(pg_engine)
    settled = settle(linh.client, refund["id"], controller_csrf(linh))
    after = db_clock(pg_engine)

    assert settled.status_code == 200, settled.text
    body = settled.json()
    Refund.model_validate(body)
    assert (body["id"], body["order_id"], body["account_id"], body["amount_vnd"]) == (
        refund["id"],
        refund["order_id"],
        linh.wallet_id,
        500_000,
    )
    assert body["status"] == "SETTLED"
    assert before <= instant(body["settled_at"]) <= after, "settled in database time"
    # The incoming credit proceeds while the outgoing transfer is held.
    assert money(linh.wallet()) == (10_480_000, 20_000, 10_460_000)
    assert refund_entries(pg_engine, refund["id"]) == [(linh.wallet_id, "REFUND_CREDIT", 500_000)]
    (event,) = audit_of(pg_engine, refund["id"])
    assert (
        event.event_type,
        event.actor_kind,
        event.actor_id,
        event.target_type,
        event.request_id,
    ) == ("REFUND_SETTLED", "DEMO_CONTROL", None, "REFUND", settled.headers["x-request-id"])
    assert (event.details["amount_vnd"], event.details["account_id"]) == (500_000, linh.wallet_id)
    assert event.details["order_id"] == refund["order_id"]
    assert_sanitized(event, controller_csrf(linh), linh.client.cookies.get(CONTROLLER_COOKIE))

    # Repeating settlement returns the stored SETTLED refund and credits nothing again.
    for _ in range(2):
        again = settle(linh.client, refund["id"], controller_csrf(linh))
        assert again.status_code == 200, again.text
        assert again.json() == body
    assert money(linh.wallet()) == (10_480_000, 20_000, 10_460_000)
    assert len(refund_entries(pg_engine, refund["id"])) == 1
    assert len(audit_of(pg_engine, refund["id"])) == 1
    assert refund_of(linh) == body

    # The hold is untouched and still releases normally.
    hold = transfer_row(pg_engine, held["id"])
    assert (hold.status, hold.reserved_amount_vnd) == ("RISK_HELD", 20_000)
    assert linh.cancel(held["id"]).json()["status"] == "CANCELED"
    assert money(linh.wallet()) == (10_480_000, 0, 10_480_000)
    assert_money_invariants(pg_engine, linh.sandbox_id)


def test_refund_requires_controller_credential(browser, pg_engine: Engine):
    linh = open_sandbox(browser())
    refund = refund_of(linh)
    ops = operator_in(browser(), linh)
    actor_only = browser()
    actor_only.cookies.set(ACTOR_COOKIE, linh.client.cookies.get(ACTOR_COOKIE))
    other = open_sandbox(browser())
    other_refund = refund_of(other)
    csrf = controller_csrf(linh)

    denials = [
        (settle(actor_only, refund["id"], linh.csrf), 401, "SESSION_EXPIRED"),
        (settle(actor_only, refund["id"], csrf), 401, "SESSION_EXPIRED"),
        (settle(linh.client, refund["id"], linh.csrf), 403, "CSRF_FAILED"),
        (settle(ops.client, refund["id"], ops.csrf), 403, "CSRF_FAILED"),
        (
            settle(linh.client, refund["id"], csrf, headers={"X-CSRF-Token": csrf}),
            403,
            "ORIGIN_DENIED",
        ),
        (
            settle(
                linh.client,
                refund["id"],
                csrf,
                headers={"Origin": "https://evil.example", "X-CSRF-Token": csrf},
            ),
            403,
            "ORIGIN_DENIED",
        ),
        (settle(linh.client, refund["id"], csrf, headers=dict(ORIGIN)), 403, "CSRF_FAILED"),
        (settle(browser(), refund["id"], csrf), 401, "SESSION_EXPIRED"),
        (settle(linh.client, other_refund["id"], csrf), 404, "NOT_FOUND"),
        (settle(other.client, refund["id"], controller_csrf(other)), 404, "NOT_FOUND"),
        (settle(linh.client, str(uuid.uuid4()), csrf), 404, "NOT_FOUND"),
        (settle(linh.client, "not-a-uuid", csrf), 422, "VALIDATION_ERROR"),
    ]
    for response, status, code in denials:
        assert (response.status_code, error_code(response)) == (status, code), response.text

    for customer, refund_id in ((linh, refund["id"]), (other, other_refund["id"])):
        row = refund_row(pg_engine, refund_id)
        assert (row.status, row.settled_at) == ("APPROVED", None)
        assert refund_entries(pg_engine, refund_id) == []
        assert audit_of(pg_engine, refund_id) == []
        assert money(customer.wallet()) == (10_000_000, 0, 10_000_000)
        assert_money_invariants(pg_engine, customer.sandbox_id)


def test_refund_must_match_its_order_and_account(browser, pg_engine: Engine):
    linh = open_sandbox(browser())
    refund = refund_of(linh)
    an = actor_in(browser(), linh, "An")
    cafe_id = linh.recipient_id("CAFE")
    original = {"account_id": uuid.UUID(linh.wallet_id), "amount_vnd": 500_000}

    for tampered in (
        {"account_id": uuid.UUID(an.wallet_id)},  # wallet of a customer who does not own the order
        {"account_id": uuid.UUID(cafe_id)},  # an ownerless external account
        {"amount_vnd": 500_001},  # more than the order's original amount
    ):
        tamper_refund(pg_engine, refund["id"], **tampered)
        refused = settle(linh.client, refund["id"], controller_csrf(linh))
        assert (refused.status_code, error_code(refused)) == (409, "STATE_CONFLICT"), refused.text
        assert set(error_of(refused)) == {"code", "message", "request_id"}
        assert refund_row(pg_engine, refund["id"]).status == "APPROVED"
        assert refund_entries(pg_engine, refund["id"]) == []
        assert audit_of(pg_engine, refund["id"]) == []
        tamper_refund(pg_engine, refund["id"], **original)
    assert money(linh.wallet()) == (10_000_000, 0, 10_000_000)
    assert money(an.wallet()) == (4_600_000, 0, 4_600_000)
    assert_money_invariants(pg_engine, linh.sandbox_id)

    settled = settle(linh.client, refund["id"], controller_csrf(linh))
    assert settled.status_code == 200 and settled.json()["status"] == "SETTLED", settled.text
    assert money(linh.wallet()) == (10_500_000, 0, 10_500_000)
    assert_money_invariants(pg_engine, linh.sandbox_id)


def test_settlement_reconciles_due_holds_first(browser, pg_engine: Engine):
    linh = open_sandbox(browser())
    due = linh.held("RISK_RECIPIENT", 20_000)
    live = linh.held("RISK_RECIPIENT", 30_000)
    pass_deadline(pg_engine, due["id"])

    settled = settle(linh.client, refund_of(linh)["id"], controller_csrf(linh))

    assert settled.status_code == 200, settled.text
    assert transfer_row(pg_engine, due["id"]).status == "EXPIRED"
    (expired,) = audit_of(pg_engine, due["id"], "TRANSFER_EXPIRED")
    assert (expired.actor_kind, expired.request_id) == ("SYSTEM", settled.headers["x-request-id"])
    assert transfer_row(pg_engine, live["id"]).status == "RISK_HELD"
    assert money(linh.wallet()) == (10_500_000, 30_000, 10_470_000)
    assert_money_invariants(pg_engine, linh.sandbox_id)


@pytest.mark.parametrize("case", ["settles", "with-account-activity"])
def test_concurrent_settles_credit_once(bounded_app: FastAPI, pg_engine: Engine, case: str):
    linh = open_sandbox(TestClient(bounded_app))
    refund = refund_of(linh)
    held = linh.held("RISK_RECIPIENT", 20_000)
    draft = linh.draft("CAFE", 20_000)
    csrf = controller_csrf(linh)
    controllers = [with_controller(TestClient(bounded_app), linh) for _ in range(2)]
    canceller, confirmer = same_actor(bounded_app, linh), same_actor(bounded_app, linh)
    contenders = [lambda c=c: settle(c, refund["id"], csrf) for c in controllers]
    if case == "with-account-activity":
        contenders += [lambda: canceller.cancel(held["id"]), lambda: confirmer.confirm(draft["id"])]

    # Every contender queues on Linh's account lock, which settlement takes before the refund.
    results = race(pg_engine, row_gate(pg_engine, "accounts", linh.wallet_id), contenders)

    first, second = results[0], results[1]
    assert [first.status_code, second.status_code] == [200, 200], [r.text for r in results]
    assert first.json() == second.json(), "both callers see the one stored settlement"
    assert first.json()["status"] == "SETTLED"
    assert refund_entries(pg_engine, refund["id"]) == [(linh.wallet_id, "REFUND_CREDIT", 500_000)]
    assert [e.event_type for e in audit_of(pg_engine, refund["id"])] == ["REFUND_SETTLED"]
    if case == "settles":
        assert money(linh.wallet()) == (10_500_000, 20_000, 10_480_000)
    else:
        canceled, confirmed = results[2], results[3]
        assert canceled.status_code == 200 and canceled.json()["status"] == "CANCELED"
        assert confirmed.status_code == 200 and confirmed.json()["status"] == "SUCCEEDED"
        assert money(linh.wallet()) == (10_480_000, 0, 10_480_000)
    assert_money_invariants(pg_engine, linh.sandbox_id)
    for client in (*controllers, canceller.client, confirmer.client):
        client.close()


def test_settlement_reads_the_balance_under_the_account_lock(
    bounded_app: FastAPI, pg_engine: Engine
):
    """Another money write commits while settlement waits for the account: none is lost."""
    linh = open_sandbox(TestClient(bounded_app))
    refund = refund_of(linh)
    controller = with_controller(TestClient(bounded_app), linh)
    wallet_id = uuid.UUID(linh.wallet_id)

    def ledger_consistent_credit(gate: Connection) -> None:
        # A second synthetic settled refund of 100,000, written as the service would.
        order_id, other_refund_id = uuid.uuid4(), uuid.uuid4()
        gate.execute(
            insert(models.Order).values(
                id=order_id,
                sandbox_id=linh.sandbox_id,
                customer_actor_id=uuid.UUID(linh.actor_id("Linh")),
                order_reference="SHOP-TEST-RACE",
                merchant_name="[Synthetic test] merchant",
                original_amount_vnd=100_000,
            )
        )
        gate.execute(
            insert(models.Refund).values(
                id=other_refund_id,
                sandbox_id=linh.sandbox_id,
                order_id=order_id,
                account_id=wallet_id,
                amount_vnd=100_000,
                status="SETTLED",
                settled_at=func.now(),
            )
        )
        gate.execute(
            insert(models.LedgerEntry).values(
                sandbox_id=linh.sandbox_id,
                account_id=wallet_id,
                refund_id=other_refund_id,
                kind="REFUND_CREDIT",
                amount_vnd=100_000,
            )
        )
        gate.execute(
            update(models.Account)
            .where(models.Account.id == wallet_id)
            .values(balance_vnd=models.Account.balance_vnd + 100_000)
        )

    (settled,) = race(
        pg_engine,
        row_gate(pg_engine, "accounts", linh.wallet_id),
        [lambda: settle(controller, refund["id"], controller_csrf(linh))],
        before_release=ledger_consistent_credit,
    )

    assert settled.status_code == 200 and settled.json()["status"] == "SETTLED", settled.text
    assert money(linh.wallet()) == (10_600_000, 0, 10_600_000)
    assert_money_invariants(pg_engine, linh.sandbox_id)
    controller.close()


def test_task8_refund_operation_matches_contract(guardian_app):
    generated = TestClient(guardian_app).get("/openapi.json").json()["paths"]
    operation = generated[f"{API}/demo/refunds/{{id}}/settle"]["post"]
    contract = OPENAPI["paths"]["/demo/refunds/{id}/settle"]["post"]

    def parameters(op: dict[str, Any]) -> dict[str, tuple[Any, ...]]:
        return {
            p["name"]: (p["in"], p.get("required", False), p["schema"].get("type"))
            for p in op.get("parameters", [])
        }

    assert operation["operationId"] == contract["operationId"] == "settleDemoRefund"
    assert operation["tags"] == contract["tags"] == ["Demo"]
    assert operation["security"] == contract["security"] == [{"demoCookie": []}]
    assert parameters(operation) == parameters(contract)
    assert "requestBody" not in operation and "requestBody" not in contract
    success = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert success["$ref"] == "#/components/schemas/Refund"
