import { useTranslations } from "next-intl";

import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { mockEndpoints, mockLeads } from "../mocks/leads.mock";
import { LeadsTable } from "./leads-table";

export function LeadsView() {
  const t = useTranslations("leads");

  const activeEndpointCount = new Set(mockLeads.map((lead) => lead.endpointId))
    .size;
  const last24hCount = mockLeads.filter((lead) => {
    const diffMs =
      new Date("2026-11-22T00:00:00Z").getTime() -
      new Date(lead.createdAt).getTime();
    return diffMs <= 24 * 60 * 60 * 1000;
  }).length;

  // TODO: replace mock data with the leads service once the API exists.
  return (
    <PageContainer className="space-y-6">
      <PageHeader title={t("title")} description={t("description")} />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card className="py-0">
          <CardContent className="space-y-1 p-5">
            <p className="text-xs text-muted-foreground">{t("stats.total")}</p>
            <p className="text-2xl font-bold tracking-tight tabular-nums">
              {mockLeads.length}
            </p>
          </CardContent>
        </Card>
        <Card className="py-0">
          <CardContent className="space-y-1 p-5">
            <p className="text-xs text-muted-foreground">
              {t("stats.last24h")}
            </p>
            <p className="text-2xl font-bold tracking-tight text-primary tabular-nums">
              {last24hCount}
            </p>
          </CardContent>
        </Card>
        <Card className="py-0">
          <CardContent className="space-y-1 p-5">
            <p className="text-xs text-muted-foreground">
              {t("stats.activeEndpoints")}
            </p>
            <p className="text-2xl font-bold tracking-tight tabular-nums">
              {activeEndpointCount}
            </p>
          </CardContent>
        </Card>
      </div>

      <LeadsTable leads={mockLeads} endpoints={mockEndpoints} />
    </PageContainer>
  );
}
