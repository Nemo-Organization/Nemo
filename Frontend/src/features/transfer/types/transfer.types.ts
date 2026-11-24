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
  balance: number;
  available: number; // balance minus held funds
};

export type Recipient = {
  id: string;
  name: string;
  accountNumber: string;
  flags: string[];
};

export type Draft = { id: string; label: string };
export type Order = { id: string; label: string; amount: number };

export type RefundStatus = "pending" | "approved" | "completed" | "rejected";

export type Refund = {
  id: string;
  orderId: string;
  amount: number;
  status: RefundStatus;
  updatedAt: string;
};

export type NoticeKind = "risk" | "refund" | "info";

// Maps to i18n key transfer.notices.items.<key>
export type Notice = {
  id: string;
  kind: NoticeKind;
  key: string;
  createdAt: string;
};
