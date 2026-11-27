"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { PaginationParams } from "@/lib/api-client";
import {
  assessTransfer,
  cancelTransfer,
  confirmTransfer,
  createAnalysis,
  createReport,
  createTransfer,
  getAnalysis,
  getMe,
  getTransfer,
  listNotifications,
  listOrders,
  listOwnReports,
  listRecipients,
  listTransfers,
} from "../services/transfer.service";
import type {
  ConfirmTransferRequest,
  CreateAnalysisRequest,
  CreateReportRequest,
  CreateTransferRequest,
} from "../types/transfer-api.types";

// Ready-to-wire TanStack Query hooks (TODO: connect in TransferView when BE is ready).

export const transferQueryKeys = {
  all: ["transfer"] as const,
  me: () => [...transferQueryKeys.all, "me"] as const,
  recipients: (params?: PaginationParams) =>
    [...transferQueryKeys.all, "recipients", params] as const,
  orders: (params?: PaginationParams) =>
    [...transferQueryKeys.all, "orders", params] as const,
  transfers: (params?: PaginationParams) =>
    [...transferQueryKeys.all, "transfers", params] as const,
  transfer: (id: string) => [...transferQueryKeys.all, "transfer", id] as const,
  analysis: (id: string) => [...transferQueryKeys.all, "analysis", id] as const,
  reports: (params?: PaginationParams) =>
    [...transferQueryKeys.all, "reports", params] as const,
  notifications: (params?: PaginationParams) =>
    [...transferQueryKeys.all, "notifications", params] as const,
};

export function useMeQuery(enabled = true) {
  return useQuery({
    queryKey: transferQueryKeys.me(),
    queryFn: getMe,
    enabled,
  });
}

export function useRecipientsQuery(params?: PaginationParams, enabled = true) {
  return useQuery({
    queryKey: transferQueryKeys.recipients(params),
    queryFn: () => listRecipients(params),
    enabled,
  });
}

export function useOrdersQuery(params?: PaginationParams, enabled = true) {
  return useQuery({
    queryKey: transferQueryKeys.orders(params),
    queryFn: () => listOrders(params),
    enabled,
  });
}

export function useTransfersQuery(params?: PaginationParams, enabled = true) {
  return useQuery({
    queryKey: transferQueryKeys.transfers(params),
    queryFn: () => listTransfers(params),
    enabled,
  });
}

export function useTransferQuery(transferId: string | null) {
  return useQuery({
    queryKey: transferQueryKeys.transfer(transferId ?? ""),
    queryFn: () => getTransfer(transferId!),
    enabled: Boolean(transferId),
  });
}

export function useAnalysisQuery(analysisId: string | null) {
  return useQuery({
    queryKey: transferQueryKeys.analysis(analysisId ?? ""),
    queryFn: () => getAnalysis(analysisId!),
    enabled: Boolean(analysisId),
  });
}

export function useOwnReportsQuery(params?: PaginationParams, enabled = true) {
  return useQuery({
    queryKey: transferQueryKeys.reports(params),
    queryFn: () => listOwnReports(params),
    enabled,
  });
}

export function useNotificationsQuery(params?: PaginationParams, enabled = true) {
  return useQuery({
    queryKey: transferQueryKeys.notifications(params),
    queryFn: () => listNotifications(params),
    enabled,
  });
}

export function useCreateTransferMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateTransferRequest) => createTransfer(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: transferQueryKeys.transfers() });
    },
  });
}

export function useAssessTransferMutation() {
  return useMutation({
    mutationFn: (transferId: string) => assessTransfer(transferId),
  });
}

export function useConfirmTransferMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      transferId,
      payload,
    }: {
      transferId: string;
      payload?: ConfirmTransferRequest;
    }) => confirmTransfer(transferId, payload),
    onSuccess: (transfer) => {
      void queryClient.invalidateQueries({ queryKey: transferQueryKeys.me() });
      void queryClient.invalidateQueries({ queryKey: transferQueryKeys.transfers() });
      queryClient.setQueryData(transferQueryKeys.transfer(transfer.id), transfer);
    },
  });
}

export function useCancelTransferMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (transferId: string) => cancelTransfer(transferId),
    onSuccess: (transfer) => {
      void queryClient.invalidateQueries({ queryKey: transferQueryKeys.me() });
      void queryClient.invalidateQueries({ queryKey: transferQueryKeys.transfers() });
      queryClient.setQueryData(transferQueryKeys.transfer(transfer.id), transfer);
    },
  });
}

export function useCreateAnalysisMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateAnalysisRequest) => createAnalysis(payload),
    onSuccess: (analysis) => {
      queryClient.setQueryData(transferQueryKeys.analysis(analysis.id), analysis);
    },
  });
}

export function useCreateReportMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateReportRequest) => createReport(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: transferQueryKeys.reports() });
    },
  });
}
