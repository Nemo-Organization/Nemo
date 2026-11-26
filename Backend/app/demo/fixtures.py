"""Server-held synthetic fixtures for the three demo scenarios (docs/guardian/scenarios.md).

Every sandbox is seeded inside the caller's single transaction with fresh UUIDs; there is no
public fixture-write route. Times are offsets from the sandbox's database creation time, so the
history stays within the last 30 days. Helpers flush only; the top-level service commits.

Symbols are construction and test labels only. They never appear in API responses.

| Symbol | Persisted fixture |
| --- | --- |
| LINH, AN, BINH, MAI | CUSTOMER actors "Linh", "An", "Binh", "Mai", each with one NEMO wallet |
| OPS | OPERATOR actor "Ops"; no wallet |
| LINH_WALLET | DEMO-WALLET-0001; OPENING 11,500,000 less five history debits = 10,000,000 |
| AN_WALLET | DEMO-WALLET-0002; OPENING 5,000,000 less two history debits = 4,600,000 |
| BINH_WALLET, MAI_WALLET | DEMO-WALLET-0003/0004; OPENING 5,000,000 each, no history |
| CAFE | DEMOBANK DEMO-ACCT-1001 "Corner Cafe (synthetic)"; familiar, unrestricted |
| RISK_RECIPIENT | DEMOBANK DEMO-ACCT-6602; ACTIVE HOLD by OPS citing two RESOLVED reports |
| NEW_RECIPIENT | DEMOBANK DEMO-ACCT-3303; no history, no restriction |
| SHOP_REAL | FALSE_POSITIVE only: DEMOBANK DEMO-ACCT-4404 with a mistaken ACTIVE HOLD |
| SHOP_4502 | Linh's SHOP-4502: 500,000, fee 0 (NULL in INSUFFICIENT_EVIDENCE), APPROVED refund |
| AN_ORDER, BINH_ORDER, MAI_ORDER | SHOP-4518, SHOP-4521, SHOP-4533 with verified fee 0 |
| PARTNER_A, PARTNER_B | Synthetic refund-support partners |
| BATCH_A | Issued to PARTNER_A: A-017 (SHOP-4502), A-018 (An), A-019 (Binh); READ by PARTNER_A |
| BATCH_B | Issued to PARTNER_B: B-001 (Mai); READ by PARTNER_B only |

External recipients have no OPENING entry: their cached balance is exactly the credits received
from seeded history. Every cached balance is computed from the ledger rows written here.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app import models
from app.api.schemas import Scenario

DAY = timedelta(days=1)
OPENING_AGO = 14 * DAY
HISTORY_DRAFT_LIFETIME = timedelta(minutes=30)
HISTORY_SETTLE_DELAY = timedelta(seconds=20)

WALLET_BANK = "NEMO"
EXTERNAL_BANK = "DEMOBANK"
MERCHANT = "Nemo Demo Fashion (synthetic merchant)"
FEE_SOURCE = "Synthetic merchant fee confirmation"
INITIAL_ACTOR = "LINH"
FIXTURE_LABEL = "[Synthetic fixture]"
CORRECTION_LABEL = "[Synthetic test of correcting an earlier operational decision]"


@dataclass(frozen=True, slots=True)
class ActorSpec:
    role: str
    display_name: str


@dataclass(frozen=True, slots=True)
class AccountSpec:
    owner: str | None
    bank_code: str
    identifier: str
    display_name: str
    opening_vnd: int | None = None


@dataclass(frozen=True, slots=True)
class HistorySpec:
    sender: str
    recipient: str
    amount_vnd: int
    ago: timedelta


@dataclass(frozen=True, slots=True)
class OrderSpec:
    customer: str
    reference: str
    original_vnd: int
    return_fee_vnd: int
    fee_verified_ago: timedelta


@dataclass(frozen=True, slots=True)
class ReportSpec:
    reporter: str
    recipient: str
    narrative: str
    resolution_reason: str
    ago: timedelta


@dataclass(frozen=True, slots=True)
class RestrictionSpec:
    recipient: str
    action: str
    reason: str
    reports: tuple[str, ...]
    ago: timedelta


@dataclass(frozen=True, slots=True)
class BatchSpec:
    partner: str
    label: str
    issued_ago: timedelta


ACTORS: dict[str, ActorSpec] = {
    "LINH": ActorSpec("CUSTOMER", "Linh"),
    "AN": ActorSpec("CUSTOMER", "An"),
    "BINH": ActorSpec("CUSTOMER", "Binh"),
    "MAI": ActorSpec("CUSTOMER", "Mai"),
    "OPS": ActorSpec("OPERATOR", "Ops"),
}

ACCOUNTS: dict[str, AccountSpec] = {
    "LINH_WALLET": AccountSpec(
        "LINH", WALLET_BANK, "DEMO-WALLET-0001", "Linh demo wallet", 11_500_000
    ),
    "AN_WALLET": AccountSpec("AN", WALLET_BANK, "DEMO-WALLET-0002", "An demo wallet", 5_000_000),
    "BINH_WALLET": AccountSpec(
        "BINH", WALLET_BANK, "DEMO-WALLET-0003", "Binh demo wallet", 5_000_000
    ),
    "MAI_WALLET": AccountSpec("MAI", WALLET_BANK, "DEMO-WALLET-0004", "Mai demo wallet", 5_000_000),
    "CAFE": AccountSpec(None, EXTERNAL_BANK, "DEMO-ACCT-1001", "Corner Cafe (synthetic)"),
    "RISK_RECIPIENT": AccountSpec(
        None, EXTERNAL_BANK, "DEMO-ACCT-6602", "Fast Refund Support (synthetic)"
    ),
    "NEW_RECIPIENT": AccountSpec(None, EXTERNAL_BANK, "DEMO-ACCT-3303", "New Contact (synthetic)"),
}
SHOP_REAL = AccountSpec(
    None, EXTERNAL_BANK, "DEMO-ACCT-4404", "Real Shop Official Store (synthetic)"
)

# Linh: five settled outgoing transfers over the last ten days, median 300,000. An: two.
HISTORY: tuple[HistorySpec, ...] = (
    HistorySpec("LINH_WALLET", "CAFE", 100_000, 9 * DAY),
    HistorySpec("LINH_WALLET", "CAFE", 200_000, 7 * DAY),
    HistorySpec("LINH_WALLET", "CAFE", 300_000, 5 * DAY),
    HistorySpec("LINH_WALLET", "CAFE", 400_000, 3 * DAY),
    HistorySpec("LINH_WALLET", "CAFE", 500_000, 1 * DAY),
    HistorySpec("AN_WALLET", "CAFE", 150_000, 6 * DAY),
    HistorySpec("AN_WALLET", "CAFE", 250_000, 2 * DAY),
)

ORDERS: dict[str, OrderSpec] = {
    "SHOP_4502": OrderSpec("LINH", "SHOP-4502", 500_000, 0, 1 * DAY),
    "AN_ORDER": OrderSpec("AN", "SHOP-4518", 320_000, 0, 2 * DAY),
    "BINH_ORDER": OrderSpec("BINH", "SHOP-4521", 275_000, 0, 2 * DAY),
    "MAI_ORDER": OrderSpec("MAI", "SHOP-4533", 410_000, 0, 3 * DAY),
}
REFUND_ORDER = "SHOP_4502"
REFUND_ACCOUNT = "LINH_WALLET"
REFUND_VND = 500_000

PARTNERS: dict[str, str] = {
    "PARTNER_A": "Partner A Refund Support (synthetic)",
    "PARTNER_B": "Partner B Returns Desk (synthetic)",
}
BATCHES: dict[str, BatchSpec] = {
    "BATCH_A": BatchSpec("PARTNER_A", "Refund-support batch A (synthetic)", 7 * DAY),
    "BATCH_B": BatchSpec("PARTNER_B", "Refund-support batch B (synthetic)", 6 * DAY),
}
TRACE_REFERENCES: dict[str, tuple[str, str]] = {
    "A-017": ("BATCH_A", "SHOP_4502"),
    "A-018": ("BATCH_A", "AN_ORDER"),
    "A-019": ("BATCH_A", "BINH_ORDER"),
    "B-001": ("BATCH_B", "MAI_ORDER"),
}
# (partner, batch, action, ago): each READ is after issuance and before sandbox creation.
ACCESS_EVENTS: tuple[tuple[str, str, str, timedelta], ...] = (
    ("PARTNER_A", "BATCH_A", "READ", 5 * DAY),
    ("PARTNER_B", "BATCH_B", "READ", 4 * DAY),
)

NEAR_MISS_REPORTS: dict[str, ReportSpec] = {
    "RISK_REPORT_BINH": ReportSpec(
        "BINH",
        "RISK_RECIPIENT",
        f"{FIXTURE_LABEL} A chat message promised a faster order refund if I first paid a "
        "20,000 VND 'recovery fee' to this account. I checked with the shop and did not pay.",
        f"{FIXTURE_LABEL} Reviewed: near-miss report naming this account as payee for an "
        "advance refund fee. No money was sent.",
        4 * DAY,
    ),
    "RISK_REPORT_MAI": ReportSpec(
        "MAI",
        "RISK_RECIPIENT",
        f"{FIXTURE_LABEL} Someone claiming to be the warehouse asked me to advance a small "
        "return fee to this account before my refund could be released. I stopped and reported.",
        f"{FIXTURE_LABEL} Reviewed: independent near-miss report with the same payee and an "
        "advance-fee request. No money was sent.",
        3 * DAY,
    ),
}
RISK_RESTRICTION = RestrictionSpec(
    "RISK_RECIPIENT",
    "HOLD",
    f"{FIXTURE_LABEL} HOLD: two independently authored, reviewed near-miss reports name this "
    "account as the payee of an advance refund fee.",
    ("RISK_REPORT_BINH", "RISK_REPORT_MAI"),
    2 * DAY,
)
SHOP_REAL_REPORT = ReportSpec(
    "AN",
    "SHOP_REAL",
    f"{CORRECTION_LABEL} I received a forwarded screenshot asking for a fee that mentioned this "
    "shop's name. I did not receive it from the shop directly.",
    f"{CORRECTION_LABEL} Accepted at the time as recipient evidence; the image was forwarded and "
    "may not establish this shop as the requested receiver.",
    2 * DAY,
)
SHOP_REAL_RESTRICTION = RestrictionSpec(
    "SHOP_REAL",
    "HOLD",
    f"{CORRECTION_LABEL} Mistaken HOLD placed on the basis of one forwarded screenshot; "
    "kept to test correcting an earlier decision.",
    ("SHOP_REAL_REPORT",),
    1 * DAY,
)


@dataclass
class SeededSandbox:
    """In-memory handles to the rows just flushed, keyed by fixture symbol."""

    sandbox: models.Sandbox
    actors: dict[str, models.Actor] = field(default_factory=dict)
    accounts: dict[str, models.Account] = field(default_factory=dict)
    orders: dict[str, models.Order] = field(default_factory=dict)
    reports: dict[str, models.Report] = field(default_factory=dict)
    restrictions: dict[str, models.RecipientRestriction] = field(default_factory=dict)

    @property
    def id(self) -> UUID:
        return self.sandbox.id

    @property
    def created_at(self) -> datetime:
        return self.sandbox.created_at


def seed_sandbox(
    session: Session, scenario: Scenario, *, created_at: datetime, expires_at: datetime
) -> SeededSandbox:
    sandbox = models.Sandbox(
        id=uuid4(), scenario=scenario, created_at=created_at, expires_at=expires_at
    )
    session.add(sandbox)
    session.flush()
    seeded = SeededSandbox(sandbox)
    seed_actors_and_ledger(session, seeded, scenario)
    seed_orders(session, seeded, scenario)
    seed_recipient_decisions(session, seeded, scenario)
    seed_trace_records(session, seeded)
    return seeded


def scenario_accounts(scenario: Scenario) -> dict[str, AccountSpec]:
    if scenario == "FALSE_POSITIVE":
        return {**ACCOUNTS, "SHOP_REAL": SHOP_REAL}
    return dict(ACCOUNTS)


def seed_actors_and_ledger(session: Session, seeded: SeededSandbox, scenario: Scenario) -> None:
    sandbox_id, now = seeded.id, seeded.created_at
    for symbol, spec in ACTORS.items():
        seeded.actors[symbol] = models.Actor(
            id=uuid4(), sandbox_id=sandbox_id, role=spec.role, display_name=spec.display_name
        )
    session.add_all(seeded.actors.values())
    session.flush()

    specs = scenario_accounts(scenario)
    account_ids = {symbol: uuid4() for symbol in specs}
    opened_at = now - OPENING_AGO
    transfers: list[models.Transfer] = []
    entries: list[models.LedgerEntry] = []
    for symbol, spec in specs.items():
        if spec.opening_vnd:
            entries.append(
                models.LedgerEntry(
                    sandbox_id=sandbox_id,
                    account_id=account_ids[symbol],
                    kind="OPENING",
                    amount_vnd=spec.opening_vnd,
                    created_at=opened_at,
                )
            )
    for history in HISTORY:
        created = now - history.ago
        completed = created + HISTORY_SETTLE_DELAY
        transfer = models.Transfer(
            id=uuid4(),
            sandbox_id=sandbox_id,
            sender_account_id=account_ids[history.sender],
            recipient_account_id=account_ids[history.recipient],
            client_request_id=uuid4(),
            amount_vnd=history.amount_vnd,
            status="SUCCEEDED",
            reserved_amount_vnd=0,
            created_at=created,
            expires_at=created + HISTORY_DRAFT_LIFETIME,
            completed_at=completed,
        )
        transfers.append(transfer)
        for account, kind, amount in (
            (history.sender, "TRANSFER_DEBIT", -history.amount_vnd),
            (history.recipient, "TRANSFER_CREDIT", history.amount_vnd),
        ):
            entries.append(
                models.LedgerEntry(
                    sandbox_id=sandbox_id,
                    account_id=account_ids[account],
                    transfer_id=transfer.id,
                    kind=kind,
                    amount_vnd=amount,
                    created_at=completed,
                )
            )

    # Cached balances are derived from exactly the ledger rows written below.
    posted = dict.fromkeys(account_ids.values(), 0)
    for entry in entries:
        posted[entry.account_id] += entry.amount_vnd
    for symbol, spec in specs.items():
        seeded.accounts[symbol] = models.Account(
            id=account_ids[symbol],
            sandbox_id=sandbox_id,
            owner_actor_id=seeded.actors[spec.owner].id if spec.owner else None,
            bank_code=spec.bank_code,
            account_identifier=spec.identifier,
            display_name=spec.display_name,
            balance_vnd=posted[account_ids[symbol]],
            reserved_vnd=0,
            created_at=opened_at,
        )
    session.add_all(seeded.accounts.values())
    session.flush()
    session.add_all(transfers)
    session.flush()
    session.add_all(entries)
    session.flush()


def seed_orders(session: Session, seeded: SeededSandbox, scenario: Scenario) -> None:
    for symbol, spec in ORDERS.items():
        unknown_fee = scenario == "INSUFFICIENT_EVIDENCE" and symbol == REFUND_ORDER
        seeded.orders[symbol] = models.Order(
            id=uuid4(),
            sandbox_id=seeded.id,
            customer_actor_id=seeded.actors[spec.customer].id,
            order_reference=spec.reference,
            merchant_name=MERCHANT,
            original_amount_vnd=spec.original_vnd,
            return_fee_vnd=None if unknown_fee else spec.return_fee_vnd,
            fee_source=None if unknown_fee else FEE_SOURCE,
            fee_verified_at=None if unknown_fee else seeded.created_at - spec.fee_verified_ago,
        )
    session.add_all(seeded.orders.values())
    session.flush()
    session.add(
        models.Refund(
            id=uuid4(),
            sandbox_id=seeded.id,
            order_id=seeded.orders[REFUND_ORDER].id,
            account_id=seeded.accounts[REFUND_ACCOUNT].id,
            amount_vnd=REFUND_VND,
            status="APPROVED",
        )
    )
    session.flush()


def seed_recipient_decisions(session: Session, seeded: SeededSandbox, scenario: Scenario) -> None:
    reports = dict(NEAR_MISS_REPORTS)
    restrictions = {"RISK_RESTRICTION": RISK_RESTRICTION}
    if scenario == "FALSE_POSITIVE":
        reports["SHOP_REAL_REPORT"] = SHOP_REAL_REPORT
        restrictions["SHOP_REAL_RESTRICTION"] = SHOP_REAL_RESTRICTION
    ops = seeded.actors["OPS"]

    for symbol, spec in reports.items():
        seeded.reports[symbol] = models.Report(
            id=uuid4(),
            sandbox_id=seeded.id,
            reporter_actor_id=seeded.actors[spec.reporter].id,
            client_request_id=uuid4(),
            recipient_account_id=seeded.accounts[spec.recipient].id,
            narrative=spec.narrative,
            status="RESOLVED",
            reviewed_by=ops.id,
            resolution_reason=spec.resolution_reason,
            created_at=seeded.created_at - spec.ago,
        )
    session.add_all(seeded.reports.values())
    session.flush()

    for symbol, spec in restrictions.items():
        # Reviewed decisions never outlive the sandbox and stay effective for its whole life.
        seeded.restrictions[symbol] = models.RecipientRestriction(
            id=uuid4(),
            sandbox_id=seeded.id,
            recipient_account_id=seeded.accounts[spec.recipient].id,
            action=spec.action,
            status="ACTIVE",
            reason=spec.reason,
            created_by=ops.id,
            created_at=seeded.created_at - spec.ago,
            expires_at=seeded.sandbox.expires_at,
        )
    session.add_all(seeded.restrictions.values())
    session.flush()
    session.add_all(
        models.RestrictionReport(
            sandbox_id=seeded.id,
            restriction_id=seeded.restrictions[symbol].id,
            report_id=seeded.reports[report].id,
        )
        for symbol, spec in restrictions.items()
        for report in spec.reports
    )
    session.flush()


def seed_trace_records(session: Session, seeded: SeededSandbox) -> None:
    partners = {
        symbol: models.Partner(id=uuid4(), sandbox_id=seeded.id, name=name)
        for symbol, name in PARTNERS.items()
    }
    session.add_all(partners.values())
    session.flush()
    batches = {
        symbol: models.DataBatch(
            id=uuid4(),
            sandbox_id=seeded.id,
            partner_id=partners[spec.partner].id,
            label=spec.label,
            issued_at=seeded.created_at - spec.issued_ago,
        )
        for symbol, spec in BATCHES.items()
    }
    session.add_all(batches.values())
    session.flush()
    session.add_all(
        models.TraceReference(
            id=uuid4(),
            sandbox_id=seeded.id,
            batch_id=batches[batch].id,
            order_id=seeded.orders[order].id,
            code=code,
        )
        for code, (batch, order) in TRACE_REFERENCES.items()
    )
    session.add_all(
        models.PartnerAccessEvent(
            id=uuid4(),
            sandbox_id=seeded.id,
            partner_id=partners[partner].id,
            batch_id=batches[batch].id,
            action=action,
            occurred_at=seeded.created_at - ago,
        )
        for partner, batch, action, ago in ACCESS_EVENTS
    )
    session.flush()
