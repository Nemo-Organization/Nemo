export type EndpointStatus = "active" | "paused";

export type EndpointItem = {
  id: string;
  name: string;
  slug: string;
  url: string;
  status: EndpointStatus;
  leadsCount: number;
  errorRate: number;
  /** ISO 8601 date-time string. */
  createdAt: string;
};
