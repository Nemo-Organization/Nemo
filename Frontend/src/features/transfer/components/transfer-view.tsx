"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { evaluateRisk } from "../lib/evaluate-risk";
import {
  mockAccount,
  mockDrafts,
  mockNotices,
  mockOrders,
  mockRecipients,
  mockRefunds,
} from "../mocks/transfer.mock";
import type {
  AccountBalance,
  RiskResult as RiskResultType,
  TransferStatus,
} from "../types/transfer.types";
import { BalanceSummary } from "./balance-summary";
import { NoticesList } from "./notices-list";
import { RefundContext } from "./refund-context";
import { RiskResult } from "./risk-result";
import { ScreenshotAnalysis } from "./screenshot-analysis";
import { TransferForm } from "./transfer-form";

export function TransferView() {
  const t = useTranslations("transfer");
  const [account, setAccount] = useState<AccountBalance>(mockAccount);
  const [risk, setRisk] = useState<RiskResultType | null>(null);
  const [status, setStatus] = useState<TransferStatus | null>(null);

  // Lock form while a transfer awaits decision or review.
  const isBusy = status === "awaiting_decision" || status === "held";

  const debit = (amount: number) =>
    setAccount((a) => ({
      balance: a.balance - amount,
      available: a.available - amount,
    }));

  const handleSubmit = ({ recipientId, amount }: { recipientId: string; amount: number }) => {
    const recipient = mockRecipients.find((r) => r.id === recipientId);
    if (!recipient) return;
    if (amount > account.available) {
      setRisk(null);
      setStatus(null);
      return; // TODO: show insufficient balance error from API.
    }

    const result = evaluateRisk(amount, recipient, account);
    setRisk(result);

    if (result.level === "ALLOW") {
      debit(amount);
      setStatus("completed");
    } else if (result.level === "WARN") {
      setStatus("awaiting_decision");
    } else {
      // HOLD reserves funds from available balance.
      setAccount((a) => ({ ...a, available: a.available - amount }));
      setStatus("held");
    }
  };

  const handleContinue = () => {
    if (!risk) return;
    debit(risk.amount);
    setStatus("completed");
  };

  const handleCancel = () => {
    if (!risk) return;
    if (status === "held") {
      setAccount((a) => ({ ...a, available: a.available + risk.amount }));
    }
    setStatus("cancelled");
  };

  return (
    <PageContainer className="space-y-6">
      <PageHeader title={t("title")} description={t("description")} />

      <BalanceSummary account={account} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="space-y-6">
          <TransferForm
            recipients={mockRecipients}
            disabled={isBusy}
            onSubmit={handleSubmit}
          />
          <ScreenshotAnalysis drafts={mockDrafts} orders={mockOrders} />
        </div>
        <RiskResult
          risk={risk}
          status={status}
          onContinue={handleContinue}
          onCancel={handleCancel}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <RefundContext refunds={mockRefunds} orders={mockOrders} />
        <NoticesList notices={mockNotices} />
      </div>
    </PageContainer>
  );
}
