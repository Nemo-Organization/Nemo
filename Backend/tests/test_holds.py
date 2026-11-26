"""Task 7: holds reserve once, cancellation releases once, and deadlines are reconciled.

Rulings encoded here: confirming a transfer that a current recipient HOLD covers reserves its
amount once and sets RISK_HELD, held_at and a deadline exactly 15 minutes later in database time;
repeating that confirmation returns the hold unchanged. Cancel of DRAFT/RISK_HELD/READY releases
the transfer's own reservation once and returns CANCELED; repeating it returns the same result;
cancel after another terminal state is 409 STATE_CONFLICT with the current transfer. A DRAFT,
RISK_HELD or READY transfer past its deadline becomes EXPIRED, releasing its reservation once,
before /me, actor selection, transfer reads (including a draft replay), assessment, confirmation
or cancellation use it. Those reconciliations are committed even when the command then answers
409, and are audited as SYSTEM TRANSFER_EXPIRED events carrying the triggering request ID.
"""

from datetime import timedelta

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.transfers.expiry import expire_due_transfers
from tests.money_support import (
    HOLD_LIFETIME,
    ME,
    TRANSFERS,
    account_row,
    as_actor,
    assert_money_invariants,
    assert_sanitized,
    assessment_count,
    audit_of,
    db_clock,
    error_code,
    error_of,
    instant,
    ledger_of,
    money,
    open_sandbox,
    pass_deadline,
    transfer_row,
    writes,
)


def test_hold_reserves_once(browser, pg_engine: Engine):
    linh = open_sandbox(browser())
    normal = linh.confirm(linh.draft("CAFE", 20_000)["id"])
    assert normal.json()["status"] == "SUCCEEDED", normal.text
    assert money(linh.wallet()) == (9_980_000, 0, 9_980_000)

    risky = linh.draft("RISK_RECIPIENT", 20_000)
    assessed = linh.assess(risky["id"]).json()
    assert assessed["decision"] == "HOLD"
    seeded_restriction = assessed["reasons"][0]["restriction_id"]

    before = db_clock(pg_engine)
    held = linh.confirm(risky["id"])
    after = db_clock(pg_engine)

    assert held.status_code == 200, held.text
    body = held.json()
    assert (body["status"], body["reserved_amount_vnd"], body["completed_at"]) == (
        "RISK_HELD",
        20_000,
        None,
    )
    assert body["assessment"]["decision"] == "HOLD"
    assert body["assessment"]["reasons"][0]["restriction_id"] == seeded_restriction
    row = transfer_row(pg_engine, risky["id"])
    assert row.held_at is not None and before <= row.held_at <= after, "database time"
    assert row.expires_at - row.held_at == HOLD_LIFETIME
    assert instant(body["expires_at"]) == row.expires_at
    assert money(linh.wallet()) == (9_980_000, 20_000, 9_960_000)
    assert ledger_of(pg_engine, risky["id"]) == [], "a hold posts no debit"
    (event,) = audit_of(pg_engine, risky["id"])
    assert (event.event_type, event.actor_kind, event.request_id) == (
        "TRANSFER_HELD",
        "CUSTOMER",
        held.headers["x-request-id"],
    )
    assert (event.details["reserved_vnd"], event.details["restriction_id"]) == (
        20_000,
        seeded_restriction,
    )
    assert_sanitized(event, linh.csrf)

    # Repeating confirmation returns the hold: no second reservation or deadline extension.
    assessments = assessment_count(pg_engine, linh.sandbox_id)
    for ack in (None, assessed["id"], body["assessment"]["id"]):
        again = linh.confirm(risky["id"], ack)
        assert again.status_code == 200, again.text
        assert again.json() == body
    repeated = transfer_row(pg_engine, risky["id"])
    assert (repeated.held_at, repeated.expires_at, repeated.reserved_amount_vnd) == (
        row.held_at,
        row.expires_at,
        20_000,
    )
    assert assessment_count(pg_engine, linh.sandbox_id) == assessments
    assert len(audit_of(pg_engine, risky["id"])) == 1
    assert money(linh.wallet()) == (9_980_000, 20_000, 9_960_000)
    assert linh.get(risky["id"]) == body
    assert_money_invariants(pg_engine, linh.sandbox_id)


def test_cancel_releases_once(browser, pg_engine: Engine):
    linh = open_sandbox(browser())
    assert linh.confirm(linh.draft("CAFE", 20_000)["id"]).json()["status"] == "SUCCEEDED"
    first = linh.held("RISK_RECIPIENT", 20_000)
    second = linh.held("RISK_RECIPIENT", 30_000)
    assert money(linh.wallet()) == (9_980_000, 50_000, 9_930_000)

    before = db_clock(pg_engine)
    canceled = linh.cancel(first["id"])
    after = db_clock(pg_engine)

    assert canceled.status_code == 200, canceled.text
    body = canceled.json()
    assert (body["status"], body["reserved_amount_vnd"]) == ("CANCELED", 0)
    assert before <= instant(body["completed_at"]) <= after
    assert money(linh.wallet()) == (9_980_000, 30_000, 9_950_000), "only its own amount"
    for _ in range(2):
        again = linh.cancel(first["id"])
        assert again.status_code == 200 and again.json() == body
    assert money(linh.wallet()) == (9_980_000, 30_000, 9_950_000), "released once"
    (event,) = audit_of(pg_engine, first["id"], "TRANSFER_CANCELED")
    assert (event.actor_kind, event.request_id) == ("CUSTOMER", canceled.headers["x-request-id"])
    assert (event.details["from_status"], event.details["released_vnd"]) == ("RISK_HELD", 20_000)
    assert_sanitized(event, linh.csrf)

    late_confirm = linh.confirm(first["id"])
    assert (late_confirm.status_code, error_code(late_confirm)) == (409, "STATE_CONFLICT")
    assert error_of(late_confirm)["current_transfer"] == body
    assert ledger_of(pg_engine, first["id"]) == []

    # Walkthrough step 4: cancelling the remaining hold leaves reserved 0, available 9,980,000.
    assert linh.cancel(second["id"]).json()["status"] == "CANCELED"
    assert money(linh.wallet()) == (9_980_000, 0, 9_980_000)

    draft = linh.draft("CAFE", 10_000)
    canceled_draft = linh.cancel(draft["id"])
    assert canceled_draft.status_code == 200, canceled_draft.text
    assert canceled_draft.json()["status"] == "CANCELED"
    assert money(linh.wallet()) == (9_980_000, 0, 9_980_000), "a draft reserved nothing"
    (draft_event,) = audit_of(pg_engine, draft["id"])
    assert (draft_event.details["from_status"], draft_event.details["released_vnd"]) == (
        "DRAFT",
        0,
    )
    refused = linh.confirm(draft["id"])
    assert (refused.status_code, error_code(refused)) == (409, "STATE_CONFLICT")
    assert error_of(refused)["current_transfer"]["status"] == "CANCELED"
    assert_money_invariants(pg_engine, linh.sandbox_id)


def test_expiry_reconciled_on_me_and_commands(browser, pg_engine: Engine):
    linh = open_sandbox(browser())
    first = linh.held("RISK_RECIPIENT", 20_000)
    second = linh.held("RISK_RECIPIENT", 30_000)
    assert money(linh.wallet()) == (10_000_000, 50_000, 9_950_000)

    # /me: the stored reservation is past its deadline and is released before display.
    pass_deadline(pg_engine, first["id"])
    assert account_row(pg_engine, linh.wallet_id).reserved_vnd == 50_000, "still stored"
    before = db_clock(pg_engine)
    me = linh.client.get(ME)
    after = db_clock(pg_engine)
    assert me.status_code == 200, me.text
    assert money(me.json()["accounts"][0]) == (10_000_000, 30_000, 9_970_000)
    row = transfer_row(pg_engine, first["id"])
    assert (row.status, row.reserved_amount_vnd) == ("EXPIRED", 0)
    assert row.completed_at is not None and before <= row.completed_at <= after
    (event,) = audit_of(pg_engine, first["id"], "TRANSFER_EXPIRED")
    assert (event.actor_kind, event.actor_id, event.request_id) == (
        "SYSTEM",
        None,
        me.headers["x-request-id"],
    )
    assert (event.details["from_status"], event.details["released_vnd"]) == ("RISK_HELD", 20_000)
    assert_sanitized(event, linh.csrf)
    assert money(linh.wallet()) == (10_000_000, 30_000, 9_970_000)
    assert linh.get(first["id"])["status"] == "EXPIRED"
    assert len(audit_of(pg_engine, first["id"], "TRANSFER_EXPIRED")) == 1, "expires once"
    for response in (linh.confirm(first["id"]), linh.cancel(first["id"])):
        assert (response.status_code, error_code(response)) == (409, "STATE_CONFLICT")
        assert error_of(response)["current_transfer"]["status"] == "EXPIRED"

    # A single transfer read and the list read reconcile before projecting.
    pass_deadline(pg_engine, second["id"])
    fetched = linh.get(second["id"])
    assert (fetched["status"], fetched["reserved_amount_vnd"]) == ("EXPIRED", 0)
    assert account_row(pg_engine, linh.wallet_id).reserved_vnd == 0
    listed_draft = linh.draft("CAFE", 10_000)
    pass_deadline(pg_engine, listed_draft["id"])
    items = linh.client.get(TRANSFERS, params={"limit": 100}).json()["items"]
    assert next(i for i in items if i["id"] == listed_draft["id"])["status"] == "EXPIRED"

    # Confirming a draft past its deadline: the committed expiry wins over execution.
    late = linh.draft("CAFE", 20_000)
    pass_deadline(pg_engine, late["id"])
    assessments = assessment_count(pg_engine, linh.sandbox_id)
    refused = linh.confirm(late["id"])
    assert (refused.status_code, error_code(refused)) == (409, "STATE_CONFLICT")
    assert error_of(refused)["current_transfer"]["status"] == "EXPIRED"
    assert transfer_row(pg_engine, late["id"]).status == "EXPIRED", "committed before the 409"
    assert ledger_of(pg_engine, late["id"]) == []
    assert assessment_count(pg_engine, linh.sandbox_id) == assessments

    # A stored reservation after its deadline never authorizes anything; cancel sees EXPIRED.
    stale_hold = linh.held("RISK_RECIPIENT", 40_000)
    pass_deadline(pg_engine, stale_hold["id"])
    stale_cancel = linh.cancel(stale_hold["id"])
    assert (stale_cancel.status_code, error_code(stale_cancel)) == (409, "STATE_CONFLICT")
    assert error_of(stale_cancel)["current_transfer"]["status"] == "EXPIRED"
    assert account_row(pg_engine, linh.wallet_id).reserved_vnd == 0

    # Assessment of a transfer past its deadline reconciles it first.
    unassessed = linh.draft("NEW_RECIPIENT", 20_000)
    pass_deadline(pg_engine, unassessed["id"])
    conflict = linh.assess(unassessed["id"])
    assert (conflict.status_code, error_code(conflict)) == (409, "STATE_CONFLICT")
    assert error_of(conflict)["current_transfer"] == linh.get(unassessed["id"])
    assert error_of(conflict)["current_transfer"]["status"] == "EXPIRED"

    # A command reconciles the caller's other due rows before it reads available funds.
    due_hold = linh.held("RISK_RECIPIENT", 20_000)
    pass_deadline(pg_engine, due_hold["id"])
    payment = linh.confirm(linh.draft("CAFE", 20_000)["id"])
    assert payment.json()["status"] == "SUCCEEDED", payment.text
    (swept,) = audit_of(pg_engine, due_hold["id"], "TRANSFER_EXPIRED")
    assert swept.request_id == payment.headers["x-request-id"]

    # Replaying the original draft request of a hold past its deadline shows it expired.
    replayed_hold = linh.held("RISK_RECIPIENT", 20_000)
    pass_deadline(pg_engine, replayed_hold["id"])
    replay = linh.client.post(
        TRANSFERS,
        json={
            "client_request_id": str(
                transfer_row(pg_engine, replayed_hold["id"]).client_request_id
            ),
            "sender_account_id": linh.wallet_id,
            "recipient_account_id": replayed_hold["recipient"]["id"],
            "amount_vnd": 20_000,
        },
        headers=writes(linh.csrf),
    )
    assert replay.status_code == 200, replay.text
    assert (replay.json()["status"], replay.json()["reserved_amount_vnd"]) == ("EXPIRED", 0)
    assert replay.json()["replayed"] is True
    assert account_row(pg_engine, linh.wallet_id).reserved_vnd == 0

    # Actor selection returns a reconciled Me.
    selected_hold = linh.held("RISK_RECIPIENT", 20_000)
    pass_deadline(pg_engine, selected_hold["id"])
    reselected = as_actor(linh, "Linh")
    assert transfer_row(pg_engine, selected_hold["id"]).status == "EXPIRED"
    assert money(reselected.wallet()) == (9_980_000, 0, 9_980_000)
    assert_money_invariants(pg_engine, linh.sandbox_id)


def test_expiry_sweep_is_scoped_and_idempotent(browser, pg_engine: Engine):
    linh = open_sandbox(browser())
    other = open_sandbox(browser())
    mine = linh.held("RISK_RECIPIENT", 20_000)
    theirs = other.held("RISK_RECIPIENT", 20_000)
    live = linh.held("RISK_RECIPIENT", 30_000)
    for transfer_id in (mine["id"], theirs["id"]):
        pass_deadline(pg_engine, transfer_id)

    with Session(pg_engine) as db:
        assert expire_due_transfers(db, linh.sandbox_id) == 1
        assert expire_due_transfers(db, linh.sandbox_id) == 0, "a second sweep converges"
    assert transfer_row(pg_engine, mine["id"]).status == "EXPIRED"
    assert transfer_row(pg_engine, live["id"]).status == "RISK_HELD"
    assert transfer_row(pg_engine, theirs["id"]).status == "RISK_HELD", "other sandbox untouched"
    assert account_row(pg_engine, linh.wallet_id).reserved_vnd == 30_000
    held_event, expired_event = audit_of(pg_engine, mine["id"])
    assert held_event.event_type == "TRANSFER_HELD"
    assert (expired_event.event_type, expired_event.actor_kind, expired_event.actor_id) == (
        "TRANSFER_EXPIRED",
        "SYSTEM",
        None,
    )
    assert expired_event.request_id.startswith("maintenance-")
    assert expired_event.details["released_vnd"] == 20_000

    with Session(pg_engine) as db:
        assert expire_due_transfers(db, None) >= 1
    assert transfer_row(pg_engine, theirs["id"]).status == "EXPIRED"
    assert account_row(pg_engine, other.wallet_id).reserved_vnd == 0
    assert transfer_row(pg_engine, live["id"]).expires_at - transfer_row(
        pg_engine, live["id"]
    ).held_at == timedelta(minutes=15)
    for sandbox_id in (linh.sandbox_id, other.sandbox_id):
        assert_money_invariants(pg_engine, sandbox_id)
