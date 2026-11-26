"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { m } from "motion/react";
import {
  ArrowsLeftRightIcon,
  ClockCounterClockwiseIcon,
  FlagIcon,
  ReceiptIcon,
  SparkleIcon,
} from "@phosphor-icons/react/ssr";

import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import {
  Tabs,
  TabsContent,
  TabsIndicator,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
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

type TransferTab = "transfer" | "check" | "refund" | "history" | "reports";

const TAB_ITEMS: { key: TransferTab; icon: typeof ArrowsLeftRightIcon }[] = [
  { key: "transfer", icon: ArrowsLeftRightIcon },
  { key: "check", icon: SparkleIcon },
  { key: "refund", icon: ReceiptIcon },
  { key: "history", icon: ClockCounterClockwiseIcon },
  { key: "reports", icon: FlagIcon },
];

const tabIndex = (tab: TransferTab) => TAB_ITEMS.findIndex((item) => item.key === tab);

// Panels mount on tab change; slide in from the side the user moved toward.
// direction 0 = first render, no animation.
function PanelMotion({
  direction,
  children,
}: {
  direction: -1 | 0 | 1;
  children: React.ReactNode;
}) {
  return (
    <m.div
      initial={direction === 0 ? false : { opacity: 0, x: direction * 8 }}
      animate={{ opacity: 1, x: 0 }}
    >
      {children}
    </m.div>
  );
}

export function TransferView() {
  const t = useTranslations("transfer");
  const [activeTab, setActiveTab] = useState<TransferTab>("transfer");
  const [panelDirection, setPanelDirection] = useState<-1 | 0 | 1>(0);
  const [account, setAccount] = useState<AccountBalance>(mockAccount);
  const [risk, setRisk] = useState<RiskResultType | null>(null);
  const [status, setStatus] = useState<TransferStatus | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [evidences, setEvidences] = useState<AnalysisResult[]>([]);
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | undefined>();
  const [recentTransfers, setRecentTransfers] =
    useState<RecentTransfer[]>(mockRecentTransfers);
  const [reports, setReports] = useState<CustomerReport[]>(mockCustomerReports);

  // Lock form while a transfer awaits decision or review.
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
    if (!risk) return;
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
    if (!risk) return;
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

  const changeTab = (next: TransferTab) => {
    if (next === activeTab) return;
    setPanelDirection(tabIndex(next) > tabIndex(activeTab) ? 1 : -1);
    setActiveTab(next);
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
    setSelectedEvidenceId(undefined);
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
        {/* Scrolls horizontally on narrow screens instead of wrapping. */}
        <TabsList
          aria-label={t("tabs.label")}
          className="flex h-auto w-full justify-start gap-1 overflow-x-auto border border-border bg-muted/60 p-1 group-data-horizontal/tabs:h-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        >
          <TabsIndicator renderBeforeHydration className="bg-primary shadow-sm" />
          {TAB_ITEMS.map(({ key, icon: Icon }) => (
            <TabsTrigger
              key={key}
              value={key}
              className="h-9 gap-2 px-3 text-xs font-medium text-muted-foreground transition-colors duration-300 not-data-active:hover:bg-background/70 data-active:bg-transparent data-active:text-primary-foreground data-active:hover:text-primary-foreground dark:data-active:border-transparent dark:data-active:bg-transparent dark:data-active:text-primary-foreground dark:data-active:hover:text-primary-foreground"
            >
              <Icon
                className="size-4"
                weight={activeTab === key ? "fill" : "regular"}
                aria-hidden
              />
              <span>{t(`tabs.${key}`)}</span>
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="transfer" className="mt-0">
          <PanelMotion direction={panelDirection}>
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <TransferForm
                recipients={mockRecipients}
                availableBalance={account.available}
                disabled={isBusy}
                onSubmit={handleSubmitTransfer}
              />
              <RiskResult
                risk={risk}
                status={status}
                onContinue={handleContinue}
                onCancel={handleCancel}
              />
            </div>
          </PanelMotion>
        </TabsContent>

        <TabsContent value="check" className="mt-0">
          <PanelMotion direction={panelDirection}>
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <ScreenshotAnalysis
                drafts={mockDrafts}
                orders={mockOrders}
                onAnalyze={handleAnalyzeMessage}
              />
              <AnalysisResultCard
                result={analysis}
                onCreateReport={handleCreateReportFromAnalysis}
              />
            </div>
          </PanelMotion>
        </TabsContent>

        <TabsContent value="refund" className="mt-0">
          <PanelMotion direction={panelDirection}>
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <RefundContext refunds={mockRefunds} orders={mockOrders} />
              <AlertsList alerts={mockAlerts} />
            </div>
          </PanelMotion>
        </TabsContent>

        <TabsContent value="history" className="mt-0">
          <PanelMotion direction={panelDirection}>
            <RecentTransfers
              transfers={recentTransfers}
              onCancelHold={releaseHeldTransfer}
            />
          </PanelMotion>
        </TabsContent>

        <TabsContent value="reports" className="mt-0">
          <PanelMotion direction={panelDirection}>
            <ReportsPanel
              recipients={mockRecipients}
              reports={reports}
              evidences={evidences}
              defaultEvidenceId={selectedEvidenceId}
              onSubmitReport={handleSubmitReport}
            />
          </PanelMotion>
        </TabsContent>
      </Tabs>
    </PageContainer>
  );
}
