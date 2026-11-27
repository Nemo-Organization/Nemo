"""Pydantic DTOs for every JSON schema in docs/guardian/openapi.yaml.

Class names equal the OpenAPI component names; `tests/test_api_schemas.py` compares the generated
JSON schemas with the contract. Requests reject unknown fields. Responses keep required nullable
fields present as null. Optional, non-nullable fields are omitted rather than sent as null.
"""

from collections.abc import Callable
from enum import StrEnum
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StrictInt,
    TypeAdapter,
    model_validator,
)
from pydantic.json_schema import SkipJsonSchema

from app.api.pagination import Page

MAX_TRANSFER_VND = 1_000_000_000


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _unique[ItemT](values: list[ItemT]) -> list[ItemT]:
    if len(set(values)) != len(values):
        raise ValueError("Items must be unique.")
    return values


def _reject_null(value: Any) -> Any:
    if value is None:
        raise ValueError("Omit this field instead of sending null.")
    return value


def _require_string(value: Any) -> Any:
    if not isinstance(value, str):
        raise ValueError("Use an ISO 8601 date-time string with a UTC offset.")
    return value


# Integer VND for a transfer/order/refund amount. Strict: rejects bool, float and numeric strings.
Vnd = Annotated[StrictInt, Field(ge=1, le=MAX_TRANSFER_VND)]
VndBalance = Annotated[int, Field(ge=0)]
NonNegativeInt = Annotated[int, Field(ge=0)]
Note = Annotated[str, Field(min_length=1, max_length=4000)]
OptionalId = Annotated[UUID | SkipJsonSchema[None], BeforeValidator(_reject_null)]
RequestTimestamp = Annotated[AwareDatetime, BeforeValidator(_require_string)]
Message = Annotated[str, Field(min_length=1, max_length=500)]


def UniqueList(item: Any, *, min_items: int | None = None, max_items: int | None = None) -> Any:  # noqa: N802
    return Annotated[
        list[item],
        Field(min_length=min_items, max_length=max_items, json_schema_extra={"uniqueItems": True}),
        AfterValidator(_unique),
    ]


Role = Literal["CUSTOMER", "OPERATOR"]
Scenario = Literal["MAIN_REFUND", "FALSE_POSITIVE", "INSUFFICIENT_EVIDENCE"]
TransferStatus = Literal[
    "DRAFT", "RISK_HELD", "READY", "SUCCEEDED", "CANCELED", "REJECTED", "EXPIRED"
]
RequestedAction = Literal[
    "PAY_FEE",
    "PAY_PURCHASE",
    "CONFIRM_TRANSFER",
    "SHARE_SECRET",
    "CONFIRM_LOGIN",
    "OTHER",
    "UNKNOWN",
]
AdditionalAction = Literal[
    "PAY_FEE", "PAY_PURCHASE", "CONFIRM_TRANSFER", "SHARE_SECRET", "CONFIRM_LOGIN", "OTHER"
]
ClaimedTransferDirection = Literal["INCOMING", "OUTGOING", "UNKNOWN"]
RunStatus = Literal["PENDING", "SUCCEEDED", "FAILED", "TIMED_OUT"]
QuoteSource = Literal["IMAGE_TRANSCRIPTION", "CUSTOMER_TEXT", "REPORT"]
RestrictionAction = Literal["WARN", "HOLD"]


class InvestigationSignal(StrEnum):
    CLAIMS_OFFICIAL_ROLE = "CLAIMS_OFFICIAL_ROLE"
    URGENCY_PRESSURE = "URGENCY_PRESSURE"
    OFF_PLATFORM_CHANNEL = "OFF_PLATFORM_CHANNEL"
    PAYEE_DIFFERS_FROM_SENDER = "PAYEE_DIFFERS_FROM_SENDER"
    USES_ORDER_DETAILS = "USES_ORDER_DETAILS"
    DISCOURAGES_VERIFICATION = "DISCOURAGES_VERIFICATION"
    OTHER = "OTHER"


# Identity and accounts


class Actor(ContractModel):
    id: UUID
    role: Role
    display_name: str


class Account(ContractModel):
    id: UUID
    display_name: str
    bank_code: str
    masked_identifier: str
    balance_vnd: VndBalance
    reserved_vnd: VndBalance
    available_vnd: VndBalance


class Recipient(ContractModel):
    id: UUID
    display_name: str
    bank_code: str
    masked_identifier: str


class Bootstrap(ContractModel):
    sandbox_id: UUID
    scenario: Scenario
    expires_at: AwareDatetime
    actors: list[Actor]
    current_actor: Actor
    controller_csrf_token: str
    actor_csrf_token: str


class Me(ContractModel):
    sandbox_id: UUID
    actor: Actor
    accounts: list[Account]
    actor_csrf_token: str


# Orders, risk and transfers


class Refund(ContractModel):
    id: UUID
    order_id: UUID
    account_id: UUID
    amount_vnd: Vnd
    status: Literal["APPROVED", "SETTLED"]
    settled_at: AwareDatetime | None


class Order(ContractModel):
    id: UUID
    order_reference: str
    merchant_name: str
    original_amount_vnd: Vnd
    return_fee_vnd: NonNegativeInt | None
    fee_source: str | None
    fee_verified_at: AwareDatetime | None
    refund: Refund | None


class RiskReason(ContractModel):
    code: Literal["AMOUNT_ABOVE_BASELINE", "RECIPIENT_WARNING", "RECIPIENT_HOLD"]
    message: str
    restriction_id: UUID | None


class RiskAssessment(ContractModel):
    id: UUID
    transfer_id: UUID
    decision: Literal["ALLOW", "WARN", "HOLD"]
    behavior_signal: Literal["NORMAL", "ANOMALOUS", "INSUFFICIENT_HISTORY"]
    recipient_signal: Literal["NONE", "WARN", "HOLD"]
    reasons: list[RiskReason]
    policy_version: str
    assessed_at: AwareDatetime
    expires_at: AwareDatetime


class Transfer(ContractModel):
    id: UUID
    sender_account_id: UUID
    recipient: Recipient
    amount_vnd: Vnd
    status: TransferStatus
    reserved_amount_vnd: VndBalance
    expires_at: AwareDatetime
    created_at: AwareDatetime
    completed_at: AwareDatetime | None
    assessment: RiskAssessment | None
    review_reason: str | None
    replayed: bool


# Evidence analysis and investigation


class Quote(ContractModel):
    source: QuoteSource
    text: str
    report_id: UUID | None


class ModelEvidence(ContractModel):
    transcription: str
    requested_action: RequestedAction
    additional_actions: UniqueList(AdditionalAction, max_items=3) = Field(default_factory=list)
    claimed_transfer_direction: ClaimedTransferDirection = "UNKNOWN"
    claimed_purpose: str
    quotes: list[Quote]
    extracted_references: list[str]
    missing_information: list[str]

    @model_validator(mode="after")
    def additional_actions_exclude_primary(self) -> "ModelEvidence":
        if self.requested_action in self.additional_actions:
            raise ValueError("additional_actions must not repeat requested_action.")
        return self


class OfficialFacts(ContractModel):
    transfer_amount_vnd: NonNegativeInt | None
    direction: Literal["OUTGOING", "UNKNOWN"]
    refund_amount_vnd: NonNegativeInt | None
    refund_status: Literal["APPROVED", "SETTLED", "UNKNOWN"]
    return_fee_vnd: NonNegativeInt | None
    fee_source: str | None


class InvestigationSource(ContractModel):
    id: Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")]
    kind: Literal[
        "CUSTOMER_TEXT",
        "IMAGE_TRANSCRIPTION",
        "TRANSFER",
        "ORDER",
        "REFUND",
        "REPORT",
        "TRACE_REFERENCE",
        "ACCESS_EVENT",
    ]
    resource_id: UUID | None
    label: Annotated[str, Field(min_length=1, max_length=160)]
    excerpt: Annotated[str, Field(min_length=1, max_length=1000)]
    observed_at: AwareDatetime | None


class InvestigationFinding(ContractModel):
    id: Annotated[str, Field(min_length=1, max_length=80)]
    statement: Annotated[str, Field(min_length=1, max_length=1500)]
    relation: Literal["SUPPORTS_CONCERN", "COUNTERS_CONCERN", "UNRESOLVED"]
    source_ids: UniqueList(
        Annotated[str, Field(min_length=1, max_length=80)], min_items=1, max_items=8
    )
    signal: InvestigationSignal | None = None


class InvestigationActivity(ContractModel):
    step: Annotated[int, Field(ge=1, le=4)]
    tool: Literal[
        "get_customer_context",
        "read_case",
        "search_related_reports",
        "lookup_reference",
        "get_batch_access_events",
    ]
    status: Literal["SUCCEEDED", "NOT_FOUND", "DENIED", "UNAVAILABLE"]
    summary: Annotated[str, Field(min_length=1, max_length=240)]


class InvestigationDossier(ContractModel):
    version: Literal["guardian-dossier-v1"]
    sources: Annotated[list[InvestigationSource], Field(max_length=40)]
    findings: Annotated[list[InvestigationFinding], Field(max_length=8)]
    activity: Annotated[list[InvestigationActivity], Field(max_length=4)]
    recommended_checks: Annotated[list[Message], Field(max_length=5)]
    limitations: Annotated[list[Message], Field(max_length=8)]
    citation_warnings: Annotated[list[Message], Field(max_length=10)]


class Analysis(ContractModel):
    id: UUID
    status: RunStatus
    finding: Literal["MISMATCH", "CONSISTENT", "UNCERTAIN"]
    evidence: ModelEvidence | None
    official_facts: OfficialFacts
    evidence_available: bool
    error_code: str | None
    replayed: bool
    dossier: InvestigationDossier | None = None


class Report(ContractModel):
    id: UUID
    recipient_account_id: UUID
    transfer_id: UUID | None
    analysis_id: UUID | None
    narrative: str
    status: Literal["RECEIVED", "IN_REVIEW", "RESOLVED", "DISMISSED"]
    created_at: AwareDatetime
    resolution_reason: str | None


class RelatedReport(ContractModel):
    report_id: UUID
    rationale: str
    quotes: list[Quote]


class Investigation(ContractModel):
    run_id: UUID
    status: RunStatus
    related_reports: list[RelatedReport]
    missing_information: list[str]
    citation_warnings: list[str]
    dossier: InvestigationDossier | None = None


# Tracing, decisions, notices and audit


class TraceReference(ContractModel):
    code: str
    batch_id: UUID
    batch_label: str
    order_id: UUID
    partner_id: UUID
    partner_name: str
    issued_at: AwareDatetime


class AccessEvent(ContractModel):
    id: UUID
    batch_id: UUID
    partner_id: UUID
    action: Literal["READ", "EXPORT"]
    occurred_at: AwareDatetime


class Trace(ContractModel):
    status: Literal["MATCHED_SCOPE", "NO_MATCH", "NO_REFERENCE"]
    references: list[TraceReference]
    access_events: list[AccessEvent]
    candidate_customer_count: NonNegativeInt
    limitations: list[str]


class ReportDetail(ContractModel):
    report: Report
    analysis: Analysis | None
    trace: Trace


class Restriction(ContractModel):
    id: UUID
    recipient_account_id: UUID
    action: RestrictionAction
    status: Literal["ACTIVE", "REVOKED", "EXPIRED"]
    reason: str
    evidence_report_ids: list[UUID]
    created_at: AwareDatetime
    expires_at: AwareDatetime
    created_by: UUID
    revocation_reason: str | None


class Notice(ContractModel):
    id: UUID
    title: str
    body: str
    created_at: AwareDatetime
    read_at: AwareDatetime | None


class NoticePreview(ContractModel):
    batch_id: UUID
    source_report_id: UUID
    recipients: list[Actor]
    count: NonNegativeInt


class PublishResult(ContractModel):
    batch_id: UUID
    source_report_id: UUID
    recipient_count: NonNegativeInt
    created_count: NonNegativeInt


class AuditEvent(ContractModel):
    id: UUID
    actor_id: UUID | None
    actor_kind: Literal["CUSTOMER", "OPERATOR", "SYSTEM", "DEMO_CONTROL"]
    event_type: str
    target_type: str
    target_id: UUID | None
    created_at: AwareDatetime
    summary: str


# Errors


class ErrorDetail(ContractModel):
    code: str
    message: str
    request_id: str
    current_transfer: Transfer | SkipJsonSchema[None] = None
    assessment: RiskAssessment | SkipJsonSchema[None] = None


class ErrorEnvelope(ContractModel):
    error: ErrorDetail


# Lists


class RecipientList(Page[Recipient]):
    pass


class OrderList(Page[Order]):
    pass


class TransferList(Page[Transfer]):
    pass


class ReportList(Page[Report]):
    pass


class RestrictionList(Page[Restriction]):
    pass


class NoticeList(Page[Notice]):
    pass


class AuditEventList(Page[AuditEvent]):
    pass


# Requests


class CreateDemo(ContractModel):
    scenario: Scenario


class SelectActor(ContractModel):
    actor_id: UUID


class CreateTransfer(ContractModel):
    client_request_id: UUID
    sender_account_id: UUID
    recipient_account_id: UUID
    amount_vnd: Vnd


class ConfirmTransfer(ContractModel):
    acknowledged_assessment_id: OptionalId = None


class CreateReport(ContractModel):
    client_request_id: UUID
    recipient_account_id: UUID
    transfer_id: OptionalId = None
    analysis_id: OptionalId = None
    narrative: Note


class ReviewReport(ContractModel):
    status: Literal["IN_REVIEW", "RESOLVED", "DISMISSED"]
    reason: Note


class InvestigateReport(ContractModel):
    client_request_id: UUID


class ReviewHold(ContractModel):
    decision: Literal["APPROVE", "REJECT"]
    reason: Note


class CreateRestriction(ContractModel):
    recipient_account_id: UUID
    action: RestrictionAction
    reason: Note
    evidence_report_ids: UniqueList(UUID, min_items=1)
    expires_at: RequestTimestamp


class RevokeRestriction(ContractModel):
    reason: Note


class PublishNotice(ContractModel):
    batch_id: UUID
    title: Annotated[str, Field(min_length=1, max_length=120)]
    body: Annotated[str, Field(min_length=1, max_length=1000)]


_MODELS: tuple[type[BaseModel], ...] = (
    Actor,
    Account,
    Recipient,
    Bootstrap,
    Me,
    Refund,
    Order,
    RiskReason,
    RiskAssessment,
    Transfer,
    Quote,
    ModelEvidence,
    OfficialFacts,
    Analysis,
    Report,
    RelatedReport,
    Investigation,
    TraceReference,
    AccessEvent,
    Trace,
    ReportDetail,
    Restriction,
    Notice,
    NoticePreview,
    PublishResult,
    AuditEvent,
    RecipientList,
    OrderList,
    TransferList,
    ReportList,
    RestrictionList,
    NoticeList,
    AuditEventList,
    CreateDemo,
    SelectActor,
    CreateTransfer,
    ConfirmTransfer,
    CreateReport,
    ReviewReport,
    InvestigateReport,
    ReviewHold,
    CreateRestriction,
    RevokeRestriction,
    PublishNotice,
    InvestigationSource,
    InvestigationFinding,
    InvestigationActivity,
    InvestigationDossier,
)

# OpenAPI component name -> JSON schema generator, used by the contract drift test.
CONTRACT_SCHEMAS: dict[str, Callable[..., dict[str, Any]]] = {
    model.__name__: model.model_json_schema for model in _MODELS
}
CONTRACT_SCHEMAS["Error"] = ErrorEnvelope.model_json_schema
CONTRACT_SCHEMAS["InvestigationSignal"] = TypeAdapter(InvestigationSignal).json_schema
