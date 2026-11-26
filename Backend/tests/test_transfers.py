"""Task 7: POST /transfers/{id}/confirm through HTTP against seeded sandboxes.

Rulings encoded here: confirmation re-evaluates current risk under locks and persists the
assessment it acted on. ALLOW or a current acknowledged WARN posts exactly one sender
TRANSFER_DEBIT and one recipient TRANSFER_CREDIT and returns SUCCEEDED. A WARN without a current
acknowledgement (missing, unknown, another transfer's, expired or with a different fingerprint)
commits a fresh assessment and returns 409 ACKNOWLEDGEMENT_REQUIRED carrying it, with nothing
reserved or posted. A current HOLD wins over any acknowledgement. Insufficient available funds is
409 INSUFFICIENT_FUNDS with no ledger, reservation or assessment write. Repeated confirmation of a
SUCCEEDED transfer returns the stored result unchanged; a terminal non-success state is 409
STATE_CONFLICT with the current transfer. State changes are audited with the request ID.
"""

import uuid
from datetime import timedelta
from pathlib import Path
from typing import Any

import yaml
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, update
from sqlalchemy.orm import Session

from app import models
from app.api.schemas import RiskAssessment, Transfer
from tests.conftest import API
from tests.money_support import (
    ORIGIN,
    account_row,
    add_restriction,
    as_actor,
    assert_money_invariants,
    assert_sanitized,
    assessment_count,
    audit_of,
    db_clock,
    error_code,
    error_of,
    instant,
    ledger_count,
    ledger_of,
    money,
    open_sandbox,
    stored_assessment,
    transfer_row,
    writes,
)

OPENAPI = yaml.safe_load(
    (Path(__file__).resolve().parents[2] / "docs/guardian/openapi.yaml").read_text(encoding="utf-8")
)


def signals(assessment: dict[str, Any]) -> tuple[str, str, str, list[str]]:
    return (
        assessment["decision"],
        assessment["behavior_signal"],
        assessment["recipient_signal"],
        [reason["code"] for reason in assessment["reasons"]],
    )


def acknowledgement_required(response) -> dict[str, Any]:
    """The fresh, committed assessment carried by a 409 ACKNOWLEDGEMENT_REQUIRED."""
    assert response.status_code == 409, response.text
    error = error_of(response)
    assert error["code"] == "ACKNOWLEDGEMENT_REQUIRED"
    assert set(error) == {"code", "message", "request_id", "assessment"}
    assert error["request_id"] == response.headers["x-request-id"]
    RiskAssessment.model_validate(error["assessment"])
    return error["assessment"]


def test_normal_transfer_posts_one_debit_credit_pair(browser, pg_engine: Engine):
    linh = open_sandbox(browser())
    assert money(linh.wallet()) == (10_000_000, 0, 10_000_000)
    cafe_id = linh.recipient_id("CAFE")
    cafe_before = account_row(pg_engine, cafe_id).balance_vnd
    draft = linh.draft("CAFE", 20_000)

    before = db_clock(pg_engine)
    confirmed = linh.confirm(draft["id"])
    after = db_clock(pg_engine)

    assert confirmed.status_code == 200, confirmed.text
    body = confirmed.json()
    Transfer.model_validate(body)
    assert (body["id"], body["status"], body["reserved_amount_vnd"], body["replayed"]) == (
        draft["id"],
        "SUCCEEDED",
        0,
        False,
    )
    assert before <= instant(body["completed_at"]) <= after, "completion uses database time"
    assert body["assessment"]["transfer_id"] == draft["id"]
    assert signals(body["assessment"]) == ("ALLOW", "NORMAL", "NONE", [])
    assert money(linh.wallet()) == (9_980_000, 0, 9_980_000)
    assert ledger_of(pg_engine, draft["id"]) == sorted(
        [(linh.wallet_id, "TRANSFER_DEBIT", -20_000), (cafe_id, "TRANSFER_CREDIT", 20_000)]
    )
    assert account_row(pg_engine, cafe_id).balance_vnd == cafe_before + 20_000
    row = transfer_row(pg_engine, draft["id"])
    assert (row.status, row.reserved_amount_vnd, row.held_at) == ("SUCCEEDED", 0, None)
    (event,) = audit_of(pg_engine, draft["id"])
    assert (event.event_type, event.actor_kind, event.target_type) == (
        "TRANSFER_SUCCEEDED",
        "CUSTOMER",
        "TRANSFER",
    )
    assert str(event.actor_id) == linh.actor_id("Linh")
    assert event.request_id == confirmed.headers["x-request-id"]
    assert (event.details["amount_vnd"], event.details["decision"]) == (20_000, "ALLOW")
    assert event.details["assessment_id"] == body["assessment"]["id"]
    assert_sanitized(event, linh.csrf, linh.client.cookies.get("guardian_session"))
    assert_money_invariants(pg_engine, linh.sandbox_id)

    # Repeating confirmation returns the stored result: no assessment, ledger or audit write.
    assessments, legs = (
        assessment_count(pg_engine, linh.sandbox_id),
        ledger_count(pg_engine, linh.sandbox_id),
    )
    for ack in (None, body["assessment"]["id"]):
        again = linh.confirm(draft["id"], ack)
        assert again.status_code == 200, again.text
        assert again.json() == body
    assert assessment_count(pg_engine, linh.sandbox_id) == assessments
    assert ledger_count(pg_engine, linh.sandbox_id) == legs
    assert len(audit_of(pg_engine, draft["id"])) == 1
    assert money(linh.wallet()) == (9_980_000, 0, 9_980_000)

    late_cancel = linh.cancel(draft["id"])
    assert (late_cancel.status_code, error_code(late_cancel)) == (409, "STATE_CONFLICT")
    assert error_of(late_cancel)["current_transfer"] == body
    assert linh.get(draft["id"]) == body
    assert_money_invariants(pg_engine, linh.sandbox_id)


def test_warning_requires_current_acknowledgement(browser, pg_engine: Engine):
    linh = open_sandbox(browser())
    warned = linh.draft("NEW_RECIPIENT", 8_000_000)
    other = linh.draft("NEW_RECIPIENT", 8_000_000)
    other_assessment = linh.assess(other["id"]).json()
    assert other_assessment["decision"] == "WARN"
    legs = ledger_count(pg_engine, linh.sandbox_id)

    missing = linh.confirm(warned["id"])
    fresh = acknowledgement_required(missing)
    assert fresh["transfer_id"] == warned["id"]
    assert signals(fresh) == ("WARN", "ANOMALOUS", "NONE", ["AMOUNT_ABOVE_BASELINE"])
    assert stored_assessment(pg_engine, fresh["id"]).facts_fingerprint, "committed before 409"
    current = linh.get(warned["id"])
    assert current["assessment"] == fresh
    assert (current["status"], current["reserved_amount_vnd"]) == ("DRAFT", 0)
    assert money(linh.wallet()) == (10_000_000, 0, 10_000_000), "nothing is reserved"

    seen = {fresh["id"]}
    for ack in (str(uuid.uuid4()), other_assessment["id"]):
        rejected = acknowledgement_required(linh.confirm(warned["id"], ack))
        assert rejected["id"] not in seen | {ack}, "each 409 carries a new assessment"
        seen.add(rejected["id"])

    # An acknowledgement past its five-minute lifetime is not current.
    expired = linh.assess(warned["id"]).json()
    with pg_engine.begin() as connection:
        connection.execute(
            update(models.RiskAssessment)
            .where(models.RiskAssessment.id == uuid.UUID(expired["id"]))
            .values(expires_at=func.now() - timedelta(seconds=1))
        )
    renewed = acknowledgement_required(linh.confirm(warned["id"], expired["id"]))
    assert renewed["id"] != expired["id"]

    # Facts change between acknowledgement and confirmation: a settled 20,000 payment adds a
    # sixth observation, so the unexpired acknowledgement no longer matches current facts.
    stale = linh.assess(warned["id"]).json()
    payment = linh.confirm(linh.draft("CAFE", 20_000)["id"])
    assert payment.json()["status"] == "SUCCEEDED", payment.text
    refreshed = acknowledgement_required(linh.confirm(warned["id"], stale["id"]))
    stale_row, refreshed_row = (
        stored_assessment(pg_engine, stale["id"]),
        stored_assessment(pg_engine, refreshed["id"]),
    )
    assert refreshed_row.facts_fingerprint != stale_row.facts_fingerprint
    assert (stale_row.facts["sample_count"], refreshed_row.facts["sample_count"]) == (5, 6)
    assert ledger_count(pg_engine, linh.sandbox_id) == legs + 2, "only the 20,000 payment posted"
    assert money(linh.wallet()) == (9_980_000, 0, 9_980_000)

    accepted = linh.confirm(warned["id"], refreshed["id"])
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "SUCCEEDED"
    assert signals(accepted.json()["assessment"])[0] == "WARN"
    assert ledger_of(pg_engine, warned["id"]) == sorted(
        [
            (linh.wallet_id, "TRANSFER_DEBIT", -8_000_000),
            (linh.recipient_id("NEW_RECIPIENT"), "TRANSFER_CREDIT", 8_000_000),
        ]
    )
    assert money(linh.wallet()) == (1_980_000, 0, 1_980_000)
    (event,) = audit_of(pg_engine, warned["id"])
    assert event.event_type == "TRANSFER_SUCCEEDED"
    assert event.details["acknowledged_assessment_id"] == refreshed["id"]

    again = linh.confirm(warned["id"], refreshed["id"])
    assert again.status_code == 200 and again.json() == accepted.json()
    assert ledger_count(pg_engine, linh.sandbox_id) == legs + 4, "succeeds once"
    assert_money_invariants(pg_engine, linh.sandbox_id)


def test_allow_then_new_hold_cannot_bypass(browser, pg_engine: Engine):
    linh = open_sandbox(browser())
    allowed = linh.draft("NEW_RECIPIENT", 20_000)
    allow = linh.assess(allowed["id"]).json()
    assert signals(allow) == ("ALLOW", "NORMAL", "NONE", [])
    warned = linh.draft("CAFE", 8_000_000)
    warn = linh.assess(warned["id"]).json()
    assert signals(warn)[0] == "WARN"

    # Ops adds reviewed HOLD decisions after the customer's assessments.
    new_hold = add_restriction(pg_engine, linh, "NEW_RECIPIENT", "HOLD")
    cafe_hold = add_restriction(pg_engine, linh, "CAFE", "HOLD")

    held = linh.confirm(allowed["id"], allow["id"])
    assert held.status_code == 200, held.text
    assert (held.json()["status"], held.json()["reserved_amount_vnd"]) == ("RISK_HELD", 20_000)
    assert signals(held.json()["assessment"]) == ("HOLD", "NORMAL", "HOLD", ["RECIPIENT_HOLD"])
    assert held.json()["assessment"]["reasons"][0]["restriction_id"] == new_hold

    held_warning = linh.confirm(warned["id"], warn["id"])
    assert held_warning.status_code == 200, held_warning.text
    assert held_warning.json()["status"] == "RISK_HELD"
    assert signals(held_warning.json()["assessment"]) == (
        "HOLD",
        "ANOMALOUS",
        "HOLD",
        ["RECIPIENT_HOLD", "AMOUNT_ABOVE_BASELINE"],
    )
    assert held_warning.json()["assessment"]["reasons"][0]["restriction_id"] == cafe_hold

    # Even a current, matching acknowledgement of a HOLD assessment never authorizes a debit.
    risky = linh.draft("RISK_RECIPIENT", 20_000)
    hold_assessment = linh.assess(risky["id"]).json()
    assert hold_assessment["decision"] == "HOLD"
    acknowledged = linh.confirm(risky["id"], hold_assessment["id"])
    assert acknowledged.status_code == 200, acknowledged.text
    assert acknowledged.json()["status"] == "RISK_HELD"

    for transfer in (allowed, warned, risky):
        assert ledger_of(pg_engine, transfer["id"]) == []
        (event,) = audit_of(pg_engine, transfer["id"])
        assert event.event_type == "TRANSFER_HELD"
    assert money(linh.wallet()) == (10_000_000, 8_040_000, 1_960_000)
    assert_money_invariants(pg_engine, linh.sandbox_id)


def test_insufficient_funds_never_overdraws(browser, pg_engine: Engine):
    binh = as_actor(open_sandbox(browser()), "Binh")
    assert money(binh.wallet()) == (5_000_000, 0, 5_000_000)
    assessments, legs = (
        assessment_count(pg_engine, binh.sandbox_id),
        ledger_count(pg_engine, binh.sandbox_id),
    )

    for symbol in ("CAFE", "RISK_RECIPIENT"):
        draft = binh.draft(symbol, 5_000_001)
        refused = binh.confirm(draft["id"])
        assert (refused.status_code, error_code(refused)) == (409, "INSUFFICIENT_FUNDS"), symbol
        assert set(error_of(refused)) == {"code", "message", "request_id"}
        assert (binh.get(draft["id"])["status"], binh.get(draft["id"])["reserved_amount_vnd"]) == (
            "DRAFT",
            0,
        )
        assert audit_of(pg_engine, draft["id"]) == []
    assert assessment_count(pg_engine, binh.sandbox_id) == assessments, "no partial write"
    assert ledger_count(pg_engine, binh.sandbox_id) == legs
    assert money(binh.wallet()) == (5_000_000, 0, 5_000_000)

    binh.held("RISK_RECIPIENT", 3_000_000)
    assert money(binh.wallet()) == (5_000_000, 3_000_000, 2_000_000)
    reserved_elsewhere = binh.confirm(binh.draft("CAFE", 2_000_001)["id"])
    assert error_code(reserved_elsewhere) == "INSUFFICIENT_FUNDS", (
        "reserved funds are not spendable"
    )
    exact = binh.confirm(binh.draft("CAFE", 2_000_000)["id"])
    assert exact.status_code == 200 and exact.json()["status"] == "SUCCEEDED", exact.text
    assert money(binh.wallet()) == (3_000_000, 3_000_000, 0)
    assert_money_invariants(pg_engine, binh.sandbox_id)


def test_confirm_requires_owner_csrf_and_strict_body(browser, pg_engine: Engine):
    client = browser()
    linh = open_sandbox(client)
    draft = linh.draft("CAFE", 20_000)
    an = as_actor(linh, "An")
    an_draft = an.draft("CAFE", 20_000)
    linh = as_actor(an, "Linh")
    other = open_sandbox(browser())
    other_draft = other.draft("CAFE", 20_000)
    path = f"{API}/transfers/{draft['id']}"

    denials = [
        (linh.confirm(draft["id"], headers={"X-CSRF-Token": linh.csrf}), 403, "ORIGIN_DENIED"),
        (linh.confirm(draft["id"], headers=dict(ORIGIN)), 403, "CSRF_FAILED"),
        (
            linh.confirm(draft["id"], headers=writes(linh.bootstrap["controller_csrf_token"])),
            403,
            "CSRF_FAILED",
        ),
        (linh.cancel(draft["id"], headers=dict(ORIGIN)), 403, "CSRF_FAILED"),
        (
            browser().post(f"{path}/confirm", json={}, headers=writes(linh.csrf)),
            401,
            "SESSION_EXPIRED",
        ),
        (browser().post(f"{path}/cancel", headers=writes(linh.csrf)), 401, "SESSION_EXPIRED"),
    ]
    for transfer_id in (an_draft["id"], other_draft["id"], str(uuid.uuid4())):
        denials.append((linh.confirm(transfer_id), 404, "NOT_FOUND"))
        denials.append((linh.cancel(transfer_id), 404, "NOT_FOUND"))
    for body in (
        {"acknowledged_assessment_id": None},
        {"acknowledged_assessment_id": "not-a-uuid"},
        {"status": "SUCCEEDED"},
        [],
    ):
        denials.append((linh.confirm(draft["id"], body=body), 422, "VALIDATION_ERROR"))
    denials.append(
        (
            client.post(f"{path}/confirm", headers=writes(linh.csrf)),
            422,
            "VALIDATION_ERROR",
        )
    )
    denials.append((linh.confirm("not-a-uuid"), 422, "VALIDATION_ERROR"))
    ops = as_actor(linh, "Ops")
    denials.append((ops.confirm(draft["id"]), 403, "FORBIDDEN"))
    denials.append((ops.cancel(draft["id"]), 403, "FORBIDDEN"))
    for response, status, code in denials:
        assert (response.status_code, error_code(response)) == (status, code), response.text

    with Session(pg_engine) as db:
        for transfer_id in (draft["id"], an_draft["id"], other_draft["id"]):
            row = db.get(models.Transfer, uuid.UUID(transfer_id))
            assert row is not None and (row.status, row.reserved_amount_vnd) == ("DRAFT", 0)
    for sandbox_id in (linh.sandbox_id, other.sandbox_id):
        assert_money_invariants(pg_engine, sandbox_id)
    assert ledger_of(pg_engine, draft["id"]) == []


def test_task7_operations_match_contract(guardian_app):
    generated = TestClient(guardian_app).get("/openapi.json").json()["paths"]

    def parameters(operation: dict[str, Any]) -> dict[str, tuple[Any, ...]]:
        return {
            p["name"]: (p["in"], p.get("required", False), p["schema"].get("type"))
            for p in operation.get("parameters", [])
        }

    for path, operation_id in (
        ("/transfers/{id}/confirm", "confirmTransfer"),
        ("/transfers/{id}/cancel", "cancelTransfer"),
    ):
        operation = generated[f"{API}{path}"]["post"]
        contract = OPENAPI["paths"][path]["post"]
        assert operation["operationId"] == contract["operationId"] == operation_id
        assert operation["tags"] == contract["tags"] == ["Customer"]
        assert operation["security"] == contract["security"] == [{"actorCookie": []}]
        assert parameters(operation) == parameters(contract), path
        success = operation["responses"]["200"]["content"]["application/json"]["schema"]
        assert success["$ref"] == "#/components/schemas/Transfer"
        assert ("requestBody" in operation) == ("requestBody" in contract), path
    confirm = generated[f"{API}/transfers/{{id}}/confirm"]["post"]
    assert confirm["requestBody"]["required"] is True
    schema = confirm["requestBody"]["content"]["application/json"]["schema"]
    assert schema["$ref"] == "#/components/schemas/ConfirmTransfer"
