"""Shared HTTP and SQL helpers for the Task 7 money tests. Not a test module.

Fixture IDs are discovered through the API. Persisted state is read through the disposable
PostgreSQL engine, and `assert_money_invariants` checks the cached money aggregates in SQL.
"""

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select, text, update
from sqlalchemy.orm import Session

from app import models
from app.demo import fixtures
from tests.conftest import API, TEST_ORIGIN, start_demo

ORIGIN = {"Origin": TEST_ORIGIN}
ME = f"{API}/me"
RECIPIENTS = f"{API}/recipients"
TRANSFERS = f"{API}/transfers"
HOLD_LIFETIME = timedelta(minutes=15)
TERMINAL_EVENTS = ("TRANSFER_SUCCEEDED", "TRANSFER_CANCELED", "TRANSFER_EXPIRED")
SECRET_MARKERS = ("token", "csrf", "cookie", "secret", "password")


def writes(csrf: str) -> dict[str, str]:
    return {**ORIGIN, "X-CSRF-Token": csrf}


def error_of(response) -> dict[str, Any]:
    return response.json()["error"]


def error_code(response) -> str:
    return error_of(response)["code"]


def instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    assert parsed.utcoffset() == timedelta(0), value
    return parsed


@dataclass
class Customer:
    """One browser acting as the selected customer of one sandbox."""

    client: TestClient
    bootstrap: dict[str, Any]
    csrf: str
    wallet_id: str

    @property
    def sandbox_id(self) -> uuid.UUID:
        return uuid.UUID(self.bootstrap["sandbox_id"])

    def actor_id(self, name: str) -> str:
        return next(a["id"] for a in self.bootstrap["actors"] if a["display_name"] == name)

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

    def assess(self, transfer_id: str):
        return self.client.post(f"{TRANSFERS}/{transfer_id}/assess", headers=writes(self.csrf))

    def confirm(
        self,
        transfer_id: str,
        ack: str | None = None,
        *,
        body: Any = None,
        headers: dict[str, str] | None = None,
    ):
        payload = (
            body
            if body is not None
            else ({} if ack is None else {"acknowledged_assessment_id": ack})
        )
        return self.client.post(
            f"{TRANSFERS}/{transfer_id}/confirm",
            json=payload,
            headers=writes(self.csrf) if headers is None else headers,
        )

    def cancel(self, transfer_id: str, *, headers: dict[str, str] | None = None):
        return self.client.post(
            f"{TRANSFERS}/{transfer_id}/cancel",
            headers=writes(self.csrf) if headers is None else headers,
        )

    def get(self, transfer_id: str) -> dict[str, Any]:
        response = self.client.get(f"{TRANSFERS}/{transfer_id}")
        assert response.status_code == 200, response.text
        return response.json()

    def wallet(self) -> dict[str, Any]:
        response = self.client.get(ME)
        assert response.status_code == 200, response.text
        (account,) = response.json()["accounts"]
        return account

    def held(self, symbol: str, amount: int) -> dict[str, Any]:
        """A confirmed draft that the current restriction holds."""
        response = self.confirm(self.draft(symbol, amount)["id"])
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "RISK_HELD", response.text
        return response.json()


def open_sandbox(client: TestClient, scenario: str = "MAIN_REFUND") -> Customer:
    """Start a sandbox in `client`; the initial actor is Linh."""
    bootstrap = start_demo(client, scenario)
    (wallet,) = client.get(ME).json()["accounts"]
    return Customer(client, bootstrap, bootstrap["actor_csrf_token"], wallet["id"])


def as_actor(customer: Customer, name: str) -> Customer:
    response = customer.client.post(
        f"{API}/demo/actors/select",
        json={"actor_id": customer.actor_id(name)},
        headers=writes(customer.bootstrap["controller_csrf_token"]),
    )
    assert response.status_code == 200, response.text
    me = response.json()
    wallet_id = me["accounts"][0]["id"] if me["accounts"] else ""
    return Customer(customer.client, customer.bootstrap, me["actor_csrf_token"], wallet_id)


def money(account: dict[str, Any]) -> tuple[int, int, int]:
    """(posted balance, reserved, available) of an Account DTO."""
    return account["balance_vnd"], account["reserved_vnd"], account["available_vnd"]


def db_clock(pg_engine: Engine) -> datetime:
    with pg_engine.connect() as connection:
        return connection.execute(select(func.clock_timestamp())).scalar_one()


def transfer_row(pg_engine: Engine, transfer_id: str) -> models.Transfer:
    with Session(pg_engine) as db:
        row = db.get(models.Transfer, uuid.UUID(transfer_id))
        assert row is not None
        return row


def account_row(pg_engine: Engine, account_id: str) -> models.Account:
    with Session(pg_engine) as db:
        row = db.get(models.Account, uuid.UUID(account_id))
        assert row is not None
        return row


def ledger_of(pg_engine: Engine, transfer_id: str) -> list[tuple[str, str, int]]:
    with Session(pg_engine) as db:
        rows = db.scalars(
            select(models.LedgerEntry).where(
                models.LedgerEntry.transfer_id == uuid.UUID(transfer_id)
            )
        ).all()
        return sorted((str(r.account_id), r.kind, r.amount_vnd) for r in rows)


def ledger_count(pg_engine: Engine, sandbox_id: uuid.UUID) -> int:
    with Session(pg_engine) as db:
        return db.scalar(
            select(func.count())
            .select_from(models.LedgerEntry)
            .where(models.LedgerEntry.sandbox_id == sandbox_id)
        )


def assessment_count(pg_engine: Engine, sandbox_id: uuid.UUID) -> int:
    with Session(pg_engine) as db:
        return db.scalar(
            select(func.count())
            .select_from(models.RiskAssessment)
            .where(models.RiskAssessment.sandbox_id == sandbox_id)
        )


def stored_assessment(pg_engine: Engine, assessment_id: str) -> models.RiskAssessment:
    with Session(pg_engine) as db:
        row = db.get(models.RiskAssessment, uuid.UUID(assessment_id))
        assert row is not None, "the assessment was committed"
        return row


def audit_of(
    pg_engine: Engine, target_id: str, event_type: str | None = None
) -> list[models.AuditEvent]:
    with Session(pg_engine) as db:
        query = select(models.AuditEvent).where(models.AuditEvent.target_id == uuid.UUID(target_id))
        if event_type is not None:
            query = query.where(models.AuditEvent.event_type == event_type)
        return list(db.scalars(query.order_by(models.AuditEvent.created_at)))


def assert_sanitized(event: models.AuditEvent, *secrets: str) -> None:
    """Audit details carry no credential-like keys or values."""
    dumped = json.dumps(event.details)
    for key in event.details:
        assert not any(marker in key.lower() for marker in SECRET_MARKERS), key
    for secret in secrets:
        assert secret not in dumped


def add_restriction(pg_engine: Engine, customer: Customer, symbol: str, action: str) -> str:
    """Insert a reviewed ACTIVE decision directly; the restriction endpoints are Task 11."""
    restriction_id = uuid.uuid4()
    with Session(pg_engine) as db, db.begin():
        db.add(
            models.RecipientRestriction(
                id=restriction_id,
                sandbox_id=customer.sandbox_id,
                recipient_account_id=uuid.UUID(customer.recipient_id(symbol)),
                action=action,
                reason="[Synthetic test] Reviewed decision added before confirmation.",
                created_by=uuid.UUID(customer.actor_id("Ops")),
                expires_at=db.scalar(select(func.now())) + timedelta(hours=1),
            )
        )
    return str(restriction_id)


def pass_deadline(pg_engine: Engine, transfer_id: str) -> None:
    """Move a stored deadline into the past; the row itself still says it is active."""
    with pg_engine.begin() as connection:
        connection.execute(
            update(models.Transfer)
            .where(models.Transfer.id == uuid.UUID(transfer_id))
            .values(expires_at=func.now() - timedelta(seconds=1))
        )


_BALANCE_DRIFT = text(
    """
    SELECT a.id, a.balance_vnd, COALESCE(SUM(l.amount_vnd), 0) AS ledger_sum
    FROM accounts a
    LEFT JOIN ledger_entries l ON l.sandbox_id = a.sandbox_id AND l.account_id = a.id
    WHERE a.sandbox_id = :sandbox
    GROUP BY a.id, a.balance_vnd
    HAVING a.balance_vnd <> COALESCE(SUM(l.amount_vnd), 0)
    """
)
_RESERVATION_DRIFT = text(
    """
    SELECT a.id, a.reserved_vnd,
           COALESCE(SUM(t.reserved_amount_vnd) FILTER (WHERE t.status IN ('RISK_HELD', 'READY')), 0)
    FROM accounts a
    LEFT JOIN transfers t ON t.sandbox_id = a.sandbox_id AND t.sender_account_id = a.id
    WHERE a.sandbox_id = :sandbox
    GROUP BY a.id, a.reserved_vnd
    HAVING a.reserved_vnd <> COALESCE(
        SUM(t.reserved_amount_vnd) FILTER (WHERE t.status IN ('RISK_HELD', 'READY')), 0)
    """
)
_NEGATIVE_OR_OVERDRAWN = text(
    """
    SELECT id, balance_vnd, reserved_vnd FROM accounts
    WHERE sandbox_id = :sandbox
      AND (balance_vnd < 0 OR reserved_vnd < 0 OR reserved_vnd > balance_vnd)
    """
)
_STRANDED_RESERVATION = text(
    """
    SELECT id, status, reserved_amount_vnd FROM transfers
    WHERE sandbox_id = :sandbox
      AND ((status IN ('RISK_HELD', 'READY')) <> (reserved_amount_vnd = amount_vnd)
           OR (status NOT IN ('RISK_HELD', 'READY') AND reserved_amount_vnd <> 0))
    """
)
_LEDGER_LEGS = text(
    """
    SELECT t.id, t.status, count(l.id) AS legs
    FROM transfers t
    LEFT JOIN ledger_entries l ON l.sandbox_id = t.sandbox_id AND l.transfer_id = t.id
    WHERE t.sandbox_id = :sandbox
    GROUP BY t.id, t.status
    HAVING NOT (
        (t.status = 'SUCCEEDED'
         AND count(l.id) = 2
         AND count(l.id) FILTER (WHERE l.kind = 'TRANSFER_DEBIT'
             AND l.account_id = t.sender_account_id AND l.amount_vnd = -t.amount_vnd) = 1
         AND count(l.id) FILTER (WHERE l.kind = 'TRANSFER_CREDIT'
             AND l.account_id = t.recipient_account_id AND l.amount_vnd = t.amount_vnd) = 1)
        OR (t.status <> 'SUCCEEDED' AND count(l.id) = 0)
    )
    """
)


def assert_money_invariants(pg_engine: Engine, sandbox_id: uuid.UUID) -> None:
    """Cached balances equal the ledger, reservations equal active holds, no overdraft.

    Every SUCCEEDED transfer has exactly one sender debit and one recipient credit of its
    amount; every other transfer has no ledger entry.
    """
    with pg_engine.connect() as connection:
        for label, statement in (
            ("balance differs from ledger sum", _BALANCE_DRIFT),
            ("reserved differs from active holds", _RESERVATION_DRIFT),
            ("negative or overdrawn account", _NEGATIVE_OR_OVERDRAWN),
            ("stranded or missing reservation", _STRANDED_RESERVATION),
            ("ledger legs inconsistent with status", _LEDGER_LEGS),
        ):
            rows = connection.execute(statement, {"sandbox": sandbox_id}).all()
            assert rows == [], (label, rows)
