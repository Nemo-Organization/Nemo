"""Contract DTOs, pagination and structured conflicts (backend Task 2)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any

import pytest
import yaml
from fastapi import Query
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api import schemas
from app.api.pagination import PageParams
from app.errors import ApplicationError
from app.main import create_app

OPENAPI = yaml.safe_load(
    (Path(__file__).resolve().parents[2] / "docs/guardian/openapi.yaml").read_text(encoding="utf-8")
)
COMPONENTS: dict[str, Any] = OPENAPI["components"]["schemas"]
# Components that are intentionally not Pydantic JSON models in app.api.schemas.
NOT_JSON_DTOS = {
    "CreateAnalysis": "multipart form; image and text are parsed with Form/File in Task 9",
    "Health": "existing skeleton model in app/health.py",
}
NOW = datetime(2026, 11, 25, 9, 0, tzinfo=UTC)


def transfer_payload(**changes: Any) -> dict[str, Any]:
    payload = {
        "client_request_id": str(uuid.uuid4()),
        "sender_account_id": str(uuid.uuid4()),
        "recipient_account_id": str(uuid.uuid4()),
        "amount_vnd": 20_000,
    }
    payload.update(changes)
    return payload


def sample_transfer(**changes: Any) -> schemas.Transfer:
    values: dict[str, Any] = {
        "id": uuid.uuid4(),
        "sender_account_id": uuid.uuid4(),
        "recipient": schemas.Recipient(
            id=uuid.uuid4(),
            display_name="Risk recipient",
            bank_code="NEMO",
            masked_identifier="**** 9012",
        ),
        "amount_vnd": 20_000,
        "status": "RISK_HELD",
        "reserved_amount_vnd": 20_000,
        "expires_at": NOW + timedelta(minutes=15),
        "created_at": NOW,
        "completed_at": None,
        "assessment": None,
        "review_reason": None,
        "replayed": False,
    }
    values.update(changes)
    return schemas.Transfer(**values)


def test_amount_rejects_bool_float_zero_and_over_limit():
    assert schemas.CreateTransfer.model_validate(transfer_payload()).amount_vnd == 20_000
    assert (
        schemas.CreateTransfer.model_validate(transfer_payload(amount_vnd=1_000_000_000)).amount_vnd
        == 1_000_000_000
    )
    for invalid in (True, False, 20_000.0, 20_000.5, "20000", 0, -1, 1_000_000_001):
        with pytest.raises(ValidationError):
            schemas.CreateTransfer.model_validate(transfer_payload(amount_vnd=invalid))
        with pytest.raises(ValidationError):
            schemas.CreateTransfer.model_validate_json(
                json.dumps(transfer_payload(amount_vnd=invalid))
            )


def test_required_nullable_fields_remain_present():
    order = schemas.Order(
        id=uuid.uuid4(),
        order_reference="SHOP-4502",
        merchant_name="Synthetic shop",
        original_amount_vnd=500_000,
        return_fee_vnd=None,
        fee_source=None,
        fee_verified_at=None,
        refund=None,
    ).model_dump(mode="json")
    assert {k: order[k] for k in ("return_fee_vnd", "fee_source", "fee_verified_at", "refund")} == {
        "return_fee_vnd": None,
        "fee_source": None,
        "fee_verified_at": None,
        "refund": None,
    }

    transfer = sample_transfer().model_dump(mode="json")
    assert transfer["completed_at"] is None
    assert transfer["assessment"] is None
    assert transfer["review_reason"] is None
    assert transfer["expires_at"] == "2026-11-25T09:15:00Z"

    with pytest.raises(ValidationError):
        schemas.Transfer(
            **{k: v for k, v in sample_transfer().__dict__.items() if k != "assessment"}
        )

    analysis = schemas.Analysis(
        id=uuid.uuid4(),
        status="FAILED",
        finding="UNCERTAIN",
        evidence=None,
        official_facts=schemas.OfficialFacts(
            transfer_amount_vnd=20_000,
            direction="OUTGOING",
            refund_amount_vnd=None,
            refund_status="UNKNOWN",
            return_fee_vnd=None,
            fee_source=None,
        ),
        evidence_available=False,
        error_code="MODEL_TIMEOUT",
        replayed=False,
    ).model_dump(mode="json")
    assert analysis["evidence"] is None
    assert analysis["dossier"] is None
    assert analysis["official_facts"]["return_fee_vnd"] is None


def test_extra_body_fields_rejected():
    with pytest.raises(ValidationError):
        schemas.CreateTransfer.model_validate(transfer_payload(role="OPERATOR"))
    with pytest.raises(ValidationError):
        schemas.SelectActor.model_validate({"actor_id": str(uuid.uuid4()), "sandbox_id": "x"})
    with pytest.raises(ValidationError):
        schemas.ConfirmTransfer.model_validate({"acknowledged_assessment_id": None})
    assert schemas.ConfirmTransfer.model_validate({}).acknowledged_assessment_id is None

    app = create_app()

    @app.post("/test/transfers")
    async def create(payload: schemas.CreateTransfer):
        return {"amount_vnd": payload.amount_vnd}

    with TestClient(app) as client:
        assert client.post("/test/transfers", json=transfer_payload()).status_code == 200
        for body in (transfer_payload(role="OPERATOR"), transfer_payload(amount_vnd=True)):
            response = client.post("/test/transfers", json=body)
            assert response.status_code == 422
            assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_request_ids_text_lists_and_timestamps_are_strict():
    report = {"client_request_id": str(uuid.uuid4()), "recipient_account_id": str(uuid.uuid4())}
    assert schemas.CreateReport.model_validate({**report, "narrative": "Asked to advance a fee."})
    for invalid in (
        {"narrative": ""},
        {"narrative": "x" * 4001},
        {"narrative": "ok", "transfer_id": "not-a-uuid"},
    ):
        with pytest.raises(ValidationError):
            schemas.CreateReport.model_validate({**report, **invalid})

    evidence_id = str(uuid.uuid4())
    restriction = {
        "recipient_account_id": str(uuid.uuid4()),
        "action": "HOLD",
        "reason": "Reviewed near-miss reports",
        "evidence_report_ids": [evidence_id],
        "expires_at": "2026-11-26T09:00:00Z",
    }
    assert schemas.CreateRestriction.model_validate(restriction).expires_at.tzinfo is not None
    for invalid in (
        {"evidence_report_ids": [evidence_id, evidence_id]},
        {"evidence_report_ids": []},
        {"expires_at": "2026-11-26T09:00:00"},
        {"action": "BLOCK"},
    ):
        with pytest.raises(ValidationError):
            schemas.CreateRestriction.model_validate({**restriction, **invalid})

    evidence = {
        "transcription": "Chi ung giup em 20k phi thu hoi",
        "requested_action": "SHARE_SECRET",
        "claimed_purpose": "Receive the pending order refund",
        "quotes": [],
        "extracted_references": [],
        "missing_information": [],
    }
    assert schemas.ModelEvidence.model_validate(evidence).additional_actions == []
    assert schemas.ModelEvidence.model_validate({**evidence, "additional_actions": ["PAY_FEE"]})
    for invalid in (
        ["UNKNOWN"],
        ["PAY_FEE", "PAY_FEE"],
        ["SHARE_SECRET"],
        ["PAY_FEE", "OTHER", "CONFIRM_LOGIN", "PAY_PURCHASE"],
    ):
        with pytest.raises(ValidationError):
            schemas.ModelEvidence.model_validate({**evidence, "additional_actions": invalid})


def test_error_context_matches_contract():
    app = create_app()
    transfer = sample_transfer()
    assessment = schemas.RiskAssessment(
        id=uuid.uuid4(),
        transfer_id=transfer.id,
        decision="WARN",
        behavior_signal="ANOMALOUS",
        recipient_signal="NONE",
        reasons=[
            schemas.RiskReason(
                code="AMOUNT_ABOVE_BASELINE", message="Unusual amount.", restriction_id=None
            )
        ],
        policy_version="guardian-rules-v1",
        assessed_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
    )

    @app.get("/test/plain-conflict")
    async def plain():
        raise ApplicationError(409, "IDEMPOTENCY_CONFLICT", "Request key reused.")

    @app.get("/test/transfer-conflict")
    async def with_transfer():
        raise ApplicationError(
            409, "STATE_CONFLICT", "Transfer changed.", current_transfer=transfer
        )

    @app.get("/test/acknowledgement")
    async def with_assessment():
        raise ApplicationError(
            409, "ACKNOWLEDGEMENT_REQUIRED", "Review the current assessment.", assessment=assessment
        )

    with TestClient(app) as client:
        plain_error = client.get("/test/plain-conflict").json()["error"]
        transfer_error = client.get("/test/transfer-conflict").json()["error"]
        assessment_error = client.get("/test/acknowledgement").json()["error"]

    assert set(plain_error) == {"code", "message", "request_id"}
    assert set(transfer_error) == {"code", "message", "request_id", "current_transfer"}
    assert transfer_error["current_transfer"] == transfer.model_dump(mode="json")
    assert transfer_error["current_transfer"]["completed_at"] is None
    assert set(assessment_error) == {"code", "message", "request_id", "assessment"}
    assert assessment_error["assessment"]["reasons"][0]["restriction_id"] is None


def test_pagination_bounds():
    assert (PageParams().limit, PageParams().offset) == (20, 0)
    assert PageParams(limit=100, offset=40).limit == 100
    for invalid in ({"limit": 0}, {"limit": 101}, {"offset": -1}):
        with pytest.raises(ValidationError):
            PageParams(**invalid)

    page = schemas.RecipientList(items=[], total=0, limit=20, offset=0).model_dump(mode="json")
    assert page == {"items": [], "total": 0, "limit": 20, "offset": 0}

    app = create_app()

    @app.get("/test/page")
    async def page_endpoint(params: Annotated[PageParams, Query()]):
        return {"limit": params.limit, "offset": params.offset}

    with TestClient(app) as client:
        assert client.get("/test/page").json() == {"limit": 20, "offset": 0}
        assert client.get("/test/page?limit=100&offset=5").json() == {"limit": 100, "offset": 5}
        for query in ("limit=0", "limit=101", "offset=-1", "limit=1.5", "limit=true"):
            response = client.get(f"/test/page?{query}")
            assert response.status_code == 422, query
            assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def normalize(node: dict[str, Any], defs: dict[str, Any]) -> dict[str, Any]:
    """Reduce a JSON schema node to what the contract fixes: shape, nullability, enums, bounds."""
    if "$ref" in node:
        name = node["$ref"].rsplit("/", 1)[-1]
        if name in COMPONENTS or name not in defs:
            return {"ref": name}
        return normalize(defs[name], defs)  # Pydantic-only helper model, e.g. ErrorDetail
    if "anyOf" in node:
        options = [option for option in node["anyOf"] if option.get("type") != "null"]
        assert len(options) == 1, node
        inner = normalize(options[0], defs)
        return {**inner, "nullable": len(options) != len(node["anyOf"])}
    result: dict[str, Any] = {"nullable": False}
    kind = node.get("type")
    if isinstance(kind, list):
        result["nullable"] = "null" in kind
        kind = next(k for k in kind if k != "null")
    if kind is not None:
        result["type"] = kind
    if "const" in node:
        result["enum"] = [node["const"]]
    if "enum" in node:
        result["enum"] = list(node["enum"])
    for key in ("minimum", "maximum", "minLength", "maxLength", "minItems", "maxItems", "pattern"):
        if key in node:
            result[key] = node[key]
    if node.get("uniqueItems"):
        result["uniqueItems"] = True
    if kind == "string" and "format" in node:
        result["format"] = node["format"]
    if "items" in node:
        result["items"] = normalize(node["items"], defs)
    if kind == "object":
        result["properties"] = {
            key: normalize(value, defs) for key, value in node.get("properties", {}).items()
        }
        result["required"] = sorted(node.get("required", []))
        result["additionalProperties"] = node.get("additionalProperties", True)
    return result


def test_dtos_match_openapi_components():
    covered = set(schemas.CONTRACT_SCHEMAS) | set(NOT_JSON_DTOS)
    assert sorted(set(COMPONENTS) - covered) == []
    assert sorted(set(schemas.CONTRACT_SCHEMAS) - set(COMPONENTS)) == []

    mismatches = {}
    for name, generate in schemas.CONTRACT_SCHEMAS.items():
        generated = generate(ref_template="#/components/schemas/{model}")
        defs = generated.pop("$defs", {})
        expected = normalize(COMPONENTS[name], {})
        actual = normalize(generated, defs)
        if expected != actual:
            mismatches[name] = {"openapi": expected, "pydantic": actual}
    assert mismatches == {}
