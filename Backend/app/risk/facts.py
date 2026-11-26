"""Risk facts: the inputs of one deterministic evaluation, how they are read, and their digest.

`collect_facts` reads the sender's behavioral history and the recipient's current restriction in
one SQL statement, so both come from one snapshot and one database `now()`. History is the sender
wallet's SUCCEEDED transfers created in the 30 days before database time. A restriction counts
only while `status = 'ACTIVE' AND expires_at > now()`; an expired row that still says ACTIVE is
ignored. Nothing here writes, flushes or commits.

`fingerprint_facts` is SHA-256 of canonical JSON (sorted keys, no whitespace) of the persisted
facts document: the immutable instruction, history sample count and median, the derived
threshold, the active restriction ID/action, the rule parameters and the policy version. It
excludes timestamps, so unchanged facts keep their fingerprint across assessments.
"""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app import models

RestrictionAction = Literal["WARN", "HOLD"]

POLICY_VERSION = "guardian-rules-v1"
HISTORY_WINDOW_DAYS = 30
MIN_OBSERVATIONS = 5
MEDIAN_MULTIPLIER = 3
MIN_ANOMALY_VND = 2_000_000
# More severe actions sort first when choosing the current restriction.
_SEVERITY = {"HOLD": 0, "WARN": 1}


@dataclass(frozen=True, slots=True)
class RiskFacts:
    """Everything one evaluation depends on. Every field is fingerprinted."""

    transfer_id: UUID
    sender_account_id: UUID
    recipient_account_id: UUID
    amount_vnd: int
    sample_count: int
    median_vnd: Decimal | None
    restriction_id: UUID | None
    restriction_action: RestrictionAction | None
    policy_version: str = POLICY_VERSION

    @property
    def has_baseline(self) -> bool:
        return self.sample_count >= MIN_OBSERVATIONS and self.median_vnd is not None

    @property
    def threshold_vnd(self) -> Decimal | None:
        """Smallest anomalous amount: both bounds are inclusive."""
        if not self.has_baseline or self.median_vnd is None:
            return None
        return max(MEDIAN_MULTIPLIER * self.median_vnd, Decimal(MIN_ANOMALY_VND))


def median_of(amounts: Sequence[int]) -> Decimal | None:
    """Exact median; an even count averages the two middle values (possibly half a VND)."""
    if not amounts:
        return None
    ordered = sorted(amounts)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return Decimal(ordered[middle])
    return (Decimal(ordered[middle - 1]) + Decimal(ordered[middle])) / 2


def _number(value: Decimal | None) -> int | float | None:
    """JSON number: an integer when whole, else the exact half-VND float."""
    if value is None:
        return None
    return int(value) if value == value.to_integral_value() else float(value)


def facts_document(facts: RiskFacts) -> dict[str, Any]:
    """JSON object persisted in risk_assessments.facts and hashed into the fingerprint."""
    return {
        "policy_version": facts.policy_version,
        "transfer_id": str(facts.transfer_id),
        "sender_account_id": str(facts.sender_account_id),
        "recipient_account_id": str(facts.recipient_account_id),
        "amount_vnd": facts.amount_vnd,
        "history_window_days": HISTORY_WINDOW_DAYS,
        "min_observations": MIN_OBSERVATIONS,
        "median_multiplier": MEDIAN_MULTIPLIER,
        "min_anomaly_vnd": MIN_ANOMALY_VND,
        "sample_count": facts.sample_count,
        "median_vnd": _number(facts.median_vnd),
        "threshold_vnd": _number(facts.threshold_vnd),
        "restriction_id": None if facts.restriction_id is None else str(facts.restriction_id),
        "restriction_action": facts.restriction_action,
    }


def fingerprint_facts(facts: RiskFacts) -> str:
    canonical = json.dumps(
        facts_document(facts), sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def collect_facts(session: Session, transfer: models.Transfer) -> RiskFacts:
    """Current history and restriction facts for `transfer`, from one database snapshot."""
    now = func.now()
    history = models.Transfer.__table__.alias("history")
    amounts = (
        select(func.array_agg(history.c.amount_vnd))
        .where(
            history.c.sandbox_id == transfer.sandbox_id,
            history.c.sender_account_id == transfer.sender_account_id,
            history.c.status == "SUCCEEDED",
            history.c.created_at >= now - timedelta(days=HISTORY_WINDOW_DAYS),
            history.c.id != transfer.id,
        )
        .scalar_subquery()
    )
    restriction = models.RecipientRestriction
    active = (
        select(restriction.id, restriction.action)
        .where(
            restriction.sandbox_id == transfer.sandbox_id,
            restriction.recipient_account_id == transfer.recipient_account_id,
            restriction.status == "ACTIVE",
            restriction.expires_at > now,
        )
        .order_by(
            case(_SEVERITY, value=restriction.action, else_=len(_SEVERITY)),
            restriction.created_at.desc(),
            restriction.id.desc(),
        )
        .limit(1)
        .cte("active_restriction")
    )
    observed, restriction_id, restriction_action = session.execute(
        select(
            amounts,
            select(active.c.id).scalar_subquery(),
            select(active.c.action).scalar_subquery(),
        )
    ).one()
    samples: list[int] = list(observed or [])
    return RiskFacts(
        transfer_id=transfer.id,
        sender_account_id=transfer.sender_account_id,
        recipient_account_id=transfer.recipient_account_id,
        amount_vnd=transfer.amount_vnd,
        sample_count=len(samples),
        median_vnd=median_of(samples),
        restriction_id=restriction_id,
        restriction_action=restriction_action,
    )
