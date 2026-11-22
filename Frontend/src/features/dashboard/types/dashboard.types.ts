export type DailyActivity = {
  /** ISO date (YYYY-MM-DD). */
  date: string;
  leads: number;
  errors: number;
};

export type ActivitySeries = "leads" | "errors";

export type PlanTier = "free" | "lite" | "pro" | "enterprise";

export type PlanUsage = {
  tier: PlanTier;
  tierLabel: string;
  leadsUsed: number;
  leadsLimit: number;
  daysUntilReset: number;
};

export type QuickLinkKey = "endpoints" | "leads" | "logs";

export type QuickLink = {
  key: QuickLinkKey;
  href: string;
};
