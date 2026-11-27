"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  ArrowLeftIcon,
  GavelIcon,
  MagnifyingGlassIcon,
  MegaphoneIcon,
} from "@phosphor-icons/react/ssr";
import { toast } from "sonner";

import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { PageTabsList } from "@/components/layout/page-tabs";
import { TabPanelMotion } from "@/components/motion/tab-panel-motion";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent } from "@/components/ui/tabs";
import { ROUTES } from "@/config/routes";
import { Link } from "@/i18n/navigation";
import { useDateTimeFormatter } from "@/hooks/use-date-formatter";
import { useTabParam } from "@/hooks/use-tab-param";
import { cn } from "@/lib/utils";
import { useMockInvestigation } from "../hooks/use-mock-investigation";
import { useRecipientRestriction } from "../hooks/use-recipient-restriction";
import type { ReportItem, ReportStatus } from "../types/operator.types";
import { EvidenceCard } from "./evidence-card";
import { InvestigationCard } from "./investigation-card";
import { RecipientDecisionCard } from "./recipient-decision-card";
import { ReportNoticeCard } from "./report-notice-card";
import { ReportReviewActions, type ReviewAction } from "./report-review-actions";
import { ReportStatusBadge } from "./report-status-badge";

const TABS = ["investigate", "decision", "notice"] as const;
type DetailTab = (typeof TABS)[number];

const TAB_ICONS = {
  investigate: MagnifyingGlassIcon,
  decision: GavelIcon,
  notice: MegaphoneIcon,
} satisfies Record<DetailTab, unknown>;

export function ReportDetailView({
  report,
  initialTab,
}: {
  report: ReportItem;
  initialTab?: string;
}) {
  const t = useTranslations("operator");
  const formatDateTime = useDateTimeFormatter();
  const { active, setActive, direction } = useTabParam(TABS, {
    fallback: "investigate",
    serverValue: initialTab,
  });
  const { detail } = report;

  // TODO(API): wire useOpsReportQuery / mutations in ../hooks/use-operator-api.ts.
  // Keep state here so it survives tab unmounts.
  const [status, setStatus] = useState<ReportStatus>(report.status);
  const investigation = useMockInvestigation(detail.investigation);
  const restriction = useRecipientRestriction({
    restriction: detail.restriction,
    history: detail.restrictionHistory,
    evidenceReportIds: [report.id],
  });
  const [noticePublished, setNoticePublished] = useState(false);

  // TODO: call report status API.
  const handleReview = (next: ReviewAction) => {
    setStatus(next);
    toast.success(t(`reports.actions.${next}Done`));
  };

  // TODO: call notice publish API.
  const handlePublish = () => {
    if (!detail.notice || !investigation.run || status !== "resolved" || noticePublished) {
      return;
    }
    setNoticePublished(true);
    toast.success(t("notice.published", { count: detail.notice.recipients.length }));
  };

  return (
    <PageContainer className="space-y-6">
      <Link
        href={{ pathname: ROUTES.operator, query: { queue: "reports" } }}
        className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "-ml-3")}
      >
        <ArrowLeftIcon data-icon="inline-start" aria-hidden />
        {t("back")}
      </Link>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <PageHeader
          title={t("reports.detailTitle", { id: report.id })}
          description={report.summary}
        />
        <ReportReviewActions status={status} onReview={handleReview} />
      </div>

      <Card>
        <CardContent>
          <dl className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-0.5">
              <dt className="text-xs text-muted-foreground">{t("reports.fields.recipient")}</dt>
              <dd className="font-medium">
                {detail.recipient.name} · {detail.recipient.bankCode}{" "}
                {detail.recipient.maskedAccount}
              </dd>
            </div>
            <div className="space-y-0.5">
              <dt className="text-xs text-muted-foreground">{t("reports.fields.reporter")}</dt>
              <dd className="font-medium">
                {detail.reporter.name}{" "}
                <span className="font-normal text-muted-foreground">({detail.reporter.id})</span>
              </dd>
            </div>
            <div className="space-y-0.5">
              <dt className="text-xs text-muted-foreground">{t("reports.fields.status")}</dt>
              <dd>
                <ReportStatusBadge status={status} />
              </dd>
            </div>
            <div className="space-y-0.5">
              <dt className="text-xs text-muted-foreground">{t("reports.fields.createdAt")}</dt>
              <dd className="font-medium">{formatDateTime(report.createdAt)}</dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      <Tabs
        value={active}
        onValueChange={(value) => setActive(value as DetailTab)}
        className="space-y-5"
      >
        <PageTabsList
          label={t("reports.tabs.label")}
          active={active}
          items={TABS.map((value) => ({
            value,
            label: t(`reports.tabs.${value}`),
            icon: TAB_ICONS[value],
          }))}
        />

        <TabsContent value="investigate" className="mt-0">
          <TabPanelMotion direction={direction}>
            <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-2">
              <div className="lg:sticky lg:top-6">
                <EvidenceCard evidence={detail.evidence} context="report" />
              </div>
              <InvestigationCard
                run={investigation.run}
                running={investigation.running}
                onRun={investigation.start}
              />
            </div>
          </TabPanelMotion>
        </TabsContent>

        <TabsContent value="decision" className="mt-0">
          <TabPanelMotion direction={direction}>
            <RecipientDecisionCard
              recipient={detail.recipient}
              restriction={restriction.restriction}
              history={restriction.history}
              onCreate={restriction.create}
              onRevoke={restriction.revoke}
            />
          </TabPanelMotion>
        </TabsContent>

        <TabsContent value="notice" className="mt-0">
          <TabPanelMotion direction={direction}>
            <ReportNoticeCard
              notice={detail.notice}
              investigated={investigation.run !== null}
              status={status}
              published={noticePublished}
              onPublish={handlePublish}
            />
          </TabPanelMotion>
        </TabsContent>
      </Tabs>
    </PageContainer>
  );
}
