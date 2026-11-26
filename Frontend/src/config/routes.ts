// App route paths (pass to Link from @/i18n/navigation).
export const ROUTES = {
  home: "/",
  transfer: "/transfer",
  operator: "/operator",
} as const;

export const operatorReportRoute = (reportId: string) =>
  `/operator/reports/${reportId}`;

export const operatorHoldRoute = (holdId: string) =>
  `/operator/holds/${holdId}`;
