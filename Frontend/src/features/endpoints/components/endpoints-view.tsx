"use client";

import { useTranslations } from "next-intl";
import { PlusIcon } from "@phosphor-icons/react/ssr";
import { toast } from "sonner";

import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { mockEndpointItems } from "../mocks/endpoints.mock";
import { EndpointsTable } from "./endpoints-table";

export function EndpointsView() {
  const t = useTranslations("endpoints");

  const activeCount = mockEndpointItems.filter(
    (endpoint) => endpoint.status === "active",
  ).length;
  const totalLeads = mockEndpointItems.reduce(
    (sum, endpoint) => sum + endpoint.leadsCount,
    0,
  );

  // TODO: replace mock data and toast with the endpoints service once the API exists.
  const handleCreate = () => toast.info(t("actions.createMock"));

  return (
    <PageContainer className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <PageHeader title={t("title")} description={t("description")} />
        <Button onClick={handleCreate} className="w-fit">
          <PlusIcon data-icon="inline-start" />
          {t("actions.create")}
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card className="py-0">
          <CardContent className="space-y-1 p-5">
            <p className="text-xs text-muted-foreground">{t("stats.total")}</p>
            <p className="text-2xl font-bold tracking-tight tabular-nums">
              {mockEndpointItems.length}
            </p>
          </CardContent>
        </Card>
        <Card className="py-0">
          <CardContent className="space-y-1 p-5">
            <p className="text-xs text-muted-foreground">{t("stats.active")}</p>
            <p className="text-2xl font-bold tracking-tight text-primary tabular-nums">
              {activeCount}
            </p>
          </CardContent>
        </Card>
        <Card className="py-0">
          <CardContent className="space-y-1 p-5">
            <p className="text-xs text-muted-foreground">
              {t("stats.leadsCaptured")}
            </p>
            <p className="text-2xl font-bold tracking-tight tabular-nums">
              {totalLeads.toLocaleString("en-US")}
            </p>
          </CardContent>
        </Card>
      </div>

      <EndpointsTable endpoints={mockEndpointItems} />
    </PageContainer>
  );
}
