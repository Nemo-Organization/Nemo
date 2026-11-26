"""Task 6: POST /transfers/{id}/assess through HTTP against seeded sandboxes.

Rulings encoded here: the customer may assess its own DRAFT, RISK_HELD or READY transfer (the
contract's "draft or active held/ready transfer"); any other state, or an active transfer past its
deadline, is 409 STATE_CONFLICT with the current transfer and no new assessment. Behavioral history
is the sender wallet's SUCCEEDED transfers created in the last 30 days of database time. Each
assessment is persisted with policy_version guardian-rules-v1 and expires exactly five minutes
after it was made. Assessment never changes balances, reservations or transfer status.
"""

import re
import socket
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select, update
from sqlalchemy.orm import Session

from app import models
from app.api.schemas import RiskAssessment
from app.demo import fixtures
from tests.conftest import API, TEST_ORIGIN, start_demo

ORIGIN = {"Origin": TEST_ORIGIN}
ME = f"{API}/me"
RECIPIENTS = f"{API}/recipients"
TRANSFERS = f"{API}/transfers"
POLICY_VERSION = "guardian-rules-v1"
ASSESSMENT_LIFETIME = timedelta(minutes=5)
ASSESSMENT_FIELDS = set(RiskAssessment.model_fields)
OPENAPI = yaml.safe_load(
    (Path(__file__).resolve().parents[2] / "docs/guardian/openapi.yaml").read_text(encoding="utf-8")
)


class Customer:
    """One browser acting as the selected customer of one sandbox."""

    def __init__(self, client: TestClient, bootstrap: dict[str, Any], me: dict[str, Any]):
        self.client = client
        self.bootstrap = bootstrap
        self.csrf = me["actor_csrf_token"]
        self.wallet_id = me["accounts"][0]["id"] if me["accounts"] else None
        self.sandbox_id = uuid.UUID(bootstrap["sandbox_id"])

    def recipient_id(self, symbol: str) -> str:
        name = fixtures.ACCOUNTS[symbol].display_name
        items = self.client.get(RECIPIENTS, params={"limit": 100}).json()["items"]
        return next(item["id"] for item in items if item["display_name"] == name)

    def draft(self, symbol: str, amount: int) -> dict[str, Any]:
        response = self.client.post(
            TRANSFERS,
            json={
                "client_request_id": str(uuid.uuid4()),
                "sender_account_id": self.wallet_id,
                "recipient_account_id": self.recipient_id(symbol),
                "amount_vnd": amount,
            },
            headers=writes(self.csrf),
        )
        assert response.status_code == 201, response.text
        return response.json()

    def assess(self, transfer_id: str, headers: dict[str, str] | None = None):
        return self.client.post(
            f"{TRANSFERS}/{transfer_id}/assess",
            headers=writes(self.csrf) if headers is None else headers,
        )

    def assessed(self, symbol: str, amount: int) -> dict[str, Any]:
        response = self.assess(self.draft(symbol, amount)["id"])
        assert response.status_code == 200, response.text
        RiskAssessment.model_validate(response.json())
        assert set(response.json()) == ASSESSMENT_FIELDS
        return response.json()


def writes(csrf: str) -> dict[str, str]:
    return {**ORIGIN, "X-CSRF-Token": csrf}


def error_code(response) -> str:
    return response.json()["error"]["code"]


def actor_named(bootstrap: dict[str, Any], name: str) -> dict[str, Any]:
    return next(actor for actor in bootstrap["actors"] if actor["display_name"] == name)


def open_sandbox(client: TestClient, scenario: str = "MAIN_REFUND") -> Customer:
    bootstrap = start_demo(client, scenario)
    return Customer(client, bootstrap, client.get(ME).json())


def as_actor(customer: Customer, name: str) -> Customer:
    response = customer.client.post(
        f"{API}/demo/actors/select",
        json={"actor_id": actor_named(customer.bootstrap, name)["id"]},
        headers=writes(customer.bootstrap["controller_csrf_token"]),
    )
    assert response.status_code == 200, response.text
    return Customer(customer.client, customer.bootstrap, response.json())


def signals(assessment: dict[str, Any]) -> tuple[str, str, str, list[str]]:
    return (
        assessment["decision"],
        assessment["behavior_signal"],
        assessment["recipient_signal"],
        [reason["code"] for reason in assessment["reasons"]],
    )


def stored(pg_engine: Engine, assessment_id: str) -> models.RiskAssessment:
    with Session(pg_engine) as db:
        row = db.get(models.RiskAssessment, uuid.UUID(assessment_id))
        assert row is not None
        return row


def assessment_count(pg_engine: Engine, sandbox_id: uuid.UUID) -> int:
    with Session(pg_engine) as db:
        return db.scalar(
            select(func.count())
            .select_from(models.RiskAssessment)
            .where(models.RiskAssessment.sandbox_id == sandbox_id)
        )


def restriction_on(
    pg_engine: Engine, customer: Customer, symbol: str
) -> models.RecipientRestriction:
    with Session(pg_engine) as db:
        row = db.scalar(
            select(models.RecipientRestriction).where(
                models.RecipientRestriction.sandbox_id == customer.sandbox_id,
                models.RecipientRestriction.recipient_account_id
                == uuid.UUID(customer.recipient_id(symbol)),
            )
        )
        assert row is not None
        return row


def money_and_transfers(pg_engine: Engine, sandbox_id: uuid.UUID) -> dict[str, Any]:
    with Session(pg_engine) as db:
        return {
            "accounts": {
                a.id: (a.balance_vnd, a.reserved_vnd)
                for a in db.scalars(
                    select(models.Account).where(models.Account.sandbox_id == sandbox_id)
                )
            },
            "ledger": sorted(
                str(e.id)
                for e in db.scalars(
                    select(models.LedgerEntry).where(models.LedgerEntry.sandbox_id == sandbox_id)
                )
            ),
            "transfers": {
                t.id: (t.status, t.reserved_amount_vnd, t.expires_at, t.completed_at, t.held_at)
                for t in db.scalars(
                    select(models.Transfer).where(models.Transfer.sandbox_id == sandbox_id)
                )
            },
        }


def instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    assert parsed.utcoffset() == timedelta(0), value
    return parsed


def test_20k_verified_recipient_holds(browser, pg_engine: Engine):
    linh = open_sandbox(browser())
    seeded = restriction_on(pg_engine, linh, "RISK_RECIPIENT")
    assert (seeded.action, seeded.status) == ("HOLD", "ACTIVE")
    before = money_and_transfers(pg_engine, linh.sandbox_id)

    held = linh.assessed("RISK_RECIPIENT", 20_000)

    assert signals(held) == ("HOLD", "NORMAL", "HOLD", ["RECIPIENT_HOLD"])
    (reason,) = held["reasons"]
    assert reason["restriction_id"] == str(seeded.id) and reason["message"]
    assert held["policy_version"] == POLICY_VERSION
    assert instant(held["expires_at"]) - instant(held["assessed_at"]) == ASSESSMENT_LIFETIME
    after = money_and_transfers(pg_engine, linh.sandbox_id)
    assert after["accounts"] == before["accounts"] and after["ledger"] == before["ledger"]
    transfer = after["transfers"][uuid.UUID(held["transfer_id"])]
    assert transfer[:2] == ("DRAFT", 0), "assessing a HOLD reserves nothing"

    anomalous = linh.assessed("RISK_RECIPIENT", 8_000_000)
    assert signals(anomalous) == (
        "HOLD",
        "ANOMALOUS",
        "HOLD",
        ["RECIPIENT_HOLD", "AMOUNT_ABOVE_BASELINE"],
    ), "recipient and behavioral reasons stay separate"
    assert [r["restriction_id"] for r in anomalous["reasons"]] == [str(seeded.id), None]

    an = as_actor(linh, "An")
    sparse = an.assessed("RISK_RECIPIENT", 20_000)
    assert signals(sparse) == ("HOLD", "INSUFFICIENT_HISTORY", "HOLD", ["RECIPIENT_HOLD"])

    # A reviewed WARN decision warns even for 20,000 (live case "New recipient report").
    linh = as_actor(an, "Linh")
    warn_id = uuid.uuid4()
    with Session(pg_engine) as db, db.begin():
        db.add(
            models.RecipientRestriction(
                id=warn_id,
                sandbox_id=linh.sandbox_id,
                recipient_account_id=uuid.UUID(linh.recipient_id("NEW_RECIPIENT")),
                action="WARN",
                reason="[Synthetic test] Reviewed WARN decision.",
                created_by=uuid.UUID(actor_named(linh.bootstrap, "Ops")["id"]),
                expires_at=db.scalar(select(func.now())) + timedelta(hours=1),
            )
        )
    warned = linh.assessed("NEW_RECIPIENT", 20_000)
    assert signals(warned) == ("WARN", "NORMAL", "WARN", ["RECIPIENT_WARNING"])
    assert warned["reasons"][0]["restriction_id"] == str(warn_id)
    assert money_and_transfers(pg_engine, linh.sandbox_id)["accounts"] == before["accounts"]


def test_expired_restriction_ignored(browser, pg_engine: Engine):
    linh = open_sandbox(browser())
    seeded = restriction_on(pg_engine, linh, "RISK_RECIPIENT")
    draft = linh.draft("RISK_RECIPIENT", 20_000)
    first = linh.assess(draft["id"]).json()
    assert signals(first)[0] == "HOLD"

    with pg_engine.begin() as connection:
        connection.execute(
            update(models.RecipientRestriction)
            .where(models.RecipientRestriction.id == seeded.id)
            .values(expires_at=func.now() - timedelta(seconds=1))
        )
    assert restriction_on(pg_engine, linh, "RISK_RECIPIENT").status == "ACTIVE"
    expired = linh.assess(draft["id"])

    assert expired.status_code == 200, expired.text
    assert signals(expired.json()) == ("ALLOW", "NORMAL", "NONE", [])
    row = stored(pg_engine, expired.json()["id"])
    assert (row.facts["restriction_id"], row.facts["restriction_action"]) == (None, None)
    assert row.facts_fingerprint != stored(pg_engine, first["id"]).facts_fingerprint

    other = open_sandbox(browser())
    revoked = restriction_on(pg_engine, other, "RISK_RECIPIENT")
    with pg_engine.begin() as connection:
        connection.execute(
            update(models.RecipientRestriction)
            .where(models.RecipientRestriction.id == revoked.id)
            .values(
                status="REVOKED",
                revoked_by=uuid.UUID(actor_named(other.bootstrap, "Ops")["id"]),
                revoked_at=func.now(),
                revocation_reason="[Synthetic test] Revoked.",
            )
        )
    assert signals(other.assessed("RISK_RECIPIENT", 20_000)) == ("ALLOW", "NORMAL", "NONE", [])


def test_linh_and_an_scenario_numbers(browser, pg_engine: Engine):
    linh = open_sandbox(browser())

    warned = linh.assessed("NEW_RECIPIENT", 8_000_000)
    ordinary = linh.assessed("NEW_RECIPIENT", 20_000)
    floor = linh.assessed("NEW_RECIPIENT", 2_000_000)
    below = linh.assessed("NEW_RECIPIENT", 1_999_999)

    assert signals(warned) == ("WARN", "ANOMALOUS", "NONE", ["AMOUNT_ABOVE_BASELINE"])
    assert warned["reasons"][0]["restriction_id"] is None
    assert signals(ordinary) == ("ALLOW", "NORMAL", "NONE", [])
    assert signals(floor)[:2] == ("WARN", "ANOMALOUS"), "2,000,000 is inclusive"
    assert signals(below) == ("ALLOW", "NORMAL", "NONE", [])
    facts = stored(pg_engine, warned["id"]).facts
    assert (facts["sample_count"], facts["median_vnd"], facts["threshold_vnd"]) == (
        5,
        300_000,
        2_000_000,
    )
    assert (facts["amount_vnd"], facts["policy_version"]) == (8_000_000, POLICY_VERSION)
    assert (facts["restriction_id"], facts["restriction_action"]) == (None, None)

    an = as_actor(linh, "An")
    sparse = an.assessed("NEW_RECIPIENT", 8_000_000)
    assert signals(sparse) == ("ALLOW", "INSUFFICIENT_HISTORY", "NONE", [])
    an_facts = stored(pg_engine, sparse["id"]).facts
    assert (an_facts["sample_count"], an_facts["median_vnd"], an_facts["threshold_vnd"]) == (
        2,
        200_000,
        None,
    )


def test_history_uses_30_days_of_settled_outgoing_transfers(browser, pg_engine: Engine):
    linh = open_sandbox(browser())
    with Session(pg_engine) as db:
        (oldest,) = db.scalars(
            select(models.Transfer).where(
                models.Transfer.sender_account_id == uuid.UUID(linh.wallet_id),
                models.Transfer.amount_vnd == 100_000,
            )
        ).all()
    # Drafts and a canceled 50,000 transfer are not settled observations.
    canceled = linh.draft("CAFE", 50_000)
    with pg_engine.begin() as connection:
        connection.execute(
            update(models.Transfer)
            .where(models.Transfer.id == uuid.UUID(canceled["id"]))
            .values(status="CANCELED", completed_at=func.now())
        )
    draft = linh.draft("NEW_RECIPIENT", 8_000_000)

    def assess_facts() -> tuple[str, dict[str, Any]]:
        response = linh.assess(draft["id"])
        assert response.status_code == 200, response.text
        return response.json()["behavior_signal"], stored(pg_engine, response.json()["id"]).facts

    def settle_ago(days: int) -> None:
        with pg_engine.begin() as connection:
            connection.execute(
                update(models.Transfer)
                .where(models.Transfer.id == oldest.id)
                .values(
                    created_at=func.now() - timedelta(days=days),
                    completed_at=func.now() - timedelta(days=days) + timedelta(seconds=20),
                )
            )

    signal, facts = assess_facts()
    assert (signal, facts["sample_count"], facts["median_vnd"]) == ("ANOMALOUS", 5, 300_000), (
        "An's settled transfers, drafts and canceled transfers are excluded"
    )
    settle_ago(31)
    signal, facts = assess_facts()
    assert (signal, facts["sample_count"], facts["median_vnd"]) == (
        "INSUFFICIENT_HISTORY",
        4,
        350_000,
    ), "a transfer settled 31 days ago is outside the window"
    settle_ago(29)
    signal, facts = assess_facts()
    assert (signal, facts["sample_count"]) == ("ANOMALOUS", 5)


def test_assessment_is_persisted_and_changes_no_money(browser, pg_engine: Engine, monkeypatch):
    linh = open_sandbox(browser())
    draft = linh.draft("NEW_RECIPIENT", 8_000_000)
    before = money_and_transfers(pg_engine, linh.sandbox_id)
    me_before = linh.client.get(ME).json()
    lookups: list[Any] = []

    def refuse(name: str):
        def guard(*args: Any, **kwargs: Any):
            lookups.append((name, args[:2]))
            raise OSError("network access is not allowed during assessment")

        return guard

    # libpq resolves and connects to PostgreSQL in C. Any Python HTTP client (a model call)
    # resolves its host through socket.getaddrinfo or socket.create_connection.
    monkeypatch.setattr(socket, "getaddrinfo", refuse("getaddrinfo"))
    monkeypatch.setattr(socket, "create_connection", refuse("create_connection"))
    response = linh.assess(draft["id"])
    monkeypatch.undo()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["transfer_id"] == draft["id"]
    assert lookups == [], "assessment makes no model or other network call"
    row = stored(pg_engine, body["id"])
    assert (str(row.sandbox_id), str(row.transfer_id)) == (str(linh.sandbox_id), draft["id"])
    assert (row.decision, row.behavior_signal, row.recipient_signal) == (
        body["decision"],
        body["behavior_signal"],
        body["recipient_signal"],
    )
    assert row.reasons == body["reasons"] and row.policy_version == POLICY_VERSION
    assert re.fullmatch(r"[0-9a-f]{64}", row.facts_fingerprint)
    assert (row.assessed_at, row.expires_at) == (
        instant(body["assessed_at"]),
        instant(body["expires_at"]),
    )
    assert row.expires_at - row.assessed_at == ASSESSMENT_LIFETIME
    with Session(pg_engine) as db:
        assert row.assessed_at <= db.scalar(select(func.now())) < row.expires_at
    assert set(row.facts) >= {
        "transfer_id",
        "sender_account_id",
        "recipient_account_id",
        "amount_vnd",
        "sample_count",
        "median_vnd",
        "threshold_vnd",
        "restriction_id",
        "restriction_action",
        "policy_version",
    }
    assert money_and_transfers(pg_engine, linh.sandbox_id) == before
    assert linh.client.get(ME).json() == me_before

    fetched = linh.client.get(f"{TRANSFERS}/{draft['id']}").json()
    assert fetched["assessment"] == body
    assert (fetched["status"], fetched["reserved_amount_vnd"]) == ("DRAFT", 0)

    again = linh.assess(draft["id"]).json()
    assert again["id"] != body["id"]
    assert instant(again["assessed_at"]) >= instant(body["assessed_at"])
    assert stored(pg_engine, again["id"]).facts_fingerprint == row.facts_fingerprint, (
        "unchanged facts keep their fingerprint"
    )
    assert linh.client.get(f"{TRANSFERS}/{draft['id']}").json()["assessment"] == again
    listed = linh.client.get(TRANSFERS).json()["items"]
    assert next(item for item in listed if item["id"] == draft["id"])["assessment"] == again
    assert assessment_count(pg_engine, linh.sandbox_id) == 2


def test_assess_only_owned_active_transfers(browser, pg_engine: Engine):
    client = browser()
    linh = open_sandbox(client)
    an = as_actor(linh, "An")
    an_draft = an.draft("CAFE", 20_000)
    linh = as_actor(an, "Linh")
    other = open_sandbox(browser())
    other_draft = other.draft("CAFE", 20_000)
    history = next(
        item
        for item in linh.client.get(TRANSFERS, params={"limit": 100}).json()["items"]
        if item["status"] == "SUCCEEDED"
    )
    count = assessment_count(pg_engine, linh.sandbox_id)

    for transfer_id in (an_draft["id"], other_draft["id"], str(uuid.uuid4())):
        hidden = linh.assess(transfer_id)
        assert (hidden.status_code, error_code(hidden)) == (404, "NOT_FOUND"), hidden.text
    malformed = linh.assess("not-a-uuid")
    assert (malformed.status_code, error_code(malformed)) == (422, "VALIDATION_ERROR")

    canceled, overdue = linh.draft("CAFE", 20_000), linh.draft("CAFE", 30_000)
    with pg_engine.begin() as connection:
        connection.execute(
            update(models.Transfer)
            .where(models.Transfer.id == uuid.UUID(canceled["id"]))
            .values(status="CANCELED", completed_at=func.now())
        )
        connection.execute(
            update(models.Transfer)
            .where(models.Transfer.id == uuid.UUID(overdue["id"]))
            .values(expires_at=func.now() - timedelta(seconds=1))
        )
    for transfer_id in (history["id"], canceled["id"], overdue["id"]):
        conflict = linh.assess(transfer_id)
        assert (conflict.status_code, error_code(conflict)) == (409, "STATE_CONFLICT")
        current = conflict.json()["error"]["current_transfer"]
        assert current == linh.client.get(f"{TRANSFERS}/{transfer_id}").json()
        assert "assessment" not in conflict.json()["error"]
    assert assessment_count(pg_engine, linh.sandbox_id) == count

    # A held or operator-cleared transfer can be re-assessed without changing its state.
    held, ready = linh.draft("RISK_RECIPIENT", 20_000), linh.draft("RISK_RECIPIENT", 30_000)
    seeded = restriction_on(pg_engine, linh, "RISK_RECIPIENT")
    with pg_engine.begin() as connection:
        for transfer, status in ((held, "RISK_HELD"), (ready, "READY")):
            values: dict[str, Any] = {
                "status": status,
                "reserved_amount_vnd": transfer["amount_vnd"],
                "held_at": func.now(),
                "expires_at": func.now() + timedelta(minutes=15),
            }
            if status == "READY":
                values.update(
                    reviewed_by=uuid.UUID(actor_named(linh.bootstrap, "Ops")["id"]),
                    review_reason="[Synthetic test] Cleared.",
                    cleared_restriction_id=seeded.id,
                )
            connection.execute(
                update(models.Transfer)
                .where(models.Transfer.id == uuid.UUID(transfer["id"]))
                .values(**values)
            )
        connection.execute(
            update(models.Account)
            .where(models.Account.id == uuid.UUID(linh.wallet_id))
            .values(reserved_vnd=50_000)
        )
    before = money_and_transfers(pg_engine, linh.sandbox_id)
    for transfer, status in ((held, "RISK_HELD"), (ready, "READY")):
        response = linh.assess(transfer["id"])
        assert response.status_code == 200, response.text
        assert signals(response.json())[0] == "HOLD"
        fetched = linh.client.get(f"{TRANSFERS}/{transfer['id']}").json()
        assert (fetched["status"], fetched["reserved_amount_vnd"]) == (
            status,
            transfer["amount_vnd"],
        )
    assert money_and_transfers(pg_engine, linh.sandbox_id) == before

    denied = [
        (linh.assess(held["id"], headers={"X-CSRF-Token": linh.csrf}), 403, "ORIGIN_DENIED"),
        (linh.assess(held["id"], headers=dict(ORIGIN)), 403, "CSRF_FAILED"),
        (
            linh.assess(held["id"], headers=writes(linh.bootstrap["controller_csrf_token"])),
            403,
            "CSRF_FAILED",
        ),
        (
            browser().post(f"{TRANSFERS}/{held['id']}/assess", headers=writes(linh.csrf)),
            401,
            "SESSION_EXPIRED",
        ),
    ]
    ops = as_actor(linh, "Ops")
    denied.append((ops.assess(held["id"]), 403, "FORBIDDEN"))
    denied.append((ops.assess("not-a-uuid"), 403, "FORBIDDEN"))
    for response, status, code in denied:
        assert (response.status_code, error_code(response)) == (status, code), response.text
    assert assessment_count(pg_engine, linh.sandbox_id) == count + 2


def test_task6_operation_matches_contract(guardian_app):
    generated = TestClient(guardian_app).get("/openapi.json").json()["paths"]
    operation = generated[f"{API}/transfers/{{id}}/assess"]["post"]
    contract = OPENAPI["paths"]["/transfers/{id}/assess"]["post"]

    def parameters(op: dict[str, Any]) -> dict[str, tuple[Any, ...]]:
        return {
            p["name"]: (p["in"], p.get("required", False), p["schema"].get("type"))
            for p in op.get("parameters", [])
        }

    assert operation["operationId"] == contract["operationId"] == "assessTransfer"
    assert operation["tags"] == contract["tags"] == ["Customer"]
    assert operation["security"] == contract["security"] == [{"actorCookie": []}]
    assert parameters(operation) == parameters(contract)
    assert "requestBody" not in operation and "requestBody" not in contract
    success = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert success["$ref"] == "#/components/schemas/RiskAssessment"
