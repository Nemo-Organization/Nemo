import type { PaginatedResponse } from "@/lib/api-client";

// OpenAPI v1.3.0 DTOs for Operations endpoints (used by operator feature).

export type OpsActorDto = {
  id: string;
  role: "CUSTOMER" | "OPERATOR";
  display_name: string;
};

export type OpsRecipientDto = {
  id: string;
  display_name: string;
  bank_code: string;
  masked_identifier: string;
};

export type OpsReportStatusDto =
  | "RECEIVED"
  | "IN_REVIEW"
  | "RESOLVED"
  | "DISMISSED";

export type OpsReportDto = {
  id: string;
  recipient_account_id: string;
  transfer_id: string | null;
  analysis_id: string | null;
  narrative: string;
  status: OpsReportStatusDto;
  created_at: string;
  resolution_reason: string | null;
  // TODO(BE): missing `category?: "SCAM_RECIPIENT" | "PHISHING_MESSAGE" | "FRAUD_ORDER"` for report queue Type column.
  // TODO(BE): missing `priority?: "LOW" | "MEDIUM" | "HIGH"` for report queue Priority column.
  // TODO(BE): missing `recipient?: OpsRecipientDto` summary for report queue/header display.
};

export type OpsReportListDto = PaginatedResponse<OpsReportDto>;

export type ReviewReportRequest = {
  status: "IN_REVIEW" | "RESOLVED" | "DISMISSED";
  reason: string;
};

export type OpsQuoteDto = {
  source: "IMAGE_TRANSCRIPTION" | "CUSTOMER_TEXT" | "REPORT";
  text: string;
  report_id: string | null;
};

export type OpsDossierSourceKindDto =
  | "CUSTOMER_TEXT"
  | "IMAGE_TRANSCRIPTION"
  | "TRANSFER"
  | "ORDER"
  | "REFUND"
  | "REPORT"
  | "TRACE_REFERENCE"
  | "ACCESS_EVENT";

export type OpsDossierSourceDto = {
  id: string;
  kind: OpsDossierSourceKindDto;
  resource_id: string | null;
  label: string;
  excerpt: string;
  observed_at: string | null;
};

export type OpsDossierFindingRelationDto =
  | "SUPPORTS_CONCERN"
  | "COUNTERS_CONCERN"
  | "UNRESOLVED";

export type OpsDossierSignalDto =
  | "CLAIMS_OFFICIAL_ROLE"
  | "URGENCY_PRESSURE"
  | "OFF_PLATFORM_CHANNEL"
  | "PAYEE_DIFFERS_FROM_SENDER"
  | "USES_ORDER_DETAILS"
  | "DISCOURAGES_VERIFICATION"
  | "OTHER";

export type OpsDossierFindingDto = {
  id: string;
  statement: string;
  relation: OpsDossierFindingRelationDto;
  source_ids: string[];
  signal?: OpsDossierSignalDto | null;
};

export type OpsDossierActivityToolDto =
  | "get_customer_context"
  | "read_case"
  | "search_related_reports"
  | "lookup_reference"
  | "get_batch_access_events";

export type OpsDossierActivityDto = {
  step: number;
  tool: OpsDossierActivityToolDto;
  status: "SUCCEEDED" | "NOT_FOUND" | "DENIED" | "UNAVAILABLE";
  summary: string;
};

export type OpsDossierDto = {
  version: "guardian-dossier-v1";
  sources: OpsDossierSourceDto[];
  findings: OpsDossierFindingDto[];
  activity: OpsDossierActivityDto[];
  recommended_checks: string[];
  limitations: string[];
  citation_warnings: string[];
};

export type OpsAnalysisDto = {
  id: string;
  status: "PENDING" | "SUCCEEDED" | "FAILED" | "TIMED_OUT";
  finding: "MISMATCH" | "CONSISTENT" | "UNCERTAIN";
  evidence: {
    transcription: string;
    requested_action: string;
    additional_actions?: string[];
    claimed_transfer_direction?: "INCOMING" | "OUTGOING" | "UNKNOWN";
    claimed_purpose: string;
    quotes: OpsQuoteDto[];
    extracted_references: string[];
    missing_information: string[];
  } | null;
  official_facts: {
    transfer_amount_vnd: number | null;
    direction: "OUTGOING" | "UNKNOWN";
    refund_amount_vnd: number | null;
    refund_status: "APPROVED" | "SETTLED" | "UNKNOWN";
    return_fee_vnd: number | null;
    fee_source: string | null;
  };
  evidence_available: boolean;
  error_code: string | null;
  replayed: boolean;
  dossier?: OpsDossierDto | null;
  // TODO(BE): missing `file_name?: string | null` and `created_at: string` for EvidenceCard.
};

export type TraceReferenceDto = {
  code: string;
  batch_id: string;
  batch_label: string;
  order_id: string;
  partner_id: string;
  partner_name: string;
  issued_at: string;
};

export type AccessEventDto = {
  id: string;
  batch_id: string;
  partner_id: string;
  action: "READ" | "EXPORT";
  occurred_at: string;
  // TODO(BE): missing `partner_name: string` and `before_report?: boolean` (currently only partner_id UUID).
};

export type TraceStatusDto = "MATCHED_SCOPE" | "NO_MATCH" | "NO_REFERENCE";

export type TraceDto = {
  status: TraceStatusDto;
  references: TraceReferenceDto[];
  access_events: AccessEventDto[];
  candidate_customer_count: number;
  limitations: string[];
};

export type OpsReportDetailDto = {
  report: OpsReportDto;
  analysis: OpsAnalysisDto | null;
  trace: TraceDto;
  // TODO(BE): missing `reporter: OpsActorDto` (FE header shows Reporter name & ID).
  // TODO(BE): missing `recipient: OpsRecipientDto` (FE header & RecipientDecisionCard show recipient bank/name/masked account).
  // TODO(BE): missing `linked_transfer?: { id: string; amount_vnd: number; status: string } | null` and `linked_order_reference?: string | null`.
  // TODO(BE): missing `active_restriction?: RestrictionDto | null`, `restriction_history?: RestrictionDto[]`, and `latest_investigation?: InvestigationDto | null`.
};

export type RelatedReportDto = {
  report_id: string;
  rationale: string;
  quotes: OpsQuoteDto[];
  // TODO(BE): missing `summary: string` and `status: OpsReportStatusDto` for InvestigationCard related reports list.
};

export type InvestigateReportRequest = {
  client_request_id: string;
};

export type InvestigationDto = {
  run_id: string;
  status: "PENDING" | "SUCCEEDED" | "FAILED" | "TIMED_OUT";
  related_reports: RelatedReportDto[];
  missing_information: string[];
  citation_warnings: string[];
  dossier?: OpsDossierDto | null;
  // TODO(BE): missing `model_calls?: number`, `tool_calls?: number`, `ran_at?: string` for InvestigationCard header.
};

export type OpsRiskReasonDto = {
  code: "AMOUNT_ABOVE_BASELINE" | "RECIPIENT_WARNING" | "RECIPIENT_HOLD";
  message: string;
  restriction_id: string | null;
};

export type OpsRiskAssessmentDto = {
  id: string;
  transfer_id: string;
  decision: "ALLOW" | "WARN" | "HOLD";
  behavior_signal: "NORMAL" | "ANOMALOUS" | "INSUFFICIENT_HISTORY";
  recipient_signal: "NONE" | "WARN" | "HOLD";
  reasons: OpsRiskReasonDto[];
  policy_version: string;
  assessed_at: string;
  expires_at: string;
};

export type OpsTransferStatusDto =
  | "DRAFT"
  | "RISK_HELD"
  | "READY"
  | "SUCCEEDED"
  | "CANCELED"
  | "REJECTED"
  | "EXPIRED";

export type OpsHoldTransferDto = {
  id: string;
  sender_account_id: string;
  recipient: OpsRecipientDto;
  amount_vnd: number;
  status: OpsTransferStatusDto;
  reserved_amount_vnd: number;
  expires_at: string;
  created_at: string;
  completed_at: string | null;
  assessment: OpsRiskAssessmentDto | null;
  review_reason: string | null;
  replayed: boolean;
  // TODO(BE): missing `GET /ops/holds/{id}` endpoint for HoldDetailView (GET /transfers/{id} is customer-only).
  // TODO(BE): missing `customer_name: string` (FE holds table & detail show sender display name, not UUID).
  // TODO(BE): missing `decided_by_name?: string | null`, `decided_at?: string | null`, `linked_evidence?: OpsAnalysisDto | null`.
  // TODO(BE): missing `restriction_source?: { report_ids: string[]; restricted_at: string } | null`, `active_restriction`, `restriction_history`.
};

export type OpsHoldListDto = PaginatedResponse<OpsHoldTransferDto>;

export type ReviewHoldRequest = {
  decision: "APPROVE" | "REJECT";
  reason: string;
};

export type RestrictionActionDto = "WARN" | "HOLD";
export type RestrictionStatusDto = "ACTIVE" | "REVOKED" | "EXPIRED";

export type RestrictionDto = {
  id: string;
  recipient_account_id: string;
  action: RestrictionActionDto;
  status: RestrictionStatusDto;
  reason: string;
  evidence_report_ids: string[];
  created_at: string;
  expires_at: string;
  created_by: string;
  revocation_reason: string | null;
  // TODO(BE): missing `created_by_name?: string`, `revoked_at?: string | null`, `revoked_by?: string | null`, `revoked_by_name?: string | null`.
};

export type RestrictionListDto = PaginatedResponse<RestrictionDto>;

export type CreateRestrictionRequest = {
  recipient_account_id: string;
  action: RestrictionActionDto;
  reason: string;
  evidence_report_ids: string[];
  expires_at: string;
};

export type RevokeRestrictionRequest = {
  reason: string;
};

export type NoticePreviewDto = {
  batch_id: string;
  source_report_id: string;
  recipients: OpsActorDto[];
  count: number;
  // TODO(BE): missing `batch_label?: string`, `suggested_title?: string`, `suggested_body?: string`.
  // TODO(BE): missing `recipients[].order_reference?: string` and `already_published?: boolean`.
};

export type PublishNoticeRequest = {
  batch_id: string;
  title: string;
  body: string;
};

export type PublishResultDto = {
  batch_id: string;
  source_report_id: string;
  recipient_count: number;
  created_count: number;
};

export type AuditEventDto = {
  id: string;
  actor_id: string | null;
  actor_kind: "CUSTOMER" | "OPERATOR" | "SYSTEM" | "DEMO_CONTROL";
  event_type: string;
  target_type: string;
  target_id: string | null;
  created_at: string;
  summary: string;
};

export type AuditEventListDto = PaginatedResponse<AuditEventDto>;
