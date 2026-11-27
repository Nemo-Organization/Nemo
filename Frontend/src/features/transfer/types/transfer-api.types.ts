import type { PaginatedResponse } from "@/lib/api-client";

// OpenAPI v1.3.0 DTOs for Customer endpoints (used by transfer feature).

export type ActorRoleDto = "CUSTOMER" | "OPERATOR";

export type ActorDto = {
  id: string;
  role: ActorRoleDto;
  display_name: string;
};

export type AccountDto = {
  id: string;
  display_name: string;
  bank_code: string;
  masked_identifier: string;
  balance_vnd: number;
  reserved_vnd: number;
  available_vnd: number;
};

export type MeDto = {
  sandbox_id: string;
  actor: ActorDto;
  accounts: AccountDto[];
  actor_csrf_token: string;
};

export type RecipientDto = {
  id: string;
  display_name: string;
  bank_code: string;
  masked_identifier: string;
  // TODO(BE): optional `active_restriction_action?: "WARN" | "HOLD" | null` if FE shows restriction badge on quick-recipient cards.
};

export type RecipientListDto = PaginatedResponse<RecipientDto>;

export type RefundStatusDto = "APPROVED" | "SETTLED";

export type RefundDto = {
  id: string;
  order_id: string;
  account_id: string;
  amount_vnd: number;
  status: RefundStatusDto;
  settled_at: string | null;
  // TODO(BE): missing `updated_at: string` (when status is APPROVED, settled_at is null so FE has no timestamp to display).
};

export type OrderDto = {
  id: string;
  order_reference: string;
  merchant_name: string;
  original_amount_vnd: number;
  return_fee_vnd: number | null;
  fee_source: string | null;
  fee_verified_at: string | null;
  refund: RefundDto | null;
};

export type OrderListDto = PaginatedResponse<OrderDto>;

export type RiskReasonCodeDto =
  | "AMOUNT_ABOVE_BASELINE"
  | "RECIPIENT_WARNING"
  | "RECIPIENT_HOLD";

export type RiskReasonDto = {
  code: RiskReasonCodeDto;
  message: string;
  restriction_id: string | null;
};

export type RiskDecisionDto = "ALLOW" | "WARN" | "HOLD";
export type BehaviorSignalDto = "NORMAL" | "ANOMALOUS" | "INSUFFICIENT_HISTORY";
export type RecipientSignalDto = "NONE" | "WARN" | "HOLD";

export type RiskAssessmentDto = {
  id: string;
  transfer_id: string;
  decision: RiskDecisionDto;
  behavior_signal: BehaviorSignalDto;
  recipient_signal: RecipientSignalDto;
  reasons: RiskReasonDto[];
  policy_version: string;
  assessed_at: string;
  expires_at: string;
};

export type TransferStatusDto =
  | "DRAFT"
  | "RISK_HELD"
  | "READY"
  | "SUCCEEDED"
  | "CANCELED"
  | "REJECTED"
  | "EXPIRED";

export type TransferDto = {
  id: string;
  sender_account_id: string;
  recipient: RecipientDto;
  amount_vnd: number;
  status: TransferStatusDto;
  reserved_amount_vnd: number;
  expires_at: string;
  created_at: string;
  completed_at: string | null;
  assessment: RiskAssessmentDto | null;
  review_reason: string | null;
  replayed: boolean;
};

export type TransferListDto = PaginatedResponse<TransferDto>;

export type CreateTransferRequest = {
  client_request_id: string;
  sender_account_id: string;
  recipient_account_id: string;
  amount_vnd: number;
};

export type ConfirmTransferRequest = {
  acknowledged_assessment_id?: string;
};

export type QuoteSourceDto = "IMAGE_TRANSCRIPTION" | "CUSTOMER_TEXT" | "REPORT";

export type QuoteDto = {
  source: QuoteSourceDto;
  text: string;
  report_id: string | null;
};

export type RequestedActionDto =
  | "PAY_FEE"
  | "PAY_PURCHASE"
  | "CONFIRM_TRANSFER"
  | "SHARE_SECRET"
  | "CONFIRM_LOGIN"
  | "OTHER"
  | "UNKNOWN";

export type AdditionalActionDto = Exclude<RequestedActionDto, "UNKNOWN">;
export type ClaimedTransferDirectionDto = "INCOMING" | "OUTGOING" | "UNKNOWN";

export type ModelEvidenceDto = {
  transcription: string;
  requested_action: RequestedActionDto;
  additional_actions?: AdditionalActionDto[];
  claimed_transfer_direction?: ClaimedTransferDirectionDto;
  claimed_purpose: string;
  quotes: QuoteDto[];
  extracted_references: string[];
  missing_information: string[];
};

export type OfficialFactsDto = {
  transfer_amount_vnd: number | null;
  direction: "OUTGOING" | "UNKNOWN";
  refund_amount_vnd: number | null;
  refund_status: "APPROVED" | "SETTLED" | "UNKNOWN";
  return_fee_vnd: number | null;
  fee_source: string | null;
  // TODO(BE): missing `order_reference?: string | null` and `order_amount_vnd?: number | null` for order cross-check card.
};

export type CustomerDossierSourceKindDto =
  | "CUSTOMER_TEXT"
  | "IMAGE_TRANSCRIPTION"
  | "TRANSFER"
  | "ORDER"
  | "REFUND";

export type CustomerDossierSourceDto = {
  id: string;
  kind: CustomerDossierSourceKindDto;
  resource_id: string | null;
  label: string;
  excerpt: string;
  observed_at: string | null;
};

export type DossierFindingRelationDto =
  | "SUPPORTS_CONCERN"
  | "COUNTERS_CONCERN"
  | "UNRESOLVED";

export type DossierSignalDto =
  | "CLAIMS_OFFICIAL_ROLE"
  | "URGENCY_PRESSURE"
  | "OFF_PLATFORM_CHANNEL"
  | "PAYEE_DIFFERS_FROM_SENDER"
  | "USES_ORDER_DETAILS"
  | "DISCOURAGES_VERIFICATION"
  | "OTHER";

export type CustomerDossierFindingDto = {
  id: string;
  statement: string;
  relation: DossierFindingRelationDto;
  source_ids: string[];
  signal?: DossierSignalDto | null;
};

export type CustomerDossierActivityDto = {
  step: number;
  tool: "get_customer_context";
  status: "SUCCEEDED" | "NOT_FOUND" | "DENIED" | "UNAVAILABLE";
  summary: string;
};

export type CustomerDossierDto = {
  version: "guardian-dossier-v1";
  sources: CustomerDossierSourceDto[];
  findings: CustomerDossierFindingDto[];
  activity: CustomerDossierActivityDto[];
  recommended_checks: string[];
  limitations: string[];
  citation_warnings: string[];
};

export type AnalysisStatusDto = "PENDING" | "SUCCEEDED" | "FAILED" | "TIMED_OUT";
export type AnalysisFindingDto = "MISMATCH" | "CONSISTENT" | "UNCERTAIN";

export type AnalysisDto = {
  id: string;
  status: AnalysisStatusDto;
  finding: AnalysisFindingDto;
  evidence: ModelEvidenceDto | null;
  official_facts: OfficialFactsDto;
  evidence_available: boolean;
  error_code: string | null;
  replayed: boolean;
  dossier?: CustomerDossierDto | null;
  // TODO(BE): missing `created_at: string` (FE displays analyzedAt timestamp).
  // TODO(BE): missing `GET /analyses` list endpoint to restore past analyses after page reload.
};

export type CreateAnalysisRequest = {
  client_request_id: string;
  transfer_id?: string;
  order_id?: string;
  text?: string;
  image?: File;
};

export type CustomerReportStatusDto =
  | "RECEIVED"
  | "IN_REVIEW"
  | "RESOLVED"
  | "DISMISSED";

export type CustomerReportDto = {
  id: string;
  recipient_account_id: string;
  transfer_id: string | null;
  analysis_id: string | null;
  narrative: string;
  status: CustomerReportStatusDto;
  created_at: string;
  resolution_reason: string | null;
  // TODO(BE): missing `category?: "SCAM_RECIPIENT" | "PHISHING_MESSAGE" | "FRAUD_ORDER"` (FE displays report category).
  // TODO(BE): missing `recipient?: RecipientDto` (or `recipient_display_name`) to avoid client-side join with GET /recipients.
};

export type CustomerReportListDto = PaginatedResponse<CustomerReportDto>;

export type CreateReportRequest = {
  client_request_id: string;
  recipient_account_id: string;
  transfer_id?: string;
  analysis_id?: string;
  narrative: string;
  // TODO(BE): missing `category` field in CreateReport schema.
};

export type NoticeDto = {
  id: string;
  title: string;
  body: string;
  created_at: string;
  read_at: string | null;
  // TODO(BE): missing `kind?: "RISK" | "REFUND" | "INFO"` for alert badge styling in AlertsList.
};

export type NoticeListDto = PaginatedResponse<NoticeDto>;
