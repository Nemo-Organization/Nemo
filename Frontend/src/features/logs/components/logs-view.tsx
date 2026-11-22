import { useTranslations } from "next-intl";

import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { mockLogs } from "../mocks/logs.mock";
import { LogsTable } from "./logs-table";

export function LogsView() {
  const t = useTranslations("logs");

  const totalRequests = mockLogs.length;
  const errorCount = mockLogs.filter((log) => log.level === "error").length;
  const successCount = mockLogs.filter((log) => log.level === "success").length;
  const successRate =
    totalRequests > 0 ? Math.round((successCount / totalRequests) * 100) : 0;
  const avgLatency =
    totalRequests > 0
      ? Math.round(
          mockLogs.reduce((sum, log) => sum + log.latencyMs, 0) / totalRequests,
        )
      : 0;

  // TODO: replace mock data with the logs service once the API exists.
  return (
    <PageContainer className="space-y-6">
      <PageHeader title={t("title")} description={t("description")} />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="py-0">
          <CardContent className="space-y-1 p-5">
            <p className="text-xs text-muted-foreground">
              {t("stats.totalRequests")}
            </p>
            <p className="text-2xl font-bold tracking-tight tabular-nums">
              {totalRequests}
            </p>
          </CardContent>
        </Card>
        <Card className="py-0">
          <CardContent className="space-y-1 p-5">
            <p className="text-xs text-muted-foreground">
              {t("stats.successRate")}
            </p>
            <p className="text-2xl font-bold tracking-tight text-primary tabular-nums">
              {successRate}%
            </p>
          </CardContent>
        </Card>
        <Card className="py-0">
          <CardContent className="space-y-1 p-5">
            <p className="text-xs text-muted-foreground">{t("stats.errors")}</p>
            <p className="text-2xl font-bold tracking-tight text-destructive tabular-nums">
              {errorCount}
            </p>
          </CardContent>
        </Card>
        <Card className="py-0">
          <CardContent className="space-y-1 p-5">
            <p className="text-xs text-muted-foreground">
              {t("stats.avgLatency")}
            </p>
            <p className="text-2xl font-bold tracking-tight tabular-nums">
              {avgLatency}ms
            </p>
          </CardContent>
        </Card>
      </div>

      <LogsTable logs={mockLogs} />
    </PageContainer>
  );
}
