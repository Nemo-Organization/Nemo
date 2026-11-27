"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  ArrowsLeftRightIcon,
  ClockCounterClockwiseIcon,
  FlagIcon,
  ReceiptIcon,
  SparkleIcon,
} from "@phosphor-icons/react/ssr";

import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { PageTabsList } from "@/components/layout/page-tabs";
import { TabPanelMotion } from "@/components/motion/tab-panel-motion";
import { Tabs, TabsContent } from "@/components/ui/tabs";
import { useTabParam } from "@/hooks/use-tab-param";
import { analyzeSuspiciousMessage } from "../lib/analyze-message";
import { evaluateRisk } from "../lib/evaluate-risk";
import {
  mockAccount,
  mockAlerts,
  mockCustomerReports,
  mockDrafts,
  mockOrders,
  mockRecentTransfers,
  mockRecipients,
  mockRefunds,
} from "../mocks/transfer.mock";
import type {
  AccountBalance,
  AnalysisResult,
  CustomerReport,
  CustomerReportCategory,
  RecentTransfer,
  RiskResult as RiskResultType,
  TransferStatus,
} from "../types/transfer.types";
import { AlertsList } from "./alerts-list";
import { AnalysisResultCard } from "./analysis-result";
import { BalanceSummary } from "./balance-summary";
import { RecentTransfers } from "./recent-transfers";
import { RefundContext } from "./refund-context";
import { ReportsPanel } from "./reports-panel";
import { RiskResult } from "./risk-result";
import { ScreenshotAnalysis } from "./screenshot-analysis";
import { TransferForm } from "./transfer-form";

const TABS = ["transfer", "check", "refund", "history", "reports"] as const;
type TransferTab = (typeof TABS)[number];

const TAB_ICONS = {
  transfer: ArrowsLeftRightIcon,
  check: SparkleIcon,
  refund: ReceiptIcon,
  history: ClockCounterClockwiseIcon,
  reports: FlagIcon,
} satisfies Record<TransferTab, unknown>;

export function TransferView() {
  const t = useTranslations("transfer");
  const {
    active: activeTab,
    setActive: changeTab,
    direction: panelDirection,
  } = useTabParam(TABS, { fallback: "transfer" });
  // TODO(API): swap mock state below for hooks in ../hooks/use-transfer-api.ts.
  const [account, setAccount] = useState<AccountBalance>(mockAccount);
  const [recipientId, setRecipientId] = useState("");
  const [amountInput, setAmountInput] = useState("");
  const [risk, setRisk] = useState<RiskResultType | null>(null);
  const [status, setStatus] = useState<TransferStatus | null>(null);
  const [shotFile, setShotFile] = useState<File | null>(null);
  const [shotText, setShotText] = useState("");
  const [shotDraftId, setShotDraftId] = useState("");
  const [shotOrderId, setShotOrderId] = useState("");
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [evidences, setEvidences] = useState<AnalysisResult[]>([]);
  const [selectedEvidenceId, setSelectedEvidenceId] = useState("");
  const [recentTransfers, setRecentTransfers] =
    useState<RecentTransfer[]>(mockRecentTransfers);
  const [reports, setReports] = useState<CustomerReport[]>(mockCustomerReports);

  // Lock form while awaiting decision or hold review.
  const isBusy = status === "awaiting_decision" || status === "held";

  const debit = (amount: number) =>
    setAccount((a) => ({
      ...a,
      balance: a.balance - amount,
      available: a.available - amount,
    }));

  const appendTransfer = (
    transferId: string,
    recipientId: string,
    amount: number,
    transferStatus: RecentTransfer["status"],
    holdDeadline?: string,
  ) => {
    const recipient = mockRecipients.find((r) => r.id === recipientId);
    if (!recipient) return;
    setRecentTransfers((prev) => [
      {
        id: transferId,
        recipientId: recipient.id,
        recipientName: recipient.name,
        accountNumber: recipient.accountNumber,
        amount,
        status: transferStatus,
        createdAt: new Date().toISOString(),
        holdDeadline,
      },
      ...prev,
    ]);
  };

  const handleSubmitTransfer = ({
    recipientId,
    amount,
  }: {
    recipientId: string;
    amount: number;
  }) => {
    const recipient = mockRecipients.find((r) => r.id === recipientId);
    if (!recipient || amount > account.available) return;

    const result = evaluateRisk(amount, recipient, account);
    setRisk(result);

    if (result.level === "ALLOW") {
      debit(amount);
      setStatus("completed");
      appendTransfer(result.transferId, recipientId, amount, "completed");
    } else if (result.level === "WARN") {
      setStatus("awaiting_decision");
    } else {
      // HOLD reserves funds from available balance.
      setAccount((a) => ({
        ...a,
        held: a.held + amount,
        available: a.available - amount,
      }));
      setStatus("held");
      appendTransfer(
        result.transferId,
        recipientId,
        amount,
        "held",
        result.holdDeadline,
      );
    }
  };

  const handleContinue = () => {
    if (!risk || status !== "awaiting_decision" || risk.amount > account.available) return;
    debit(risk.amount);
    setStatus("completed");
    appendTransfer(risk.transferId, risk.recipientId, risk.amount, "completed");
  };

  const releaseHeldTransfer = (transferId: string) => {
    const target = recentTransfers.find(
      (item) => item.id === transferId && item.status === "held",
    );
    if (!target) return;

    setAccount((a) => ({
      ...a,
      held: Math.max(0, a.held - target.amount),
      available: a.available + target.amount,
    }));
    setRecentTransfers((prev) =>
      prev.map((item) =>
        item.id === transferId ? { ...item, status: "cancelled" } : item,
      ),
    );
    if (risk?.transferId === transferId) {
      setStatus("cancelled");
    }
  };

  const handleCancel = () => {
    if (!risk || (status !== "awaiting_decision" && status !== "held")) return;
    if (status === "held") {
      releaseHeldTransfer(risk.transferId);
      return;
    }
    setStatus("cancelled");
    appendTransfer(risk.transferId, risk.recipientId, risk.amount, "cancelled");
  };

  const handleAnalyzeMessage = ({
    fileName,
    text,
    draftId,
    orderId,
  }: {
    fileName?: string;
    text: string;
    draftId: string;
    orderId: string;
  }) => {
    const draft = mockDrafts.find((d) => d.id === draftId);
    const order = mockOrders.find((o) => o.id === orderId);
    const result = analyzeSuspiciousMessage({ text, fileName, draft, order });
    setAnalysis(result);
    setEvidences((prev) => [result, ...prev]);
  };

  const handleCreateReportFromAnalysis = (item: AnalysisResult) => {
    setSelectedEvidenceId(item.id);
    changeTab("reports");
  };

  const handleSubmitReport = ({
    recipientId,
    category,
    description,
    evidenceId,
  }: {
    recipientId: string;
    category: CustomerReportCategory;
    description: string;
    evidenceId?: string;
  }) => {
    const recipient = mockRecipients.find((r) => r.id === recipientId);
    if (!recipient) return;
    setReports((prev) => [
      {
        id: `RPT-${Date.now().toString().slice(-4)}`,
        recipientId: recipient.id,
        recipientName: recipient.name,
        category,
        description,
        evidenceId,
        status: "received",
        createdAt: new Date().toISOString(),
      },
      ...prev,
    ]);
    setSelectedEvidenceId("");
  };

  return (
    <PageContainer className="space-y-6">
      <PageHeader title={t("title")} description={t("description")} />

      <BalanceSummary account={account} />

      <Tabs
        value={activeTab}
        onValueChange={(value) => changeTab(value as TransferTab)}
        className="space-y-5"
      >
        <PageTabsList
          label={t("tabs.label")}
          active={activeTab}
          items={TABS.map((value) => ({
            value,
            label: t(`tabs.${value}`),
            icon: TAB_ICONS[value],
          }))}
        />

        <TabsContent value="transfer" className="mt-0">
          <TabPanelMotion direction={panelDirection}>
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <TransferForm
                recipients={mockRecipients}
                recipientId={recipientId}
                amount={amountInput}
                availableBalance={account.available}
                disabled={isBusy}
                onRecipientChange={setRecipientId}
                onAmountChange={setAmountInput}
                onSubmit={handleSubmitTransfer}
              />
              <RiskResult
                risk={risk}
                status={status}
                onContinue={handleContinue}
                onCancel={handleCancel}
              />
            </div>
          </TabPanelMotion>
        </TabsContent>

        <TabsContent value="check" className="mt-0">
          <TabPanelMotion direction={panelDirection}>
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <ScreenshotAnalysis
                drafts={mockDrafts}
                orders={mockOrders}
                file={shotFile}
                text={shotText}
                draftId={shotDraftId}
                orderId={shotOrderId}
                onFileChange={setShotFile}
                onTextChange={setShotText}
                onDraftChange={setShotDraftId}
                onOrderChange={setShotOrderId}
                onAnalyze={handleAnalyzeMessage}
              />
              <AnalysisResultCard
                result={analysis}
                onCreateReport={handleCreateReportFromAnalysis}
              />
            </div>
          </TabPanelMotion>
        </TabsContent>

        <TabsContent value="refund" className="mt-0">
          <TabPanelMotion direction={panelDirection}>
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <RefundContext refunds={mockRefunds} orders={mockOrders} />
              <AlertsList alerts={mockAlerts} />
            </div>
          </TabPanelMotion>
        </TabsContent>

        <TabsContent value="history" className="mt-0">
          <TabPanelMotion direction={panelDirection}>
            <RecentTransfers
              transfers={recentTransfers}
              onCancelHold={releaseHeldTransfer}
            />
          </TabPanelMotion>
        </TabsContent>

        <TabsContent value="reports" className="mt-0">
          <TabPanelMotion direction={panelDirection}>
            <ReportsPanel
              recipients={mockRecipients}
              reports={reports}
              evidences={evidences}
              evidenceId={selectedEvidenceId}
              onEvidenceChange={setSelectedEvidenceId}
              onSubmitReport={handleSubmitReport}
            />
          </TabPanelMotion>
        </TabsContent>
      </Tabs>
    </PageContainer>
  );
}
