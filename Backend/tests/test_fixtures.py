"""Task 3: server-held scenario fixtures, seeded atomically through POST /demo/sessions.

Symbolic fixtures (docs/guardian/scenarios.md) are discovered from persisted relationships and
spec values, never from hard-coded IDs: CAFE is the recipient of Linh's history, RISK_RECIPIENT
is the account whose restriction cites two reports, and SHOP_REAL is the other restricted account.
"""

import uuid
from collections import Counter
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app import models
from tests.conftest import API, TEST_ORIGIN, start_demo

SCENARIOS = ["MAIN_REFUND", "FALSE_POSITIVE", "INSUFFICIENT_EVIDENCE"]
FEE_SOURCE = "Synthetic merchant fee confirmation"


class SandboxView:
    """Persisted rows of one sandbox, read after the bootstrap transaction committed."""

    def __init__(self, db: Session, sandbox_id: str):
        self.id = uuid.UUID(sandbox_id)
        self.db = db
        self.sandbox = db.get(models.Sandbox, self.id)
        self.actors = self.rows(models.Actor)
        self.accounts = self.rows(models.Account)
        self.transfers = self.rows(models.Transfer)
        self.ledger = self.rows(models.LedgerEntry)
        self.orders = self.rows(models.Order)
        self.refunds = self.rows(models.Refund)
        self.reports = self.rows(models.Report)
        self.restrictions = self.rows(models.RecipientRestriction)
        self.restriction_reports = self.rows(models.RestrictionReport)
        self.partners = self.rows(models.Partner)
        self.batches = self.rows(models.DataBatch)
        self.references = self.rows(models.TraceReference)
        self.access_events = self.rows(models.PartnerAccessEvent)

    def rows(self, model) -> list[Any]:
        return list(self.db.scalars(select(model).where(model.sandbox_id == self.id)))

    def actor(self, name: str) -> models.Actor:
        return next(actor for actor in self.actors if actor.display_name == name)

    def operator(self) -> models.Actor:
        (ops,) = [actor for actor in self.actors if actor.role == "OPERATOR"]
        return ops

    def wallet(self, name: str) -> models.Account:
        (wallet,) = [a for a in self.accounts if a.owner_actor_id == self.actor(name).id]
        return wallet

    def outgoing(self, name: str) -> list[models.Transfer]:
        wallet = self.wallet(name)
        return [t for t in self.transfers if t.sender_account_id == wallet.id]

    def cafe(self) -> models.Account:
        (recipient,) = {t.recipient_account_id for t in self.outgoing("Linh")}
        return self.db.get(models.Account, recipient)

    def evidence(self, restriction: models.RecipientRestriction) -> list[models.Report]:
        ids = {
            link.report_id
            for link in self.restriction_reports
            if link.restriction_id == restriction.id
        }
        return [report for report in self.reports if report.id in ids]

    def risk_restriction(self) -> models.RecipientRestriction:
        (restriction,) = [r for r in self.restrictions if len(self.evidence(r)) == 2]
        return restriction

    def order(self, reference: str) -> models.Order:
        return next(order for order in self.orders if order.order_reference == reference)


@pytest.fixture
def seeded(browser, pg_engine: Engine):
    sessions: list[Session] = []

    def create(scenario: str = "MAIN_REFUND") -> SandboxView:
        bootstrap = start_demo(browser(), scenario)
        db = Session(pg_engine)
        sessions.append(db)
        return SandboxView(db, bootstrap["sandbox_id"])

    yield create
    for db in sessions:
        db.close()


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_every_cached_balance_equals_ledger_sum(seeded, scenario):
    view = seeded(scenario)

    sums = Counter()
    for entry in view.ledger:
        sums[entry.account_id] += entry.amount_vnd
    for account in view.accounts:
        assert account.balance_vnd == sums[account.id], account.display_name
        assert account.reserved_vnd == 0
    for transfer in view.transfers:
        assert transfer.status == "SUCCEEDED" and transfer.reserved_amount_vnd == 0
        legs = sorted(e.kind for e in view.ledger if e.transfer_id == transfer.id)
        assert legs == ["TRANSFER_CREDIT", "TRANSFER_DEBIT"]
    assert view.wallet("Linh").balance_vnd == 10_000_000
    for name in ("An", "Binh", "Mai"):
        assert view.wallet(name).balance_vnd >= 1_000_000, "sufficient opening funds"
    openings = [e for e in view.ledger if e.kind == "OPENING"]
    assert {e.account_id for e in openings} == {
        view.wallet(n).id for n in ("Linh", "An", "Binh", "Mai")
    }
    assert [e.amount_vnd for e in openings if e.account_id == view.wallet("Linh").id] == [
        11_500_000
    ]


def test_actors_wallets_and_external_recipients(seeded):
    view = seeded()

    customers = sorted(a.display_name for a in view.actors if a.role == "CUSTOMER")
    assert customers == ["An", "Binh", "Linh", "Mai"]
    ops = view.operator()
    assert not [a for a in view.accounts if a.owner_actor_id == ops.id], "Ops has no wallet"
    wallets = {view.wallet(name).id for name in customers}
    assert len(wallets) == 4
    external = [a for a in view.accounts if a.owner_actor_id is None]
    assert len(external) == 3, "CAFE, RISK_RECIPIENT and NEW_RECIPIENT"
    cafe = view.cafe()
    risk = view.db.get(models.Account, view.risk_restriction().recipient_account_id)
    (new_recipient,) = [a for a in external if a.id not in {cafe.id, risk.id}]
    restricted = {r.recipient_account_id for r in view.restrictions}
    assert cafe.id not in restricted and new_recipient.id not in restricted
    assert not [t for t in view.transfers if t.recipient_account_id == new_recipient.id]
    identities = [(a.bank_code, a.account_identifier) for a in view.accounts]
    assert len(set(identities)) == len(identities)
    for account in view.accounts:
        assert "synthetic" in account.display_name.lower() or account.owner_actor_id


def test_an_has_exactly_two_settled_history_transfers(seeded):
    view = seeded()
    created = view.sandbox.created_at

    an_history = view.outgoing("An")
    assert len(an_history) == 2
    assert {t.status for t in an_history} == {"SUCCEEDED"}
    assert view.outgoing("Binh") == [] and view.outgoing("Mai") == []
    linh = view.outgoing("Linh")
    assert sorted(t.amount_vnd for t in linh) == [100_000, 200_000, 300_000, 400_000, 500_000]
    for transfer in linh + an_history:
        assert created - timedelta(days=10) <= transfer.created_at < created
        assert transfer.created_at <= transfer.completed_at < created
        assert transfer.recipient_account_id == view.cafe().id


def test_risk_restriction_cites_two_resolved_reports(seeded):
    view = seeded()
    ops = view.operator()

    restriction = view.risk_restriction()
    assert (restriction.action, restriction.status) == ("HOLD", "ACTIVE")
    assert restriction.created_by == ops.id
    assert restriction.revoked_at is None and restriction.revocation_reason is None
    assert view.sandbox.created_at < restriction.expires_at <= view.sandbox.expires_at
    assert restriction.created_at < view.sandbox.created_at
    reports = view.evidence(restriction)
    assert len({report.reporter_actor_id for report in reports}) == 2
    customers = {a.id for a in view.actors if a.role == "CUSTOMER"}
    linh = view.actor("Linh").id
    for report in reports:
        assert report.status == "RESOLVED"
        assert report.reviewed_by == ops.id and report.resolution_reason
        assert report.recipient_account_id == restriction.recipient_account_id
        assert report.reporter_actor_id in customers and report.reporter_actor_id != linh
        assert report.transfer_id is None, "near misses: no earlier customer lost money"
        assert report.created_at < restriction.created_at
        assert "synthetic" in report.narrative.lower()
    assert len(view.restrictions) == 1


def test_trace_references_map_to_batches_and_orders(seeded):
    view = seeded()
    partners = {partner.id: partner for partner in view.partners}
    batches = {batch.id: batch for batch in view.batches}
    orders = {order.id: order for order in view.orders}
    owners = {actor.id: actor.display_name for actor in view.actors}

    mapping = {
        ref.code: (batches[ref.batch_id], owners[orders[ref.order_id].customer_actor_id])
        for ref in view.references
    }
    assert set(mapping) == {"A-017", "A-018", "A-019", "B-001"}
    assert {code: owner for code, (_, owner) in mapping.items()} == {
        "A-017": "Linh",
        "A-018": "An",
        "A-019": "Binh",
        "B-001": "Mai",
    }
    batch_a = mapping["A-017"][0]
    batch_b = mapping["B-001"][0]
    assert batch_a.id != batch_b.id and batch_a.partner_id != batch_b.partner_id
    assert {mapping[code][0].id for code in ("A-017", "A-018", "A-019")} == {batch_a.id}
    linh_ref = next(ref for ref in view.references if ref.code == "A-017")
    assert orders[linh_ref.order_id].order_reference == "SHOP-4502"
    assert len(partners) == 2 and len(batches) == 2

    events = {(e.partner_id, e.batch_id, e.action): e for e in view.access_events}
    assert set(events) == {
        (batch_a.partner_id, batch_a.id, "READ"),
        (batch_b.partner_id, batch_b.id, "READ"),
    }, "PARTNER_A reads BATCH_A; PARTNER_B reads only BATCH_B"
    for batch in (batch_a, batch_b):
        event = events[(batch.partner_id, batch.id, "READ")]
        assert batch.issued_at < event.occurred_at < view.sandbox.created_at
    for row in [*view.partners, *view.batches]:
        label = row.name if isinstance(row, models.Partner) else row.label
        assert "synthetic" in label.lower()


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_refund_and_fee_fixtures_by_scenario(seeded, scenario):
    view = seeded(scenario)

    owners = Counter(
        view.db.get(models.Actor, o.customer_actor_id).display_name for o in view.orders
    )
    assert owners == {"Linh": 1, "An": 1, "Binh": 1, "Mai": 1}
    shop = view.order("SHOP-4502")
    assert shop.customer_actor_id == view.actor("Linh").id
    assert shop.original_amount_vnd == 500_000
    (refund,) = view.refunds
    assert (refund.order_id, refund.account_id) == (shop.id, view.wallet("Linh").id)
    assert (refund.amount_vnd, refund.status, refund.settled_at) == (500_000, "APPROVED", None)

    if scenario == "INSUFFICIENT_EVIDENCE":
        assert (shop.return_fee_vnd, shop.fee_source, shop.fee_verified_at) == (None, None, None)
    else:
        assert (shop.return_fee_vnd, shop.fee_source) == (0, FEE_SOURCE)
        assert shop.fee_verified_at < view.sandbox.created_at
    for order in view.orders:
        if order.id != shop.id:
            assert order.return_fee_vnd is not None and order.fee_source and order.fee_verified_at


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_shop_real_mistaken_hold_only_in_false_positive(seeded, scenario):
    view = seeded(scenario)
    risk = view.risk_restriction()
    others = [r for r in view.restrictions if r.id != risk.id]
    external = [a for a in view.accounts if a.owner_actor_id is None]

    if scenario != "FALSE_POSITIVE":
        assert others == [] and len(external) == 3
        return
    assert len(external) == 4
    (mistaken,) = others
    assert (mistaken.action, mistaken.status) == ("HOLD", "ACTIVE")
    assert mistaken.created_by == view.operator().id
    assert "correct" in mistaken.reason.lower() and "earlier" in mistaken.reason.lower()
    assert view.sandbox.created_at < mistaken.expires_at <= view.sandbox.expires_at
    shop_real = view.db.get(models.Account, mistaken.recipient_account_id)
    assert shop_real.owner_actor_id is None and shop_real.id != risk.recipient_account_id
    evidence = view.evidence(mistaken)
    assert evidence and all(
        r.status == "RESOLVED" and r.recipient_account_id == shop_real.id for r in evidence
    )


def test_each_sandbox_gets_fresh_ids(seeded):
    first, second = seeded(), seeded()

    for attribute in ("actors", "accounts", "transfers", "orders", "reports", "references"):
        ids_a = {row.id for row in getattr(first, attribute)}
        ids_b = {row.id for row in getattr(second, attribute)}
        assert ids_a and not ids_a & ids_b, attribute


def test_failed_seed_leaves_no_partial_sandbox(guardian_app, pg_engine: Engine, monkeypatch):
    def counts() -> tuple[int, ...]:
        with Session(pg_engine) as db:
            return tuple(
                db.scalar(select(func.count()).select_from(model))
                for model in (models.Sandbox, models.Actor, models.Account, models.LedgerEntry)
            )

    client = TestClient(guardian_app, raise_server_exceptions=False)
    start_demo(client)
    before = counts()

    def fail(*_args, **_kwargs):
        raise RuntimeError("simulated failure after earlier fixture rows were flushed")

    monkeypatch.setattr("app.demo.fixtures.seed_trace_records", fail)
    response = client.post(
        f"{API}/demo/sessions", json={"scenario": "MAIN_REFUND"}, headers={"Origin": TEST_ORIGIN}
    )

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "set-cookie" not in {name.lower() for name, _ in response.headers.multi_items()}
    assert counts() == before
