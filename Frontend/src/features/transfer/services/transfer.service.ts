import {
  apiClient,
  buildApiUrl,
  setCsrfToken,
  type PaginationParams,
} from "@/lib/api-client";
import { mockRecipients } from "../mocks/transfer.mock";
import type { Recipient } from "../types/transfer.types";
import type {
  AnalysisDto,
  ConfirmTransferRequest,
  CreateAnalysisRequest,
  CreateReportRequest,
  CreateTransferRequest,
  CustomerReportDto,
  CustomerReportListDto,
  MeDto,
  NoticeListDto,
  OrderListDto,
  RecipientListDto,
  RiskAssessmentDto,
  TransferDto,
  TransferListDto,
} from "../types/transfer-api.types";

// TODO: remove mock helper once TransferView switches to useRecipientsQuery().
export async function getTransferRecipients(): Promise<Recipient[]> {
  return mockRecipients;
}

// --- Customer API functions (ready to wire; UI still uses mocks) ---

export async function getMe(): Promise<MeDto> {
  const { data } = await apiClient.get<MeDto>("/me");
  setCsrfToken(data.actor_csrf_token);
  return data;
}

export async function listRecipients(
  params?: PaginationParams,
): Promise<RecipientListDto> {
  const { data } = await apiClient.get<RecipientListDto>("/recipients", { params });
  return data;
}

export async function listOrders(
  params?: PaginationParams,
): Promise<OrderListDto> {
  const { data } = await apiClient.get<OrderListDto>("/orders", { params });
  return data;
}

export async function listTransfers(
  params?: PaginationParams,
): Promise<TransferListDto> {
  const { data } = await apiClient.get<TransferListDto>("/transfers", { params });
  return data;
}

export async function getTransfer(transferId: string): Promise<TransferDto> {
  const { data } = await apiClient.get<TransferDto>(`/transfers/${transferId}`);
  return data;
}

export async function createTransfer(
  payload: CreateTransferRequest,
): Promise<TransferDto> {
  const { data } = await apiClient.post<TransferDto>("/transfers", payload);
  return data;
}

export async function assessTransfer(
  transferId: string,
): Promise<RiskAssessmentDto> {
  const { data } = await apiClient.post<RiskAssessmentDto>(
    `/transfers/${transferId}/assess`,
  );
  return data;
}

export async function confirmTransfer(
  transferId: string,
  payload: ConfirmTransferRequest = {},
): Promise<TransferDto> {
  const { data } = await apiClient.post<TransferDto>(
    `/transfers/${transferId}/confirm`,
    payload,
  );
  return data;
}

export async function cancelTransfer(transferId: string): Promise<TransferDto> {
  const { data } = await apiClient.post<TransferDto>(
    `/transfers/${transferId}/cancel`,
  );
  return data;
}

export async function createAnalysis(
  payload: CreateAnalysisRequest,
): Promise<AnalysisDto> {
  const form = new FormData();
  form.append("client_request_id", payload.client_request_id);
  if (payload.transfer_id) form.append("transfer_id", payload.transfer_id);
  if (payload.order_id) form.append("order_id", payload.order_id);
  if (payload.text) form.append("text", payload.text);
  if (payload.image) form.append("image", payload.image);

  const { data } = await apiClient.post<AnalysisDto>("/analyses", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function getAnalysis(analysisId: string): Promise<AnalysisDto> {
  const { data } = await apiClient.get<AnalysisDto>(`/analyses/${analysisId}`);
  return data;
}

export function getAnalysisEvidenceUrl(analysisId: string): string {
  return buildApiUrl(`/analyses/${analysisId}/evidence`);
}

export async function createReport(
  payload: CreateReportRequest,
): Promise<CustomerReportDto> {
  const { data } = await apiClient.post<CustomerReportDto>("/reports", payload);
  return data;
}

export async function listOwnReports(
  params?: PaginationParams,
): Promise<CustomerReportListDto> {
  const { data } = await apiClient.get<CustomerReportListDto>("/reports", { params });
  return data;
}

export async function listNotifications(
  params?: PaginationParams,
): Promise<NoticeListDto> {
  const { data } = await apiClient.get<NoticeListDto>("/notifications", { params });
  return data;
}

// TODO(BE): add listAnalyses() once GET /analyses is exposed in OpenAPI.
// TODO(BE): add markNotificationRead(id) once POST /notifications/{id}/read is exposed.
