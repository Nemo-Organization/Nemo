"""Task 6: the pure behavioral/recipient evaluator and the assessment fact fingerprint.

No database: `evaluate_risk` and `fingerprint_facts` are pure functions of `RiskFacts`. The
database-facing fact collection is exercised through HTTP in tests/test_assessments.py.
"""

import dataclasses
import hashlib
import json
import re
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from app.risk.facts import POLICY_VERSION, RiskFacts, facts_document, fingerprint_facts, median_of
from app.risk.service import evaluate_risk

TRANSFER = UUID("00000000-0000-4000-8000-000000000001")
SENDER = UUID("00000000-0000-4000-8000-000000000002")
RECIPIENT = UUID("00000000-0000-4000-8000-000000000003")
RESTRICTION = UUID("00000000-0000-4000-8000-000000000004")
LINH_HISTORY = [100_000, 200_000, 300_000, 400_000, 500_000]


def facts(**overrides: Any) -> RiskFacts:
    """Linh's MAIN_REFUND facts for an 8,000,000 transfer to an unrestricted recipient."""
    values: dict[str, Any] = {
        "transfer_id": TRANSFER,
        "sender_account_id": SENDER,
        "recipient_account_id": RECIPIENT,
        "amount_vnd": 8_000_000,
        "sample_count": 5,
        "median_vnd": Decimal(300_000),
        "restriction_id": None,
        "restriction_action": None,
    }
    values.update(overrides)
    return RiskFacts(**values)


def signals(decision) -> tuple[str, str, str, list[str]]:
    return (
        decision.decision,
        decision.behavior_signal,
        decision.recipient_signal,
        [reason.code for reason in decision.reasons],
    )


def test_8m_against_300k_median_warns():
    assert median_of(LINH_HISTORY) == Decimal(300_000)
    assert POLICY_VERSION == "guardian-rules-v1"

    warned = evaluate_risk(facts())

    assert signals(warned) == ("WARN", "ANOMALOUS", "NONE", ["AMOUNT_ABOVE_BASELINE"])
    (reason,) = warned.reasons
    assert reason.restriction_id is None and reason.message
    assert evaluate_risk(facts()) == warned, "pure and deterministic"
    maximum = evaluate_risk(facts(amount_vnd=1_000_000_000))
    assert signals(maximum)[:3] == ("WARN", "ANOMALOUS", "NONE"), "behavior alone never holds"
    ordinary = evaluate_risk(facts(amount_vnd=20_000))
    assert signals(ordinary) == ("ALLOW", "NORMAL", "NONE", [])


def test_2m_threshold_is_inclusive():
    # Median 300,000: three times the median is 900,000, so the 2,000,000 floor governs.
    assert evaluate_risk(facts(amount_vnd=2_000_000)).behavior_signal == "ANOMALOUS"
    assert evaluate_risk(facts(amount_vnd=1_999_999)).behavior_signal == "NORMAL"
    # Median 700,000: three times the median (2,100,000) governs and is inclusive too.
    high = Decimal(700_000)
    assert evaluate_risk(facts(median_vnd=high, amount_vnd=2_100_000)).behavior_signal == (
        "ANOMALOUS"
    )
    assert evaluate_risk(facts(median_vnd=high, amount_vnd=2_099_999)).behavior_signal == "NORMAL"
    assert evaluate_risk(facts(median_vnd=high, amount_vnd=2_000_000)).behavior_signal == "NORMAL"
    # An even sample count can give a half-VND median; the comparison stays exact.
    half = median_of([1_000_000, 1_000_000, 1_000_001, 1_000_001, 5, 9_000_000])
    assert half == Decimal("1000000.5")
    assert evaluate_risk(facts(median_vnd=half, amount_vnd=3_000_001)).behavior_signal == "NORMAL"
    assert evaluate_risk(facts(median_vnd=half, amount_vnd=3_000_002)).behavior_signal == (
        "ANOMALOUS"
    )
    assert median_of([]) is None
    assert median_of([7]) == Decimal(7)
    assert median_of([400_000, 100_000, 300_000, 200_000]) == Decimal(250_000)


def test_four_samples_are_insufficient():
    four = evaluate_risk(facts(sample_count=4))
    assert signals(four) == ("ALLOW", "INSUFFICIENT_HISTORY", "NONE", [])
    assert signals(evaluate_risk(facts(sample_count=5)))[1] == "ANOMALOUS", "five is enough"
    none = evaluate_risk(facts(sample_count=0, median_vnd=None))
    assert signals(none) == ("ALLOW", "INSUFFICIENT_HISTORY", "NONE", [])
    an = evaluate_risk(facts(sample_count=2, median_vnd=Decimal(200_000)))
    assert signals(an) == ("ALLOW", "INSUFFICIENT_HISTORY", "NONE", [])
    sparse_hold = evaluate_risk(
        facts(sample_count=2, restriction_id=RESTRICTION, restriction_action="HOLD")
    )
    assert signals(sparse_hold) == ("HOLD", "INSUFFICIENT_HISTORY", "HOLD", ["RECIPIENT_HOLD"])


def test_recipient_signal_is_independent_and_hold_wins():
    hold = evaluate_risk(
        facts(amount_vnd=20_000, restriction_id=RESTRICTION, restriction_action="HOLD")
    )
    assert signals(hold) == ("HOLD", "NORMAL", "HOLD", ["RECIPIENT_HOLD"])
    assert hold.reasons[0].restriction_id == RESTRICTION
    warn = evaluate_risk(
        facts(amount_vnd=20_000, restriction_id=RESTRICTION, restriction_action="WARN")
    )
    assert signals(warn) == ("WARN", "NORMAL", "WARN", ["RECIPIENT_WARNING"])
    assert warn.reasons[0].restriction_id == RESTRICTION
    both = evaluate_risk(facts(restriction_id=RESTRICTION, restriction_action="HOLD"))
    assert signals(both) == (
        "HOLD",
        "ANOMALOUS",
        "HOLD",
        ["RECIPIENT_HOLD", "AMOUNT_ABOVE_BASELINE"],
    )
    assert both.reasons[1].restriction_id is None
    warned_twice = evaluate_risk(facts(restriction_id=RESTRICTION, restriction_action="WARN"))
    assert signals(warned_twice) == (
        "WARN",
        "ANOMALOUS",
        "WARN",
        ["RECIPIENT_WARNING", "AMOUNT_ABOVE_BASELINE"],
    )
    assert len({reason.message for reason in both.reasons + warn.reasons}) == 3


def test_assessment_fingerprint_changes_with_relevant_facts():
    base = facts()
    fingerprint = fingerprint_facts(base)

    assert re.fullmatch(r"[0-9a-f]{64}", fingerprint)
    assert fingerprint_facts(facts()) == fingerprint, "equal facts give equal fingerprints"
    canonical = json.dumps(facts_document(base), sort_keys=True, separators=(",", ":"))
    assert fingerprint == hashlib.sha256(canonical.encode("utf-8")).hexdigest(), (
        "SHA-256 of canonical JSON: stable across processes"
    )

    document = facts_document(base)
    assert {field.name for field in dataclasses.fields(RiskFacts)} <= set(document)
    assert (document["sample_count"], document["median_vnd"], document["threshold_vnd"]) == (
        5,
        300_000,
        2_000_000,
    )
    assert (document["restriction_id"], document["restriction_action"]) == (None, None)
    assert document["policy_version"] == "guardian-rules-v1"
    assert facts_document(facts(sample_count=4))["threshold_vnd"] is None
    assert facts_document(facts(median_vnd=Decimal("1000000.5")))["median_vnd"] == 1_000_000.5
    json.dumps(document, allow_nan=False)

    changed = {
        "amount": facts(amount_vnd=8_000_001),
        "sample count": facts(sample_count=6),
        "median": facts(median_vnd=Decimal(310_000)),
        "median unknown": facts(sample_count=0, median_vnd=None),
        "restriction id": facts(restriction_id=RESTRICTION, restriction_action="HOLD"),
        "other restriction": facts(restriction_id=uuid4(), restriction_action="HOLD"),
        "restriction action": facts(restriction_id=RESTRICTION, restriction_action="WARN"),
        "policy version": facts(policy_version="guardian-rules-v2"),
        "transfer": facts(transfer_id=uuid4()),
        "sender": facts(sender_account_id=uuid4()),
        "recipient": facts(recipient_account_id=uuid4()),
    }
    fingerprints = {label: fingerprint_facts(value) for label, value in changed.items()}
    for label, value in fingerprints.items():
        assert value != fingerprint, f"{label} must change the fingerprint"
    assert len(set(fingerprints.values())) == len(fingerprints)
