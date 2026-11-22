/**
 * Central place for route paths. Use these instead of hard-coding strings so
 * renaming a route only needs one change. Pass them to `Link` from
 * `@/i18n/navigation` (locale prefix is added automatically).
 */
export const ROUTES = {
  home: "/",
  endpoints: "/endpoints",
  leads: "/leads",
  logs: "/logs",
  upgrade: "/upgrade",
} as const;

export const leadDetailRoute = (leadId: string) => `/leads/${leadId}`;

export const endpointLeadsRoute = (endpointId: string) =>
  `/endpoints/${endpointId}/leads`;
