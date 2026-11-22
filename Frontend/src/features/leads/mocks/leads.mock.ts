import type { Endpoint, Lead } from "../types/leads.types";

// Mock data. TODO: replace with data from the leads service when the API exists.

export const mockEndpoints: Endpoint[] = [
  { id: "ep_1", name: "Contact Form" },
  { id: "ep_2", name: "Newsletter Signup" },
  { id: "ep_3", name: "Landing Page" },
  { id: "ep_4", name: "Webinar Registration" },
];

export const mockLeads: Lead[] = [
  { id: "ld_8f3a21", endpointId: "ep_1", endpointName: "Contact Form", createdAt: "2026-11-21T21:12:00Z" },
  { id: "ld_7c1b94", endpointId: "ep_2", endpointName: "Newsletter Signup", createdAt: "2026-11-21T19:45:00Z" },
  { id: "ld_62de07", endpointId: "ep_3", endpointName: "Landing Page", createdAt: "2026-11-21T16:30:00Z" },
  { id: "ld_51a9c3", endpointId: "ep_1", endpointName: "Contact Form", createdAt: "2026-11-21T14:05:00Z" },
  { id: "ld_40b8f1", endpointId: "ep_4", endpointName: "Webinar Registration", createdAt: "2026-11-21T08:18:00Z" },
  { id: "ld_39e4d2", endpointId: "ep_3", endpointName: "Landing Page", createdAt: "2026-11-20T22:40:00Z" },
  { id: "ld_28c7a9", endpointId: "ep_2", endpointName: "Newsletter Signup", createdAt: "2026-11-20T18:15:00Z" },
  { id: "ld_17f5e4", endpointId: "ep_1", endpointName: "Contact Form", createdAt: "2026-11-20T11:50:00Z" },
  { id: "ld_06a2b8", endpointId: "ep_4", endpointName: "Webinar Registration", createdAt: "2026-11-19T19:22:00Z" },
  { id: "ld_95d1c6", endpointId: "ep_3", endpointName: "Landing Page", createdAt: "2026-11-19T09:05:00Z" },
];
