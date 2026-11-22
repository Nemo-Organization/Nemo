import { useTranslations } from "next-intl";

import { PageContainer } from "@/components/layout/page-container";
import { PageHeader } from "@/components/layout/page-header";
import {
  mockDailyActivity,
  mockPlanUsage,
  mockQuickLinks,
} from "../mocks/dashboard.mock";
import { OverviewChart } from "./overview-chart";
import { QuickLinks } from "./quick-links";
import { RecentLeadsSection } from "./recent-leads-section";
import { UsageOverviewCard } from "./usage-overview-card";

export function DashboardView() {
  const t = useTranslations("dashboard");
  const isEnterprise = mockPlanUsage.tier === "enterprise";

  // TODO: replace mock data with the dashboard service once the API exists.
  return (
    <PageContainer className="space-y-6">
      <PageHeader title={t("title")} description={t("description")} />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <OverviewChart
          activity={mockDailyActivity}
          className={isEnterprise ? "lg:col-span-3" : "lg:col-span-2"}
        />
        {!isEnterprise && <UsageOverviewCard planUsage={mockPlanUsage} />}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <QuickLinks links={mockQuickLinks} />
      </div>

      <RecentLeadsSection />
    </PageContainer>
  );
}
