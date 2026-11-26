"""Task 8: operator hold review and customer reconfirmation from READY, through HTTP.

Rulings encoded here:
- listHolds is OPERATOR only: the caller sandbox's RISK_HELD and READY transfers of every
  customer, newest created_at first then ID descending, total before paging. The sandbox's
  passed deadlines are first reconciled to EXPIRED (committed; SYSTEM audit with the list
  request ID), so a hold past its deadline is never listed.
- APPROVE of a RISK_HELD transfer sets READY with reviewed_by, review_reason and
  cleared_restriction_id = the recipient's current active HOLD restriction, read under the
  recipient lock. When no HOLD restriction is currently active (revoked or expired, or only a
  WARN remains) clearance binds to the restriction that placed the hold; it can never become
  active again, so it overrides nothing. Reservation and original deadline are kept; nothing
  is posted.
- REJECT of a RISK_HELD transfer sets REJECTED, releases the reservation once, sets
  completed_at and records the reviewer and reason.
- Repeating APPROVE on READY or REJECT on REJECTED returns the stored transfer, whatever the
  reason. Any other state or decision is 409 STATE_CONFLICT with current_transfer.
- Customer confirm from READY: an active HOLD other than cleared_restriction_id re-holds
  (RISK_HELD, no new reservation, same held_at and deadline, clearance fields cleared). The
  exact cleared HOLD is overridden; a WARN restriction or a behavioral warning still needs a
  current acknowledgement (409 ACKNOWLEDGEMENT_REQUIRED with a committed fresh assessment).
  Execution reduces balance and reservation together and posts one debit/credit pair.
- Audit: TRANSFER_APPROVED and TRANSFER_REJECTED (OPERATOR actor, reason, restriction IDs),
  TRANSFER_HELD from READY on re-hold, TRANSFER_SUCCEEDED from READY.
"""

import uuid
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Connection, Engine, func, insert, update

from app import models
from app.api.schemas import RiskAssessment, Transfer, TransferList
from app.transfers.locking import recipient_policy_key
from tests.conftest import API
from tests.money_support import (
    HOLD_LIFETIME,
    ORIGIN,
    Customer,
    account_row,
    actor_in,
    add_restriction,
    assert_money_invariants,
    assert_sanitized,
    audit_of,
    db_clock,
    error_code,
    error_of,
    instant,
    ledger_count,
    ledger_of,
    money,
    open_sandbox,
    operator_in,
    pass_deadline,
    revoke_restriction,
    stored_assessment,
    transfer_row,
    with_controller,
    writes,
)
from tests.race_support import advisory_gate, race, row_gate, same_actor

OPENAPI = yaml.safe_load(
    (Path(__file__).resolve().parents[2] / "docs/guardian/openapi.yaml").read_text(encoding="utf-8")
)
HOLDS = f"{API}/ops/holds"
APPROVAL = "[Synthetic test] Buyer verified this payee independently; clear this transfer only."
REJECTION = "[Synthetic test] Payee matches the reviewed advance-fee pattern; release funds."
REVIEW_EVENTS = ("TRANSFER_APPROVED", "TRANSFER_REJECTED")


def review_path(transfer_id: str) -> str:
    return f"{API}/ops/transfers/{transfer_id}/review"


def review(
    ops: Customer,
    transfer_id: str,
    decision: str,
    reason: str | None = None,
    *,
    body: Any = None,
    headers: dict[str, str] | None = None,
):
    if body is None:
        body = {
            "decision": decision,
            "reason": reason or (APPROVAL if decision == "APPROVE" else REJECTION),
        }
    return ops.client.post(
        review_path(transfer_id),
        json=body,
        headers=writes(ops.csrf) if headers is None else headers,
    )


def approved(ops: Customer, transfer_id: str) -> dict[str, Any]:
    response = review(ops, transfer_id, "APPROVE")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "READY", response.text
    return response.json()


def listed_holds(ops: Customer, **params: Any) -> dict[str, Any]:
    response = ops.client.get(HOLDS, params=params)
    assert response.status_code == 200, response.text
    TransferList.model_validate(response.json())
    return response.json()


def restriction_of(transfer: dict[str, Any]) -> str:
    """The restriction that the transfer's latest assessment cites first."""
    return transfer["assessment"]["reasons"][0]["restriction_id"]


def signals(assessment: dict[str, Any]) -> tuple[str, str, str, list[str]]:
    return (
        assessment["decision"],
        assessment["behavior_signal"],
        assessment["recipient_signal"],
        [reason["code"] for reason in assessment["reasons"]],
    )


def acknowledgement_required(response) -> dict[str, Any]:
    assert response.status_code == 409, response.text
    error = error_of(response)
    assert error["code"] == "ACKNOWLEDGEMENT_REQUIRED"
    assert set(error) == {"code", "message", "request_id", "assessment"}
    RiskAssessment.model_validate(error["assessment"])
    return error["assessment"]


def state_conflict(response) -> dict[str, Any]:
    assert (response.status_code, error_code(response)) == (409, "STATE_CONFLICT"), response.text
    return error_of(response)["current_transfer"]


def event_types(pg_engine: Engine, transfer_id: str) -> list[str]:
    return [event.event_type for event in audit_of(pg_engine, transfer_id)]


def test_approve_is_ready_without_debit(browser, pg_engine: Engine):
    linh = open_sandbox(browser())
    assert linh.confirm(linh.draft("CAFE", 20_000)["id"]).json()["status"] == "SUCCEEDED"
    held = linh.held("RISK_RECIPIENT", 20_000)
    restriction = restriction_of(held)
    recipient_id = held["recipient"]["id"]
    recipient_before = account_row(pg_engine, recipient_id).balance_vnd
    stored = transfer_row(pg_engine, held["id"])
    ops = operator_in(browser(), linh)
    legs = ledger_count(pg_engine, linh.sandbox_id)

    approval = review(ops, held["id"], "APPROVE")

    assert approval.status_code == 200, approval.text
    body = approval.json()
    Transfer.model_validate(body)
    assert (body["id"], body["status"], body["reserved_amount_vnd"], body["completed_at"]) == (
        held["id"],
        "READY",
        20_000,
        None,
    )
    assert body["review_reason"] == APPROVAL
    assert body["expires_at"] == held["expires_at"], "the original deadline is kept"
    assert body["assessment"] == held["assessment"], "approval is not a risk assessment"
    row = transfer_row(pg_engine, held["id"])
    assert (str(row.reviewed_by), row.review_reason, str(row.cleared_restriction_id)) == (
        linh.actor_id("Ops"),
        APPROVAL,
        restriction,
    )
    assert (row.held_at, row.expires_at, row.completed_at) == (
        stored.held_at,
        stored.expires_at,
        None,
    )
    assert money(linh.wallet()) == (9_980_000, 20_000, 9_960_000), "no debit, still reserved"
    assert ledger_of(pg_engine, held["id"]) == []
    assert ledger_count(pg_engine, linh.sandbox_id) == legs
    assert account_row(pg_engine, recipient_id).balance_vnd == recipient_before
    held_event, approval_event = audit_of(pg_engine, held["id"])
    assert held_event.event_type == "TRANSFER_HELD"
    assert (
        approval_event.event_type,
        approval_event.actor_kind,
        str(approval_event.actor_id),
        approval_event.target_type,
        approval_event.request_id,
    ) == (
        "TRANSFER_APPROVED",
        "OPERATOR",
        linh.actor_id("Ops"),
        "TRANSFER",
        approval.headers["x-request-id"],
    )
    details = approval_event.details
    assert (details["reason"], details["cleared_restriction_id"]) == (APPROVAL, restriction)
    assert (details["from_status"], details["reserved_vnd"]) == ("RISK_HELD", 20_000)
    assert_sanitized(approval_event, ops.csrf, ops.client.cookies.get("guardian_session"))

    # Repeating the decision, with any reason, returns the stored READY transfer unchanged.
    for reason in (APPROVAL, "[Synthetic test] Repeated click."):
        again = review(ops, held["id"], "APPROVE", reason)
        assert again.status_code == 200, again.text
        assert again.json() == body
    assert event_types(pg_engine, held["id"]) == ["TRANSFER_HELD", "TRANSFER_APPROVED"]
    assert transfer_row(pg_engine, held["id"]).review_reason == APPROVAL
    assert linh.get(held["id"]) == body
    assert listed_holds(ops)["items"] == [body]
    assert money(linh.wallet()) == (9_980_000, 20_000, 9_960_000)
    assert_money_invariants(pg_engine, linh.sandbox_id)


def test_ready_requires_customer_reconfirm(browser, pg_engine: Engine):
    linh = open_sandbox(browser())
    ops = operator_in(browser(), linh)
    held = linh.held("RISK_RECIPIENT", 20_000)
    other = linh.held("RISK_RECIPIENT", 30_000)
    restriction = restriction_of(held)
    recipient_id = held["recipient"]["id"]
    recipient_before = account_row(pg_engine, recipient_id).balance_vnd
    ready = approved(ops, held["id"])

    # READY never executes by itself: reads, the hold list and the operator cannot send it.
    assert linh.get(held["id"]) == ready
    assert money(linh.wallet()) == (10_000_000, 50_000, 9_950_000)
    assert {item["id"] for item in listed_holds(ops)["items"]} == {held["id"], other["id"]}
    refused = ops.confirm(held["id"])
    assert (refused.status_code, error_code(refused)) == (403, "FORBIDDEN")
    assert ledger_of(pg_engine, held["id"]) == []
    assert transfer_row(pg_engine, held["id"]).status == "READY"

    before = db_clock(pg_engine)
    confirmed = linh.confirm(held["id"])
    after = db_clock(pg_engine)

    assert confirmed.status_code == 200, confirmed.text
    body = confirmed.json()
    Transfer.model_validate(body)
    assert (body["status"], body["reserved_amount_vnd"], body["review_reason"]) == (
        "SUCCEEDED",
        0,
        APPROVAL,
    )
    assert before <= instant(body["completed_at"]) <= after, "completion uses database time"
    assert signals(body["assessment"]) == ("ALLOW", "NORMAL", "NONE", []), "exact override"
    assert ledger_of(pg_engine, held["id"]) == sorted(
        [(linh.wallet_id, "TRANSFER_DEBIT", -20_000), (recipient_id, "TRANSFER_CREDIT", 20_000)]
    )
    # Balance and reservation fall together; the other hold's reservation stays.
    assert money(linh.wallet()) == (9_980_000, 30_000, 9_950_000)
    assert account_row(pg_engine, recipient_id).balance_vnd == recipient_before + 20_000
    row = transfer_row(pg_engine, held["id"])
    assert (row.status, str(row.cleared_restriction_id), str(row.reviewed_by)) == (
        "SUCCEEDED",
        restriction,
        linh.actor_id("Ops"),
    )
    event = audit_of(pg_engine, held["id"])[-1]
    assert (event.event_type, event.actor_kind, event.request_id) == (
        "TRANSFER_SUCCEEDED",
        "CUSTOMER",
        confirmed.headers["x-request-id"],
    )
    assert (event.details["from_status"], event.details["released_vnd"]) == ("READY", 20_000)
    assert event.details["cleared_restriction_id"] == restriction
    assert event.details["assessment_id"] == body["assessment"]["id"]

    # Executes once: repeating returns the stored result; cancel is a conflict.
    legs = ledger_count(pg_engine, linh.sandbox_id)
    again = linh.confirm(held["id"])
    assert again.status_code == 200 and again.json() == body, again.text
    assert state_conflict(linh.cancel(held["id"])) == body
    assert state_conflict(review(ops, held["id"], "APPROVE")) == body
    assert ledger_count(pg_engine, linh.sandbox_id) == legs
    assert event_types(pg_engine, held["id"]).count("TRANSFER_SUCCEEDED") == 1

    # Clearance belongs to one transfer: the restriction still holds everything else.
    still_held = linh.confirm(other["id"])
    assert still_held.status_code == 200 and still_held.json()["status"] == "RISK_HELD"
    an = actor_in(browser(), linh, "An")
    an_assessment = an.assess(an.draft("RISK_RECIPIENT", 20_000)["id"]).json()
    assert (an_assessment["decision"], restriction_of({"assessment": an_assessment})) == (
        "HOLD",
        restriction,
    )
    assert_money_invariants(pg_engine, linh.sandbox_id)


def test_ready_still_requires_behavioral_acknowledgement(browser, pg_engine: Engine):
    linh = open_sandbox(browser())
    ops = operator_in(browser(), linh)
    held = linh.held("RISK_RECIPIENT", 8_000_000)
    assert signals(held["assessment"]) == (
        "HOLD",
        "ANOMALOUS",
        "HOLD",
        ["RECIPIENT_HOLD", "AMOUNT_ABOVE_BASELINE"],
    )
    approved(ops, held["id"])

    # Clearance overrides only the restriction; the independent amount warning remains.
    fresh: dict[str, Any] = {}
    for ack in (None, held["assessment"]["id"]):
        fresh = acknowledgement_required(linh.confirm(held["id"], ack))
        assert fresh["transfer_id"] == held["id"]
        assert signals(fresh) == ("WARN", "ANOMALOUS", "NONE", ["AMOUNT_ABOVE_BASELINE"])
        assert stored_assessment(pg_engine, fresh["id"]).facts_fingerprint, "committed"
        current = linh.get(held["id"])
        assert (current["status"], current["reserved_amount_vnd"]) == ("READY", 8_000_000)
        assert current["assessment"] == fresh
        assert money(linh.wallet()) == (10_000_000, 8_000_000, 2_000_000)
        assert ledger_of(pg_engine, held["id"]) == []

    accepted = linh.confirm(held["id"], fresh["id"])
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "SUCCEEDED"
    assert signals(accepted.json()["assessment"])[0] == "WARN"
    assert money(linh.wallet()) == (2_000_000, 0, 2_000_000)
    assert len(ledger_of(pg_engine, held["id"])) == 2
    event = audit_of(pg_engine, held["id"])[-1]
    assert event.event_type == "TRANSFER_SUCCEEDED"
    assert (event.details["from_status"], event.details["acknowledged_assessment_id"]) == (
        "READY",
        fresh["id"],
    )
    assert_money_invariants(pg_engine, linh.sandbox_id)


def test_new_restriction_invalidates_clearance(browser, pg_engine: Engine):
    linh = open_sandbox(browser())
    ops = operator_in(browser(), linh)
    held = linh.held("RISK_RECIPIENT", 20_000)
    original = restriction_of(held)
    first_hold = transfer_row(pg_engine, held["id"])
    approved(ops, held["id"])

    # Ops replaces the decision: revoke the cleared restriction, add a new HOLD.
    revoke_restriction(pg_engine, linh, original)
    replacement = add_restriction(pg_engine, linh, "RISK_RECIPIENT", "HOLD")
    events_before = len(audit_of(pg_engine, held["id"]))

    rehold = linh.confirm(held["id"])

    assert rehold.status_code == 200, rehold.text
    body = rehold.json()
    assert (body["status"], body["reserved_amount_vnd"], body["review_reason"]) == (
        "RISK_HELD",
        20_000,
        None,
    )
    assert body["expires_at"] == held["expires_at"], "no deadline extension"
    assert signals(body["assessment"]) == ("HOLD", "NORMAL", "HOLD", ["RECIPIENT_HOLD"])
    assert restriction_of(body) == replacement
    row = transfer_row(pg_engine, held["id"])
    assert (row.reviewed_by, row.review_reason, row.cleared_restriction_id) == (None, None, None)
    assert (row.held_at, row.expires_at) == (first_hold.held_at, first_hold.expires_at)
    assert money(linh.wallet()) == (10_000_000, 20_000, 9_980_000), "no second reservation"
    assert ledger_of(pg_engine, held["id"]) == []
    events = audit_of(pg_engine, held["id"])
    assert len(events) == events_before + 1
    event = events[-1]
    assert (event.event_type, event.actor_kind) == ("TRANSFER_HELD", "CUSTOMER")
    assert (event.details["from_status"], event.details["restriction_id"]) == (
        "READY",
        replacement,
    )
    assert event.details["invalidated_restriction_id"] == original
    assert (event.details["reserved_vnd"], event.details["newly_reserved_vnd"]) == (20_000, 0)

    again = linh.confirm(held["id"])
    assert again.status_code == 200 and again.json() == body, "repeat returns the hold"
    assert len(audit_of(pg_engine, held["id"])) == events_before + 1
    assert [item["status"] for item in listed_holds(ops)["items"]] == ["RISK_HELD"]

    # A second review clears the replacement; the customer's reconfirmation then executes once.
    approved(ops, held["id"])
    assert str(transfer_row(pg_engine, held["id"]).cleared_restriction_id) == replacement
    executed = linh.confirm(held["id"])
    assert executed.status_code == 200 and executed.json()["status"] == "SUCCEEDED"
    assert money(linh.wallet()) == (9_980_000, 0, 9_980_000)

    # A changed decision that is only a WARN also invalidates clearance: it needs a current
    # acknowledgement, and the stale clearance cannot skip it.
    cafe_hold = add_restriction(pg_engine, linh, "CAFE", "HOLD")
    to_cafe = linh.held("CAFE", 20_000)
    approved(ops, to_cafe["id"])
    revoke_restriction(pg_engine, linh, cafe_hold)
    cafe_warning = add_restriction(pg_engine, linh, "CAFE", "WARN")
    warned = acknowledgement_required(linh.confirm(to_cafe["id"]))
    assert signals(warned) == ("WARN", "NORMAL", "WARN", ["RECIPIENT_WARNING"])
    assert restriction_of({"assessment": warned}) == cafe_warning
    assert transfer_row(pg_engine, to_cafe["id"]).status == "READY"
    assert money(linh.wallet()) == (9_980_000, 20_000, 9_960_000)
    sent = linh.confirm(to_cafe["id"], warned["id"])
    assert sent.status_code == 200 and sent.json()["status"] == "SUCCEEDED", sent.text
    assert money(linh.wallet()) == (9_960_000, 0, 9_960_000)
    assert_money_invariants(pg_engine, linh.sandbox_id)


def test_approval_binds_the_restriction_in_force(browser, pg_engine: Engine):
    linh = open_sandbox(browser())
    ops = operator_in(browser(), linh)
    held = linh.held("RISK_RECIPIENT", 20_000)
    original = restriction_of(held)

    # The decision is replaced while the transfer waits for review: Ops clears the new one.
    revoke_restriction(pg_engine, linh, original)
    replacement = add_restriction(pg_engine, linh, "RISK_RECIPIENT", "HOLD")
    approved(ops, held["id"])
    assert str(transfer_row(pg_engine, held["id"]).cleared_restriction_id) == replacement
    details = audit_of(pg_engine, held["id"], "TRANSFER_APPROVED")[0].details
    assert (details["cleared_restriction_id"], details["current_restriction_id"]) == (
        replacement,
        replacement,
    )
    sent = linh.confirm(held["id"])
    assert sent.status_code == 200 and sent.json()["status"] == "SUCCEEDED", sent.text
    assert money(linh.wallet()) == (9_980_000, 0, 9_980_000)

    # Only a WARN is in force at review time: clearance never overrides a warning, so it binds
    # the HOLD that placed the transfer and the customer must still acknowledge the WARN.
    cafe_hold = add_restriction(pg_engine, linh, "CAFE", "HOLD")
    to_cafe = linh.held("CAFE", 20_000)
    revoke_restriction(pg_engine, linh, cafe_hold)
    cafe_warning = add_restriction(pg_engine, linh, "CAFE", "WARN")
    approved(ops, to_cafe["id"])
    assert str(transfer_row(pg_engine, to_cafe["id"]).cleared_restriction_id) == cafe_hold
    warned = acknowledgement_required(linh.confirm(to_cafe["id"]))
    assert signals(warned) == ("WARN", "NORMAL", "WARN", ["RECIPIENT_WARNING"])
    assert restriction_of({"assessment": warned}) == cafe_warning
    assert money(linh.wallet()) == (9_980_000, 20_000, 9_960_000)
    assert_money_invariants(pg_engine, linh.sandbox_id)


def test_false_positive_correction_paths(browser, pg_engine: Engine):
    linh = open_sandbox(browser(), "FALSE_POSITIVE")
    ops = operator_in(browser(), linh)
    canceled_path = linh.held("SHOP_REAL", 20_000)
    approved_path = linh.held("SHOP_REAL", 30_000)
    mistaken = restriction_of(approved_path)
    revoke_restriction(pg_engine, linh, mistaken)

    # Revoking the restriction alone never sends a held transfer.
    for transfer in (canceled_path, approved_path):
        unchanged = linh.confirm(transfer["id"])
        assert unchanged.status_code == 200 and unchanged.json()["status"] == "RISK_HELD"
        assert ledger_of(pg_engine, transfer["id"]) == []
    assert money(linh.wallet()) == (10_000_000, 50_000, 9_950_000)

    assert linh.cancel(canceled_path["id"]).json()["status"] == "CANCELED"
    assert money(linh.wallet()) == (10_000_000, 30_000, 9_970_000), "released immediately"

    # Approval with no restriction in force binds the (revoked) restriction that held it.
    ready = approved(ops, approved_path["id"])
    assert ready["expires_at"] == approved_path["expires_at"]
    assert str(transfer_row(pg_engine, approved_path["id"]).cleared_restriction_id) == mistaken
    approval_event = audit_of(pg_engine, approved_path["id"])[-1]
    assert approval_event.event_type == "TRANSFER_APPROVED"
    assert approval_event.details["cleared_restriction_id"] == mistaken
    assert approval_event.details["current_restriction_id"] is None
    assert money(linh.wallet()) == (10_000_000, 30_000, 9_970_000)

    sent = linh.confirm(approved_path["id"])
    assert sent.status_code == 200, sent.text
    assert sent.json()["status"] == "SUCCEEDED"
    assert signals(sent.json()["assessment"]) == ("ALLOW", "NORMAL", "NONE", [])
    assert money(linh.wallet()) == (9_970_000, 0, 9_970_000)
    assert_money_invariants(pg_engine, linh.sandbox_id)


def test_ready_keeps_original_deadline(browser, pg_engine: Engine):
    linh = open_sandbox(browser())
    ops = operator_in(browser(), linh)
    held = linh.held("RISK_RECIPIENT", 20_000)
    stored = transfer_row(pg_engine, held["id"])
    assert stored.expires_at - stored.held_at == HOLD_LIFETIME

    ready = approved(ops, held["id"])
    assert instant(ready["expires_at"]) == stored.expires_at
    row = transfer_row(pg_engine, held["id"])
    assert (row.held_at, row.expires_at) == (stored.held_at, stored.expires_at)

    # The original deadline passes while READY: nothing executes, the reservation is released.
    pass_deadline(pg_engine, held["id"])
    current = state_conflict(linh.confirm(held["id"]))
    assert (current["status"], current["reserved_amount_vnd"]) == ("EXPIRED", 0)
    assert transfer_row(pg_engine, held["id"]).status == "EXPIRED", "committed before the 409"
    assert ledger_of(pg_engine, held["id"]) == []
    assert money(linh.wallet()) == (10_000_000, 0, 10_000_000)
    (expired,) = audit_of(pg_engine, held["id"], "TRANSFER_EXPIRED")
    assert (expired.details["from_status"], expired.details["released_vnd"]) == ("READY", 20_000)
    assert state_conflict(review(ops, held["id"], "APPROVE"))["status"] == "EXPIRED"

    # A review after the hold's deadline: the expiry wins and is committed first.
    late = linh.held("RISK_RECIPIENT", 30_000)
    pass_deadline(pg_engine, late["id"])
    for decision in ("APPROVE", "REJECT"):
        current = state_conflict(review(ops, late["id"], decision))
        assert (current["status"], current["reserved_amount_vnd"]) == ("EXPIRED", 0)
    assert event_types(pg_engine, late["id"]) == ["TRANSFER_HELD", "TRANSFER_EXPIRED"]
    assert money(linh.wallet()) == (10_000_000, 0, 10_000_000)

    # The hold list reconciles a READY past its deadline before listing.
    listed_ready = linh.held("RISK_RECIPIENT", 40_000)
    approved(ops, listed_ready["id"])
    pass_deadline(pg_engine, listed_ready["id"])
    response = ops.client.get(HOLDS)
    assert response.status_code == 200, response.text
    assert response.json()["items"] == [] and response.json()["total"] == 0
    assert transfer_row(pg_engine, listed_ready["id"]).status == "EXPIRED"
    (swept,) = audit_of(pg_engine, listed_ready["id"], "TRANSFER_EXPIRED")
    assert (swept.actor_kind, swept.request_id) == ("SYSTEM", response.headers["x-request-id"])
    assert money(linh.wallet()) == (10_000_000, 0, 10_000_000)
    assert_money_invariants(pg_engine, linh.sandbox_id)


def test_reject_releases_once(browser, pg_engine: Engine):
    linh = open_sandbox(browser())
    ops = operator_in(browser(), linh)
    assert linh.confirm(linh.draft("CAFE", 20_000)["id"]).json()["status"] == "SUCCEEDED"
    held = linh.held("RISK_RECIPIENT", 20_000)
    bystander = linh.held("RISK_RECIPIENT", 30_000)
    assert money(linh.wallet()) == (9_980_000, 50_000, 9_930_000)

    before = db_clock(pg_engine)
    rejection = review(ops, held["id"], "REJECT")
    after = db_clock(pg_engine)

    assert rejection.status_code == 200, rejection.text
    body = rejection.json()
    Transfer.model_validate(body)
    assert (body["status"], body["reserved_amount_vnd"], body["review_reason"]) == (
        "REJECTED",
        0,
        REJECTION,
    )
    assert before <= instant(body["completed_at"]) <= after
    row = transfer_row(pg_engine, held["id"])
    assert (str(row.reviewed_by), row.cleared_restriction_id) == (linh.actor_id("Ops"), None)
    assert money(linh.wallet()) == (9_980_000, 30_000, 9_950_000), "only its own amount"
    for _ in range(2):
        again = review(ops, held["id"], "REJECT", "[Synthetic test] Repeated click.")
        assert again.status_code == 200 and again.json() == body, again.text
    assert money(linh.wallet()) == (9_980_000, 30_000, 9_950_000), "released once"
    (event,) = audit_of(pg_engine, held["id"], "TRANSFER_REJECTED")
    assert (event.actor_kind, str(event.actor_id), event.request_id) == (
        "OPERATOR",
        linh.actor_id("Ops"),
        rejection.headers["x-request-id"],
    )
    assert (event.details["reason"], event.details["from_status"]) == (REJECTION, "RISK_HELD")
    assert event.details["released_vnd"] == 20_000
    assert_sanitized(event, ops.csrf)

    # A different decision or a customer command after rejection is a conflict.
    assert state_conflict(review(ops, held["id"], "APPROVE")) == body
    assert state_conflict(linh.confirm(held["id"])) == body
    assert state_conflict(linh.cancel(held["id"])) == body
    assert ledger_of(pg_engine, held["id"]) == []
    assert [item["id"] for item in listed_holds(ops)["items"]] == [bystander["id"]]
    assert_money_invariants(pg_engine, linh.sandbox_id)


def test_review_outside_held_state_conflicts(browser, pg_engine: Engine):
    linh = open_sandbox(browser())
    ops = operator_in(browser(), linh)
    draft = linh.draft("CAFE", 20_000)
    paid = linh.confirm(linh.draft("CAFE", 10_000)["id"]).json()
    canceled = linh.held("RISK_RECIPIENT", 20_000)
    assert linh.cancel(canceled["id"]).json()["status"] == "CANCELED"
    ready = approved(ops, linh.held("RISK_RECIPIENT", 30_000)["id"])

    for transfer_id in (draft["id"], paid["id"], canceled["id"]):
        expected = linh.get(transfer_id)
        for decision in ("APPROVE", "REJECT"):
            assert state_conflict(review(ops, transfer_id, decision)) == expected
    # REJECT after APPROVE is a different decision: the READY transfer and its money stay.
    assert state_conflict(review(ops, ready["id"], "REJECT")) == ready
    assert linh.get(ready["id"]) == ready
    assert money(linh.wallet()) == (9_990_000, 30_000, 9_960_000)
    assert linh.get(draft["id"])["status"] == "DRAFT"
    for transfer_id in (draft["id"], paid["id"], canceled["id"], ready["id"]):
        assert not set(event_types(pg_engine, transfer_id)) & {"TRANSFER_REJECTED"}
    assert_money_invariants(pg_engine, linh.sandbox_id)


def test_list_holds_is_scoped_paginated_and_deterministic(browser, pg_engine: Engine):
    linh = open_sandbox(browser())
    ops = operator_in(browser(), linh)
    first = linh.held("RISK_RECIPIENT", 20_000)
    second = linh.held("RISK_RECIPIENT", 30_000)
    third = linh.held("RISK_RECIPIENT", 40_000)
    due = linh.held("RISK_RECIPIENT", 50_000)
    linh.draft("CAFE", 10_000)
    linh.confirm(linh.draft("CAFE", 10_000)["id"])
    assert linh.cancel(linh.held("RISK_RECIPIENT", 10_000)["id"]).json()["status"] == "CANCELED"
    assert review(ops, linh.held("RISK_RECIPIENT", 10_000)["id"], "REJECT").status_code == 200
    an = actor_in(browser(), linh, "An")
    an_hold = an.held("RISK_RECIPIENT", 20_000)
    approved(ops, second["id"])
    pass_deadline(pg_engine, due["id"])
    other = open_sandbox(browser())
    other_ops = operator_in(browser(), other)
    other_hold = other.held("RISK_RECIPIENT", 20_000)

    everything = listed_holds(ops, limit=100)
    expected = [an_hold["id"], third["id"], second["id"], first["id"]]
    assert [item["id"] for item in everything["items"]] == expected, "newest first"
    assert (everything["total"], everything["limit"], everything["offset"]) == (4, 100, 0)
    assert {item["status"] for item in everything["items"]} == {"RISK_HELD", "READY"}
    assert transfer_row(pg_engine, due["id"]).status == "EXPIRED", "reconciled before listing"
    by_id = {item["id"]: item for item in everything["items"]}
    assert by_id[second["id"]]["status"] == "READY"
    assert by_id[second["id"]]["review_reason"] == APPROVAL
    assert by_id[an_hold["id"]]["sender_account_id"] == an.wallet_id
    assert by_id[first["id"]] == linh.get(first["id"])

    pages = [listed_holds(ops, limit=2, offset=offset) for offset in (0, 2, 4)]
    assert [[item["id"] for item in page["items"]] for page in pages] == [
        expected[:2],
        expected[2:],
        [],
    ]
    assert {page["total"] for page in pages} == {4}
    assert [item["id"] for item in listed_holds(other_ops)["items"]] == [other_hold["id"]]

    for params in ({"limit": 0}, {"limit": 101}, {"offset": -1}, {"limit": "x"}):
        invalid = ops.client.get(HOLDS, params=params)
        assert (invalid.status_code, error_code(invalid)) == (422, "VALIDATION_ERROR"), params
    for client, status, code in (
        (linh.client, 403, "FORBIDDEN"),
        (an.client, 403, "FORBIDDEN"),
        (browser(), 401, "SESSION_EXPIRED"),
        (with_controller(browser(), linh), 401, "SESSION_EXPIRED"),
    ):
        denied = client.get(HOLDS)
        assert (denied.status_code, error_code(denied)) == (status, code)
    for sandbox_id in (linh.sandbox_id, other.sandbox_id):
        assert_money_invariants(pg_engine, sandbox_id)


def test_customer_forged_role_cannot_review(browser, pg_engine: Engine):
    linh = open_sandbox(browser())
    held = linh.held("RISK_RECIPIENT", 20_000)
    forged = {
        "X-Role": "OPERATOR",
        "X-Actor-Role": "OPERATOR",
        "X-User-Role": "OPERATOR",
        "X-Actor-Id": linh.actor_id("Ops"),
        "X-Sandbox-Id": str(linh.sandbox_id),
    }
    for decision in ("APPROVE", "REJECT"):
        response = review(linh, held["id"], decision, headers={**writes(linh.csrf), **forged})
        assert (response.status_code, error_code(response)) == (403, "FORBIDDEN"), response.text
    listing = linh.client.get(HOLDS, headers=forged, params={"role": "OPERATOR"})
    assert (listing.status_code, error_code(listing)) == (403, "FORBIDDEN")

    ops = operator_in(browser(), linh)
    other = open_sandbox(browser())
    other_ops = operator_in(browser(), other)
    other_held = other.held("RISK_RECIPIENT", 20_000)
    controller_csrf = linh.bootstrap["controller_csrf_token"]
    approve = {"decision": "APPROVE", "reason": APPROVAL}
    denials = [
        (
            review(ops, held["id"], "APPROVE", headers={"X-CSRF-Token": ops.csrf}),
            403,
            "ORIGIN_DENIED",
        ),
        (
            review(
                ops,
                held["id"],
                "APPROVE",
                headers={"Origin": "https://evil.example", "X-CSRF-Token": ops.csrf},
            ),
            403,
            "ORIGIN_DENIED",
        ),
        (review(ops, held["id"], "APPROVE", headers=dict(ORIGIN)), 403, "CSRF_FAILED"),
        (review(ops, held["id"], "APPROVE", headers=writes(controller_csrf)), 403, "CSRF_FAILED"),
        (review(ops, held["id"], "APPROVE", headers=writes(linh.csrf)), 403, "CSRF_FAILED"),
        (
            browser().post(review_path(held["id"]), json=approve, headers=writes(ops.csrf)),
            401,
            "SESSION_EXPIRED",
        ),
        (
            with_controller(browser(), linh).post(
                review_path(held["id"]), json=approve, headers=writes(controller_csrf)
            ),
            401,
            "SESSION_EXPIRED",
        ),
        (review(other_ops, held["id"], "APPROVE"), 404, "NOT_FOUND"),
        (review(ops, other_held["id"], "REJECT"), 404, "NOT_FOUND"),
        (review(ops, str(uuid.uuid4()), "APPROVE"), 404, "NOT_FOUND"),
        (review(ops, "not-a-uuid", "APPROVE"), 422, "VALIDATION_ERROR"),
    ]
    for body in (
        {"decision": "SEND", "reason": APPROVAL},
        {"decision": "APPROVE"},
        {"decision": "APPROVE", "reason": ""},
        {"decision": "APPROVE", "reason": "x" * 4001},
        {"decision": "APPROVE", "reason": APPROVAL, "cleared_restriction_id": str(uuid.uuid4())},
        {"decision": "APPROVE", "reason": APPROVAL, "role": "OPERATOR"},
        [],
    ):
        denials.append((review(ops, held["id"], "APPROVE", body=body), 422, "VALIDATION_ERROR"))
    for response, status, code in denials:
        assert (response.status_code, error_code(response)) == (status, code), response.text

    for customer, transfer in ((linh, held), (other, other_held)):
        row = transfer_row(pg_engine, transfer["id"])
        assert (row.status, row.reserved_amount_vnd, row.reviewed_by) == ("RISK_HELD", 20_000, None)
        assert event_types(pg_engine, transfer["id"]) == ["TRANSFER_HELD"]
        assert money(customer.wallet()) == (10_000_000, 20_000, 9_980_000)
        assert_money_invariants(pg_engine, customer.sandbox_id)
    assert [item["id"] for item in listed_holds(other_ops)["items"]] == [other_held["id"]]


@pytest.mark.parametrize("case", ["held", "ready"])
def test_review_cancel_confirm_race(bounded_app: FastAPI, pg_engine: Engine, case: str):
    """Operator decisions and customer commands on one transfer converge to one outcome."""
    linh = open_sandbox(TestClient(bounded_app))
    ops = operator_in(TestClient(bounded_app), linh)
    bystander = linh.held("RISK_RECIPIENT", 30_000)
    target = linh.held("RISK_RECIPIENT", 20_000)
    if case == "ready":
        approved(ops, target["id"])
    approver, rejecter = same_actor(bounded_app, ops), same_actor(bounded_app, ops)
    confirmer, canceller = same_actor(bounded_app, linh), same_actor(bounded_app, linh)
    if case == "held":
        names = ["approve", "reject", "cancel"]
        contenders = [
            lambda: review(approver, target["id"], "APPROVE"),
            lambda: review(rejecter, target["id"], "REJECT"),
            lambda: canceller.cancel(target["id"]),
        ]
    else:
        names = ["confirm", "reject", "cancel"]
        contenders = [
            lambda: confirmer.confirm(target["id"]),
            lambda: review(rejecter, target["id"], "REJECT"),
            lambda: canceller.cancel(target["id"]),
        ]

    # Every contender queues on the sender account (reviews and the confirm first take the
    # recipient advisory lock, so one of them waits there instead).
    results = dict(
        zip(
            names,
            race(pg_engine, row_gate(pg_engine, "accounts", linh.wallet_id), contenders),
            strict=True,
        )
    )

    final = transfer_row(pg_engine, target["id"])
    winners = {name: r.json() for name, r in results.items() if r.status_code == 200}
    for name, response in results.items():
        if response.status_code != 200:
            current = state_conflict(response)
            assert current["status"] in {"READY", final.status}, (name, current)
    terminal = [
        event
        for event in event_types(pg_engine, target["id"])
        if event in {"TRANSFER_SUCCEEDED", "TRANSFER_CANCELED", "TRANSFER_REJECTED"}
    ]
    assert terminal == [f"TRANSFER_{final.status}"], "exactly one terminal outcome"
    if case == "held":
        assert final.status in {"CANCELED", "REJECTED"}
        assert ("reject" in winners) != ("cancel" in winners), [r.text for r in results.values()]
        if "approve" in winners:
            assert winners["approve"]["status"] == "READY"
            assert final.status == "CANCELED", "a READY transfer cannot be rejected"
        approvals = event_types(pg_engine, target["id"]).count("TRANSFER_APPROVED")
        assert approvals == (1 if "approve" in winners else 0)
        assert ledger_of(pg_engine, target["id"]) == []
    else:
        assert final.status in {"SUCCEEDED", "CANCELED"}
        assert "reject" not in winners, "a READY transfer cannot be rejected"
        assert ("confirm" in winners) != ("cancel" in winners), [r.text for r in results.values()]
        legs = ledger_of(pg_engine, target["id"])
        assert len(legs) == (2 if final.status == "SUCCEEDED" else 0)
    (winner,) = [body for body in winners.values() if body["status"] == final.status]
    assert winner["reserved_amount_vnd"] == 0
    posted = 10_000_000 - (20_000 if final.status == "SUCCEEDED" else 0)
    assert money(linh.wallet()) == (posted, 30_000, posted - 30_000), "released exactly once"
    assert ledger_of(pg_engine, bystander["id"]) == []
    assert_money_invariants(pg_engine, linh.sandbox_id)
    for browser_ in (approver, rejecter, confirmer, canceller):
        browser_.client.close()


def test_review_waits_for_recipient_policy_lock(bounded_app: FastAPI, pg_engine: Engine):
    """A review is ordered after a concurrent restriction change and holds no account lock
    while it waits for the recipient-policy lock (taken first, as by confirmation).
    """
    linh = open_sandbox(TestClient(bounded_app))
    ops = operator_in(TestClient(bounded_app), linh)
    held = linh.held("RISK_RECIPIENT", 20_000)
    other = linh.held("RISK_RECIPIENT", 30_000)
    original = restriction_of(held)
    recipient_id = uuid.UUID(held["recipient"]["id"])
    reviewer, canceller = same_actor(bounded_app, ops), same_actor(bounded_app, linh)
    replacement = uuid.uuid4()
    outcome: dict[str, Any] = {}

    def replace_decision_while_review_waits(gate: Connection) -> None:
        # As a restriction create/revoke would: change the decision under the advisory lock.
        gate.execute(
            update(models.RecipientRestriction)
            .where(models.RecipientRestriction.id == uuid.UUID(original))
            .values(
                status="REVOKED",
                revoked_by=uuid.UUID(linh.actor_id("Ops")),
                revoked_at=func.now(),
                revocation_reason="[Synthetic test] Replaced while a review waited.",
            )
        )
        gate.execute(
            insert(models.RecipientRestriction).values(
                id=replacement,
                sandbox_id=linh.sandbox_id,
                recipient_account_id=recipient_id,
                action="HOLD",
                reason="[Synthetic test] Replacement decision.",
                created_by=uuid.UUID(linh.actor_id("Ops")),
                expires_at=func.now() + timedelta(hours=1),
            )
        )
        outcome["cancel"] = canceller.cancel(other["id"])

    (response,) = race(
        pg_engine,
        advisory_gate(pg_engine, recipient_policy_key(linh.sandbox_id, recipient_id)),
        [lambda: review(reviewer, held["id"], "APPROVE")],
        before_release=replace_decision_while_review_waits,
    )

    assert outcome["cancel"].status_code == 200, "the waiting review holds no account lock"
    assert response.status_code == 200 and response.json()["status"] == "READY", response.text
    assert transfer_row(pg_engine, held["id"]).cleared_restriction_id == replacement
    assert money(linh.wallet()) == (10_000_000, 20_000, 9_980_000)
    assert_money_invariants(pg_engine, linh.sandbox_id)
    for browser_ in (reviewer, canceller):
        browser_.client.close()


def test_task8_hold_operations_match_contract(guardian_app):
    generated = TestClient(guardian_app).get("/openapi.json").json()["paths"]

    def parameters(operation: dict[str, Any]) -> dict[str, tuple[Any, ...]]:
        keys = ("type", "minimum", "maximum", "default")
        return {
            p["name"]: (p["in"], p.get("required", False), *(p["schema"].get(k) for k in keys))
            for p in operation.get("parameters", [])
        }

    for path, method, operation_id, model in (
        ("/ops/holds", "get", "listHolds", "TransferList"),
        ("/ops/transfers/{id}/review", "post", "reviewHold", "Transfer"),
    ):
        operation = generated[f"{API}{path}"][method]
        contract = OPENAPI["paths"][path][method]
        assert operation["operationId"] == contract["operationId"] == operation_id
        assert operation["tags"] == contract["tags"] == ["Operations"]
        assert operation["security"] == contract["security"] == [{"actorCookie": []}]
        assert parameters(operation) == parameters(contract), path
        success = operation["responses"]["200"]["content"]["application/json"]["schema"]
        assert success["$ref"] == f"#/components/schemas/{model}"
        assert ("requestBody" in operation) == ("requestBody" in contract), path
    body = generated[f"{API}/ops/transfers/{{id}}/review"]["post"]["requestBody"]
    assert body["required"] is True
    assert body["content"]["application/json"]["schema"]["$ref"] == (
        "#/components/schemas/ReviewHold"
    )
