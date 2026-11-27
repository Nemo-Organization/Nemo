import type { InvestigationTool } from "../types/operator.types";

// Bounds shown to the operator before running an investigation.
export const INVESTIGATION_LIMITS = { seconds: 20, modelCalls: 3, toolCalls: 4 } as const;

export const OPS_INVESTIGATION_TOOLS: InvestigationTool[] = [
  "read_case",
  "search_related_reports",
  "lookup_reference",
  "get_batch_access_events",
];

// TODO: remove once the investigation API is ready.
export const MOCK_INVESTIGATION_DELAY_MS = 1400;

export const RESTRICTION_TTL_DAYS = 30;
