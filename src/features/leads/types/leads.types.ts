export type Endpoint = { id: string; name: string };

export type Lead = {
  id: string;
  endpointId: string;
  endpointName: string;
  /** ISO 8601 date-time string. */
  createdAt: string;
};
