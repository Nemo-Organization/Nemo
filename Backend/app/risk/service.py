"""Independent behavioral and recipient risk: a pure evaluator and the assessTransfer service.

Rules (guardian-rules-v1, product requirements G03-G05):
- Behavior: fewer than five settled observations is INSUFFICIENT_HISTORY. Otherwise an amount
  >= 3 x median AND >= 2,000,000 (both inclusive) is ANOMALOUS, else NORMAL.
- Recipient: the most severe currently active restriction gives HOLD or WARN, else NONE.
- Decision: HOLD if the recipient signal is HOLD, else WARN if any warning, else ALLOW.
  Behavioral risk alone never produces HOLD.
Reasons list the recipient reason first, then the behavioral reason. No model is ever called.

Rulings where the docs are silent:
- Assessable states are DRAFT, RISK_HELD and READY (the contract's "draft or active held/ready
  transfer"). Any other state is 409 STATE_CONFLICT with the current transfer.
- An assessable transfer whose deadline has passed is also 409 STATE_CONFLICT and records
  nothing; expiry reconciliation itself belongs to the transfer lifecycle service.
"""

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Literal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.api.schemas import RiskAssessment, RiskReason
from app.auth.principal import Principal
from app.auth.service import database_now
from app.errors import ApplicationError
from app.risk.facts import (
    MEDIAN_MULTIPLIER,
    MIN_ANOMALY_VND,
    RiskFacts,
    collect_facts,
    facts_document,
    fingerprint_facts,
)
from app.transfers import serialization
from app.transfers.service import owned_transfer

Decision = Literal["ALLOW", "WARN", "HOLD"]
BehaviorSignal = Literal["NORMAL", "ANOMALOUS", "INSUFFICIENT_HISTORY"]
RecipientSignal = Literal["NONE", "WARN", "HOLD"]

DEFAULT_ASSESSMENT_LIFETIME = timedelta(minutes=5)
ASSESSABLE_STATUSES = frozenset({"DRAFT", "RISK_HELD", "READY"})
MESSAGES = {
    "RECIPIENT_HOLD": "This recipient requires additional review based on verified reports.",
    "RECIPIENT_WARNING": "Reviewed reports about this recipient call for extra care before "
    "you send money.",
    "AMOUNT_ABOVE_BASELINE": "This amount is at least three times your usual transfer amount "
    "over the last 30 days.",
}


@dataclass(frozen=True, slots=True)
class RiskDecision:
    decision: Decision
    behavior_signal: BehaviorSignal
    recipient_signal: RecipientSignal
    reasons: tuple[RiskReason, ...]


def _behavior(facts: RiskFacts) -> BehaviorSignal:
    if not facts.has_baseline or facts.median_vnd is None:
        return "INSUFFICIENT_HISTORY"
    amount = Decimal(facts.amount_vnd)
    if amount >= MEDIAN_MULTIPLIER * facts.median_vnd and facts.amount_vnd >= MIN_ANOMALY_VND:
        return "ANOMALOUS"
    return "NORMAL"


def evaluate_risk(facts: RiskFacts) -> RiskDecision:
    """Pure function of `facts`: no I/O, clock or randomness."""
    behavior = _behavior(facts)
    recipient: RecipientSignal = facts.restriction_action or "NONE"
    reasons: list[RiskReason] = []
    if recipient != "NONE":
        code = "RECIPIENT_HOLD" if recipient == "HOLD" else "RECIPIENT_WARNING"
        reasons.append(
            RiskReason(code=code, message=MESSAGES[code], restriction_id=facts.restriction_id)
        )
    if behavior == "ANOMALOUS":
        reasons.append(
            RiskReason(
                code="AMOUNT_ABOVE_BASELINE",
                message=MESSAGES["AMOUNT_ABOVE_BASELINE"],
                restriction_id=None,
            )
        )
    decision: Decision = "HOLD" if recipient == "HOLD" else "WARN" if reasons else "ALLOW"
    return RiskDecision(decision, behavior, recipient, tuple(reasons))


def record_assessment(
    session: Session,
    transfer: models.Transfer,
    facts: RiskFacts,
    decision: RiskDecision,
    *,
    lifetime: timedelta = DEFAULT_ASSESSMENT_LIFETIME,
) -> models.RiskAssessment:
    """Persist one assessment snapshot (flush only). Times are database `now()`."""
    row = models.RiskAssessment(
        sandbox_id=transfer.sandbox_id,
        transfer_id=transfer.id,
        decision=decision.decision,
        behavior_signal=decision.behavior_signal,
        recipient_signal=decision.recipient_signal,
        policy_version=facts.policy_version,
        facts_fingerprint=fingerprint_facts(facts),
        reasons=[reason.model_dump(mode="json") for reason in decision.reasons],
        facts=facts_document(facts),
        assessed_at=func.now(),
        expires_at=func.now() + lifetime,
    )
    session.add(row)
    session.flush()
    session.refresh(row)
    return row


def state_conflict(session: Session, transfer: models.Transfer, message: str) -> ApplicationError:
    return ApplicationError(
        409,
        "STATE_CONFLICT",
        message,
        current_transfer=serialization.load_transfer_view(session, transfer),
    )


def assess_transfer(
    session: Session,
    principal: Principal,
    transfer_id: UUID,
    *,
    lifetime: timedelta = DEFAULT_ASSESSMENT_LIFETIME,
) -> RiskAssessment:
    """Evaluate and persist current risk for the caller's own active transfer.

    Changes no balance, reservation or transfer status.
    """
    transfer = owned_transfer(session, principal, transfer_id)
    if transfer.status not in ASSESSABLE_STATUSES:
        raise state_conflict(session, transfer, "This transfer can no longer be assessed.")
    if transfer.expires_at <= database_now(session):
        raise state_conflict(session, transfer, "This transfer has passed its deadline.")
    facts = collect_facts(session, transfer)
    row = record_assessment(session, transfer, facts, evaluate_risk(facts), lifetime=lifetime)
    assessment = serialization.assessment_view(row)
    session.commit()
    return assessment
