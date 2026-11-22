import { useTranslations } from "next-intl";

import { LeadsTable, mockEndpoints, mockLeads } from "@/features/leads";

export function RecentLeadsSection() {
  const t = useTranslations("dashboard");

  // TODO: replace mock data with the 5 most recent leads from the leads service.
  return (
    <section className="space-y-4 pt-2">
      <h2 className="text-lg font-semibold tracking-tight text-foreground">
        {t("recentLeads")}
      </h2>
      <LeadsTable leads={mockLeads.slice(0, 5)} endpoints={mockEndpoints} />
    </section>
  );
}
