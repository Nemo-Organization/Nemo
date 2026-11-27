import {
  apiClient,
  buildApiUrl,
  type PaginationParams,
} from "@/lib/api-client";
import type {
  AuditEventListDto,
  CreateRestrictionRequest,
  InvestigateReportRequest,
  InvestigationDto,
  NoticePreviewDto,
  OpsHoldListDto,
  OpsHoldTransferDto,
  OpsReportDetailDto,
  OpsReportDto,
  OpsReportListDto,
  PublishNoticeRequest,
  PublishResultDto,
  RestrictionDto,
  RestrictionListDto,
  ReviewHoldRequest,
  ReviewReportRequest,
  RevokeRestrictionRequest,
  TraceDto,
} from "../types/operator-api.types";

// --- Operations API functions (ready to wire; UI still uses mocks) ---

export async function listOpsReports(
  params?: PaginationParams,
): Promise<OpsReportListDto> {
  const { data } = await apiClient.get<OpsReportListDto>("/ops/reports", { params });
  return data;
}

export async function getOpsReport(reportId: string): Promise<OpsReportDetailDto> {
  const { data } = await apiClient.get<OpsReportDetailDto>(
    `/ops/reports/${reportId}`,
  );
  return data;
}

export async function reviewOpsReport(
  reportId: string,
  payload: ReviewReportRequest,
): Promise<OpsReportDto> {
  const { data } = await apiClient.patch<OpsReportDto>(
    `/ops/reports/${reportId}`,
    payload,
  );
  return data;
}

export async function investigateOpsReport(
  reportId: string,
  payload: InvestigateReportRequest,
): Promise<InvestigationDto> {
  const { data } = await apiClient.post<InvestigationDto>(
    `/ops/reports/${reportId}/investigate`,
    payload,
  );
  return data;
}

export async function traceOpsReport(reportId: string): Promise<TraceDto> {
  const { data } = await apiClient.get<TraceDto>(`/ops/reports/${reportId}/trace`);
  return data;
}

export async function listOpsHolds(
  params?: PaginationParams,
): Promise<OpsHoldListDto> {
  const { data } = await apiClient.get<OpsHoldListDto>("/ops/holds", { params });
  return data;
}

export async function reviewOpsHold(
  transferId: string,
  payload: ReviewHoldRequest,
): Promise<OpsHoldTransferDto> {
  const { data } = await apiClient.post<OpsHoldTransferDto>(
    `/ops/transfers/${transferId}/review`,
    payload,
  );
  return data;
}

export async function listOpsRestrictions(
  params?: PaginationParams & {
    // TODO(BE): add ?recipient_account_id filter on GET /ops/recipient-restrictions.
    recipient_account_id?: string;
  },
): Promise<RestrictionListDto> {
  const { data } = await apiClient.get<RestrictionListDto>(
    "/ops/recipient-restrictions",
    { params },
  );
  return data;
}

export async function createOpsRestriction(
  payload: CreateRestrictionRequest,
): Promise<RestrictionDto> {
  const { data } = await apiClient.post<RestrictionDto>(
    "/ops/recipient-restrictions",
    payload,
  );
  return data;
}

export async function revokeOpsRestriction(
  restrictionId: string,
  payload: RevokeRestrictionRequest,
): Promise<RestrictionDto> {
  const { data } = await apiClient.post<RestrictionDto>(
    `/ops/recipient-restrictions/${restrictionId}/revoke`,
    payload,
  );
  return data;
}

export async function previewOpsNotice(
  reportId: string,
  batchId: string,
): Promise<NoticePreviewDto> {
  const { data } = await apiClient.get<NoticePreviewDto>(
    `/ops/reports/${reportId}/notice-preview`,
    { params: { batch_id: batchId } },
  );
  return data;
}

export async function publishOpsNotices(
  reportId: string,
  payload: PublishNoticeRequest,
): Promise<PublishResultDto> {
  const { data } = await apiClient.post<PublishResultDto>(
    `/ops/reports/${reportId}/notices`,
    payload,
  );
  return data;
}

export async function listOpsAuditEvents(
  params?: PaginationParams,
): Promise<AuditEventListDto> {
  const { data } = await apiClient.get<AuditEventListDto>("/ops/audit-events", {
    params,
  });
  return data;
}

export function getOpsEvidenceUrl(analysisId: string): string {
  return buildApiUrl(`/analyses/${analysisId}/evidence`);
}

// TODO(BE): add getOpsHold(id) once GET /ops/holds/{id} is added to OpenAPI.
// TODO(BE): add listOpsInvestigations(reportId) once GET /ops/reports/{id}/investigations is added.
