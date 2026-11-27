// Operator mocks are shaped by the operator UI, not the API contract.

export const REPORT_STATUSES = ["new", "inReview", "resolved", "dismissed"] as const;
export type ReportStatus = (typeof REPORT_STATUSES)[number];

export const HOLD_STATUSES = ["pending", "approved", "rejected"] as const;
export type HoldStatus = (typeof HOLD_STATUSES)[number];

export type ReportType = "scamRecipient" | "phishingMessage" | "fraudOrder";
export type Priority = "low" | "medium" | "high";
export type RestrictionLevel = "WARN" | "HOLD";

// ----- Shared by report and hold detail -----

export type RecipientAccount = {
  id: string;
  name: string;
  bankCode: string;
  maskedAccount: string;
};

export type EvidenceVerdict = "MISMATCH" | "UNCERTAIN" | "CONSISTENT";

export type Evidence = {
  fileName?: string; // screenshot; its text is a model transcription
  text: string;
  textSource: "transcription" | "customerText";
  submittedAt: string;
  linkedTransfer?: { amount: number; status: string }; // amount in VND
  linkedOrder?: string;
  customerAnalysis?: { verdict: EvidenceVerdict; summary: string };
};

export type Restriction = {
  id: string;
  level: RestrictionLevel;
  reason: string;
  createdAt: string;
  createdBy: string;
  expiresAt: string;
  evidenceReportIds: string[];
};

export type RestrictionHistoryEntry = {
  id: string;
  action: "created" | "revoked";
  level: RestrictionLevel;
  at: string;
  by: string;
  reason?: string;
};

// ----- Report detail -----

export type FindingRelation = "supportsConcern" | "countersConcern" | "unresolved";

export type SourceKind =
  | "CUSTOMER_TEXT"
  | "IMAGE_TRANSCRIPTION"
  | "REPORT"
  | "TRACE_REFERENCE"
  | "ACCESS_EVENT";

// Maps to i18n key operator.investigation.signal.<code>
export type FindingSignal =
  | "CLAIMS_OFFICIAL_ROLE"
  | "URGENCY_PRESSURE"
  | "OFF_PLATFORM_CHANNEL"
  | "PAYEE_DIFFERS_FROM_SENDER"
  | "USES_ORDER_DETAILS"
  | "DISCOURAGES_VERIFICATION"
  | "OTHER";

export type InvestigationFinding = {
  id: string;
  statement: string;
  relation: FindingRelation;
  signal?: FindingSignal;
  sources: { id: string; kind: SourceKind }[];
};

export type RelatedReport = { id: string; summary: string; status: ReportStatus };

export type TraceStatus = "MATCHED_SCOPE" | "NO_MATCH" | "NO_REFERENCE";

export type TraceResult = {
  status: TraceStatus;
  batch?: string;
  references: { code: string; batch: string; partner: string; issuedAt: string }[];
  accessEvents: {
    id: string;
    action: "READ" | "EXPORT";
    partner: string;
    occurredAt: string;
    beforeReport: boolean;
  }[];
  candidateCustomerCount: number;
};

export type InvestigationTool =
  | "read_case"
  | "search_related_reports"
  | "lookup_reference"
  | "get_batch_access_events";

export type InvestigationActivity = {
  step: number;
  tool: InvestigationTool;
  status: "SUCCEEDED" | "NOT_FOUND" | "DENIED" | "UNAVAILABLE";
  summary: string;
};

// What "Investigate with AI" returns for a report in the mock.
export type InvestigationResult = {
  modelCalls: number;
  toolCalls: number;
  findings: InvestigationFinding[];
  relatedReports: RelatedReport[];
  trace: TraceResult;
  recommendedChecks: string[];
  limitations: string[];
  missingInformation: string[];
  activity: InvestigationActivity[];
  citationWarningCount: number;
};

export type InvestigationRun = InvestigationResult & { runId: string; ranAt: string };

export type NoticeRecipient = {
  customerId: string;
  customerName: string;
  orderLabel: string;
};

// Notice for customers with orders in the traced batch.
export type NoticeDraft = {
  batch: string;
  title: string;
  body: string;
  recipients: NoticeRecipient[];
};

export type ReportCase = {
  reporter: { id: string; name: string };
  recipient: RecipientAccount;
  evidence: Evidence | null;
  restriction: Restriction | null;
  restrictionHistory: RestrictionHistoryEntry[];
  investigation: InvestigationResult;
  notice: NoticeDraft | null; // null when the trace finds no batch
};

export type ReportItem = {
  id: string;
  type: ReportType;
  status: ReportStatus;
  priority: Priority;
  summary: string;
  createdAt: string;
  detail: ReportCase;
};

// ----- Hold detail -----

export type RecipientSignalLevel = "HOLD" | "WARN" | "NONE";
export type BehaviorSignalLevel = "WARN" | "NONE" | "INSUFFICIENT_HISTORY";

// Snapshot at hold time; unaffected by later restriction changes.
export type HoldSignals = {
  recipient: {
    level: RecipientSignalLevel;
    summary: string;
    source?: { reportIds: string[]; restrictedAt: string };
  };
  behavior: { level: BehaviorSignalLevel; summary: string; note?: string };
};

export type HoldDecision = {
  action: "approved" | "rejected";
  by: string;
  at: string;
  reason: string;
};

export type HoldItem = {
  id: string;
  transferId: string;
  customerName: string;
  recipient: RecipientAccount;
  amount: number; // VND
  status: HoldStatus;
  heldAt: string;
  deadline: string;
  signals: HoldSignals;
  evidence: Evidence | null;
  restriction: Restriction | null;
  restrictionHistory: RestrictionHistoryEntry[];
  decision?: HoldDecision; // present once approved or rejected
};
