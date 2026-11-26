"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import { DataTable } from "@/components/data-table/data-table";
import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { cn } from "@/lib/utils";
import { mockHolds, mockReports } from "../mocks/operator.mock";
import { HOLD_STATUSES, REPORT_STATUSES } from "../types/operator.types";
import { holdColumns } from "./hold-columns";
import { QueueToolbar } from "./queue-toolbar";
import { reportColumns } from "./report-columns";

type QueueKey = "reports" | "holds";

function ReportsQueue() {
  const t = useTranslations("operator.reports");

  return (
    <DataTable
      columns={reportColumns}
      data={mockReports}
      renderToolbar={(table) => (
        <QueueToolbar
          table={table}
          filterPlaceholder={t("toolbar.filterPlaceholder")}
          statusTitle={t("toolbar.status")}
          statusOptions={REPORT_STATUSES.map((value) => ({ value, label: t(`status.${value}`) }))}
          resetLabel={t("toolbar.reset")}
        />
      )}
    />
  );
}

function HoldsQueue() {
  const t = useTranslations("operator.holds");

  return (
    <DataTable
      columns={holdColumns}
      data={mockHolds}
      renderToolbar={(table) => (
        <QueueToolbar
          table={table}
          filterPlaceholder={t("toolbar.filterPlaceholder")}
          statusTitle={t("toolbar.status")}
          statusOptions={HOLD_STATUSES.map((value) => ({ value, label: t(`status.${value}`) }))}
          resetLabel={t("toolbar.reset")}
        />
      )}
    />
  );
}

export function OperatorView() {
  const t = useTranslations("operator");
  const [queue, setQueue] = useState<QueueKey>("reports");

  const openReports = mockReports.filter((r) => r.status === "new" || r.status === "inReview").length;
  const pendingHolds = mockHolds.filter((h) => h.status === "pending").length;

  const tabs: { key: QueueKey; label: string; count: number }[] = [
    { key: "reports", label: t("queues.reports"), count: openReports },
    { key: "holds", label: t("queues.holds"), count: pendingHolds },
  ];

  return (
    <PageContainer className="space-y-6">
      <PageHeader title={t("title")} description={t("description")} />

      <div role="group" aria-label={t("queues.label")} className="inline-flex border border-border bg-background">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            aria-pressed={queue === tab.key}
            onClick={() => setQueue(tab.key)}
            className={cn(
              "flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors",
              queue === tab.key
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            {tab.label}
            <span className="tabular-nums text-xs opacity-80">{tab.count}</span>
          </button>
        ))}
      </div>

      {queue === "reports" ? <ReportsQueue /> : <HoldsQueue />}
    </PageContainer>
  );
}
