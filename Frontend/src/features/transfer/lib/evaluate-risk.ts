import { HOLD_THRESHOLD, UNUSUAL_THRESHOLD } from "../constants/transfer.constants";
import type {
  AccountBalance,
  Recipient,
  RiskResult,
  RiskSignal,
} from "../types/transfer.types";

// Mock risk engine (TODO: replace with API). Keeps recipient & behavioral signals separate.
export function evaluateRisk(
  amount: number,
  recipient: Recipient,
  account: AccountBalance,
): RiskResult {
  const recipientSignals: RiskSignal[] = recipient.flags.map((code) => ({
    code,
    kind: "recipient",
  }));

  const behavioralSignals: RiskSignal[] = [];
  if (amount >= UNUSUAL_THRESHOLD)
    behavioralSignals.push({ code: "unusualAmount", kind: "behavioral" });
  if (amount > account.available * 0.8)
    behavioralSignals.push({ code: "drainsBalance", kind: "behavioral" });
  if (amount >= HOLD_THRESHOLD)
    behavioralSignals.push({ code: "highAmount", kind: "behavioral" });

  const level =
    recipient.restriction === "HOLD" || amount >= HOLD_THRESHOLD
      ? "HOLD"
      : recipient.restriction === "WARN" ||
          recipientSignals.length ||
          behavioralSignals.length
        ? "WARN"
        : "ALLOW";

  return {
    transferId: `TRF-${Date.now()}`,
    level,
    amount,
    recipientId: recipient.id,
    recipientSignals,
    behavioralSignals,
    holdDeadline:
      level === "HOLD"
        ? new Date(Date.now() + 15 * 60 * 1000).toISOString()
        : undefined,
  };
}
