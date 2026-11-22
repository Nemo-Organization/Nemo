import { ROUTES } from "@/config/routes";
import type {
  DailyActivity,
  PlanUsage,
  QuickLink,
} from "../types/dashboard.types";

// Mock data. TODO: replace with data from the dashboard service when the API exists.

const FIRST_DAY_UTC = Date.UTC(2026, 9, 22); // 2026-10-22
const ONE_DAY_MS = 24 * 3600 * 1000;

// Deterministic (no Math.random) so server and client render the same output.
export const mockDailyActivity: DailyActivity[] = Array.from(
  { length: 30 },
  (_, dayIndex) => ({
    date: new Date(FIRST_DAY_UTC + dayIndex * ONE_DAY_MS)
      .toISOString()
      .slice(0, 10),
    leads: 40 + ((dayIndex * 37) % 55) + (dayIndex % 7 === 0 ? 30 : 0),
    errors: 2 + ((dayIndex * 11) % 9),
  }),
);

export const mockPlanUsage: PlanUsage = {
  tier: "free",
  tierLabel: "Free",
  leadsUsed: 642,
  leadsLimit: 1000,
  daysUntilReset: 9,
};

export const mockQuickLinks: QuickLink[] = [
  { key: "endpoints", href: ROUTES.endpoints },
  { key: "leads", href: ROUTES.leads },
  { key: "logs", href: ROUTES.logs },
];
