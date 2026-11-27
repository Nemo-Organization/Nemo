"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { PaginationParams } from "@/lib/api-client";
import {
  createOpsRestriction,
  getOpsReport,
  investigateOpsReport,
  listOpsAuditEvents,
  listOpsHolds,
  listOpsReports,
  listOpsRestrictions,
  previewOpsNotice,
  publishOpsNotices,
  reviewOpsHold,
  reviewOpsReport,
  revokeOpsRestriction,
  traceOpsReport,
} from "../services/operator.service";
import type {
  CreateRestrictionRequest,
  InvestigateReportRequest,
  PublishNoticeRequest,
  ReviewHoldRequest,
  ReviewReportRequest,
  RevokeRestrictionRequest,
} from "../types/operator-api.types";

// Ready-to-wire TanStack Query hooks (TODO: connect in operator views when BE is ready).

export const operatorQueryKeys = {
  all: ["operator"] as const,
  reports: (params?: PaginationParams) =>
    [...operatorQueryKeys.all, "reports", params] as const,
  report: (id: string) => [...operatorQueryKeys.all, "report", id] as const,
  trace: (id: string) => [...operatorQueryKeys.all, "trace", id] as const,
  holds: (params?: PaginationParams) =>
    [...operatorQueryKeys.all, "holds", params] as const,
  restrictions: (params?: PaginationParams & { recipient_account_id?: string }) =>
    [...operatorQueryKeys.all, "restrictions", params] as const,
  noticePreview: (reportId: string, batchId: string) =>
    [...operatorQueryKeys.all, "noticePreview", reportId, batchId] as const,
  auditEvents: (params?: PaginationParams) =>
    [...operatorQueryKeys.all, "auditEvents", params] as const,
};

export function useOpsReportsQuery(params?: PaginationParams, enabled = true) {
  return useQuery({
    queryKey: operatorQueryKeys.reports(params),
    queryFn: () => listOpsReports(params),
    enabled,
  });
}

export function useOpsReportQuery(reportId: string | null) {
  return useQuery({
    queryKey: operatorQueryKeys.report(reportId ?? ""),
    queryFn: () => getOpsReport(reportId!),
    enabled: Boolean(reportId),
  });
}

export function useOpsReportTraceQuery(reportId: string | null) {
  return useQuery({
    queryKey: operatorQueryKeys.trace(reportId ?? ""),
    queryFn: () => traceOpsReport(reportId!),
    enabled: Boolean(reportId),
  });
}

export function useOpsHoldsQuery(params?: PaginationParams, enabled = true) {
  return useQuery({
    queryKey: operatorQueryKeys.holds(params),
    queryFn: () => listOpsHolds(params),
    enabled,
  });
}

export function useOpsRestrictionsQuery(
  params?: PaginationParams & { recipient_account_id?: string },
  enabled = true,
) {
  return useQuery({
    queryKey: operatorQueryKeys.restrictions(params),
    queryFn: () => listOpsRestrictions(params),
    enabled,
  });
}

export function useOpsNoticePreviewQuery(
  reportId: string | null,
  batchId: string | null,
) {
  return useQuery({
    queryKey: operatorQueryKeys.noticePreview(reportId ?? "", batchId ?? ""),
    queryFn: () => previewOpsNotice(reportId!, batchId!),
    enabled: Boolean(reportId && batchId),
  });
}

export function useOpsAuditEventsQuery(params?: PaginationParams, enabled = true) {
  return useQuery({
    queryKey: operatorQueryKeys.auditEvents(params),
    queryFn: () => listOpsAuditEvents(params),
    enabled,
  });
}

export function useReviewOpsReportMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      reportId,
      payload,
    }: {
      reportId: string;
      payload: ReviewReportRequest;
    }) => reviewOpsReport(reportId, payload),
    onSuccess: (_data, { reportId }) => {
      void queryClient.invalidateQueries({ queryKey: operatorQueryKeys.reports() });
      void queryClient.invalidateQueries({ queryKey: operatorQueryKeys.report(reportId) });
    },
  });
}

export function useInvestigateOpsReportMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      reportId,
      payload,
    }: {
      reportId: string;
      payload: InvestigateReportRequest;
    }) => investigateOpsReport(reportId, payload),
    onSuccess: (_data, { reportId }) => {
      void queryClient.invalidateQueries({ queryKey: operatorQueryKeys.report(reportId) });
      void queryClient.invalidateQueries({ queryKey: operatorQueryKeys.trace(reportId) });
    },
  });
}

export function useReviewOpsHoldMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      transferId,
      payload,
    }: {
      transferId: string;
      payload: ReviewHoldRequest;
    }) => reviewOpsHold(transferId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: operatorQueryKeys.holds() });
    },
  });
}

export function useCreateOpsRestrictionMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateRestrictionRequest) =>
      createOpsRestriction(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: operatorQueryKeys.restrictions(),
      });
    },
  });
}

export function useRevokeOpsRestrictionMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      restrictionId,
      payload,
    }: {
      restrictionId: string;
      payload: RevokeRestrictionRequest;
    }) => revokeOpsRestriction(restrictionId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: operatorQueryKeys.restrictions(),
      });
    },
  });
}

export function usePublishOpsNoticesMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      reportId,
      payload,
    }: {
      reportId: string;
      payload: PublishNoticeRequest;
    }) => publishOpsNotices(reportId, payload),
    onSuccess: (_data, { reportId }) => {
      void queryClient.invalidateQueries({ queryKey: operatorQueryKeys.report(reportId) });
    },
  });
}
