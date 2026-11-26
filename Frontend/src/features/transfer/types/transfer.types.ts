export type RiskLevel = "ALLOW" | "WARN" | "HOLD";

export type SignalKind = "recipient" | "behavioral";

// Maps to i18n key transfer.risk.signals.<code>
export type RiskSignal = { code: string; kind: SignalKind };

export type RiskResult = {
  transferId: string;
  level: RiskLevel;
  amount: number; // VND, positive integer
  recipientId: string;
  recipientSignals: RiskSignal[];
  behavioralSignals: RiskSignal[];
  holdDeadline?: string; // ISO datetime (HOLD only)
};

export type TransferStatus =
  | "awaiting_decision" // WARN: awaiting choice
  | "held" // HOLD: funds reserved
  | "completed"
  | "cancelled";

export type AccountBalance = {
  balance: number; // ledger balance
  held: number; // reserved funds
  available: number; // balance minus held funds
};

export type Recipient = {
  id: string;
  name: string;
  bankCode: string;
  accountNumber: string;
  flags: string[];
  restriction?: "WARN" | "HOLD";
};

export type Draft = { id: string; label: string; amount: number };

export type Order = {
  id: string;
  label: string;
  amount: number;
  feeVnd: number | null;
};

export type RefundStatus = "pending" | "approved" | "completed" | "rejected";

export type Refund = {
  id: string;
  orderId: string;
  amount: number;
  status: RefundStatus;
  updatedAt: string;
};

export type AlertKind = "risk" | "refund" | "info";

// Maps to i18n key transfer.alerts.items.<key>
export type AlertItem = {
  id: string;
  kind: AlertKind;
  key: string;
  createdAt: string;
};

export type AnalysisVerdict = "MISMATCH" | "CONSISTENT" | "UNCERTAIN";

export type AnalysisResult = {
  id: string;
  verdict: AnalysisVerdict;
  requestedAction: string;
  claimedPurpose: string;
  extractedReferences: string[];
  sourceExcerpts: string[];
  missingInfo: string[];
  orderComparison?: {
    orderLabel: string;
    orderAmount: number;
    feeVnd: number | null;
  };
  draftLabel?: string;
  fileName?: string;
  analyzedAt: string;
};

export type RecentTransferStatus = "completed" | "held" | "cancelled";

export type RecentTransfer = {
  id: string;
  recipientId: string;
  recipientName: string;
  accountNumber: string;
  amount: number;
  status: RecentTransferStatus;
  createdAt: string;
  holdDeadline?: string;
};

export type CustomerReportCategory =
  | "scamRecipient"
  | "phishingMessage"
  | "fraudOrder";

export type CustomerReportStatus =
  | "received"
  | "inReview"
  | "resolved"
  | "dismissed";

export type CustomerReport = {
  id: string;
  recipientId: string;
  recipientName: string;
  category: CustomerReportCategory;
  description: string;
  evidenceId?: string;
  status: CustomerReportStatus;
  createdAt: string;
};
