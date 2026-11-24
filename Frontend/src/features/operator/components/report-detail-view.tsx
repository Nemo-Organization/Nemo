"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { ArrowLeftIcon } from "@phosphor-icons/react/ssr";
import { toast } from "sonner";

import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ROUTES } from "@/config/routes";
import { Link } from "@/i18n/navigation";
import { useDateTimeFormatter } from "@/hooks/use-date-formatter";
import { cn } from "@/lib/utils";
import type { ReportItem, ReportStatus } from "../types/operator.types";
import { CaseSections } from "./case-sections";

export function ReportDetailView({ report }: { report: ReportItem }) {
  const t = useTranslations("operator");
  const formatDateTime = useDateTimeFormatter();
  const [status, setStatus] = useState<ReportStatus>(report.status);
  const isClosed = status === "resolved" || status === "dismissed";

  // TODO: call report status API.
  const changeStatus = (next: ReportStatus) => {
    setStatus(next);
    toast.success(t(`reports.actions.${next}Done`));
  };

  return (
    <PageContainer className="space-y-6">
      <Link
        href={ROUTES.operator}
        className={cn(buttonVariants({ variant: "ghost", size: "sm" }), "-ml-3")}
      >
        <ArrowLeftIcon data-icon="inline-start" aria-hidden />
        {t("back")}
      </Link>

      <PageHeader
        title={t("reports.detailTitle", { id: report.id })}
        description={report.summary}
      />

      <Card>
        <CardContent className="space-y-5 pt-6">
          <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
            <div>
              <dt className="text-xs text-muted-foreground">{t("reports.columns.type")}</dt>
              <dd>{t(`reports.type.${report.type}`)}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">{t("reports.columns.status")}</dt>
              <dd><Badge variant="secondary">{t(`reports.status.${status}`)}</Badge></dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">{t("reports.columns.priority")}</dt>
              <dd>{t(`reports.priority.${report.priority}`)}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">{t("reports.columns.createdAt")}</dt>
              <dd>{formatDateTime(report.createdAt)}</dd>
            </div>
          </dl>

          {isClosed ? (
            <p className="text-sm text-muted-foreground">{t("reports.closedNote")}</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {status === "new" && (
                <Button variant="outline" onClick={() => changeStatus("inReview")}>
                  {t("reports.actions.inReview")}
                </Button>
              )}
              <Button onClick={() => changeStatus("resolved")}>
                {t("reports.actions.resolved")}
              </Button>
              <Button variant="outline" onClick={() => changeStatus("dismissed")}>
                {t("reports.actions.dismissed")}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <CaseSections caseFile={report.caseFile} />
    </PageContainer>
  );
}
