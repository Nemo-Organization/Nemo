export type LogLevel = "success" | "warning" | "error";

export type LogMethod = "POST" | "GET";

export type ApiLog = {
  id: string;
  endpointId: string;
  endpointName: string;
  method: LogMethod;
  statusCode: number;
  level: LogLevel;
  latencyMs: number;
  message: string;
  /** ISO 8601 date-time string. */
  createdAt: string;
};
