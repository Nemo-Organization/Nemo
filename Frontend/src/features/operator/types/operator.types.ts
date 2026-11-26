export const REPORT_STATUSES = ["new", "inReview", "resolved", "dismissed"] as const;
export type ReportStatus = (typeof REPORT_STATUSES)[number];

export const HOLD_STATUSES = ["pending", "approved", "rejected"] as const;
export type HoldStatus = (typeof HOLD_STATUSES)[number];

export type ReportType = "scamRecipient" | "phishingMessage" | "fraudOrder";
export type Priority = "low" | "medium" | "high";
export type RestrictionLevel = "WARN" | "HOLD";

export type Evidence = {
  kind: "screenshot" | "text";
  fileName?: string;
  text?: string;
  submittedAt: string;
  linkedDraftLabel?: string;
  linkedOrderLabel?: string;
};

// Evidence reference matched against issuance/access records.
export type TraceMatch = {
  id: string;
  reference: string;
  recordType: "issuance" | "access";
  recordId: string;
  match: "exact" | "partial";
  matchedAt: string;
};

export type RecipientInfo = { id: string; name: string; accountNumber: string };

export type Restriction = {
  id: string;
  level: RestrictionLevel;
  reason: string;
  createdAt: string;
};

export type AudienceReason = "transferredRecently" | "hasDraft";

export type AudienceEntry = {
  customerId: string;
  customerName: string;
  reason: AudienceReason;
};

export type CaseFile = {
  evidence: Evidence | null;
  traceMatches: TraceMatch[];
  recipient: RecipientInfo;
  restriction: Restriction | null;
  audience: AudienceEntry[];
};

export type ReportItem = {
  id: string;
  type: ReportType;
  status: ReportStatus;
  priority: Priority;
  summary: string;
  createdAt: string;
  caseFile: CaseFile;
};

// Maps to i18n key transfer.risk.signals.<code>
export type HoldSignal = { code: string; kind: "recipient" | "behavioral" };

export type HoldItem = {
  id: string;
  transferId: string;
  customerName: string;
  amount: number; // VND
  status: HoldStatus;
  heldAt: string;
  deadline: string;
  signals: HoldSignal[];
  caseFile: CaseFile;
};
