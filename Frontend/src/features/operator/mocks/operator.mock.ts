import type {
  AudienceEntry,
  CaseFile,
  HoldItem,
  RecipientInfo,
  ReportItem,
} from "../types/operator.types";

// TODO: remove once operator API is ready.

const recipientBinh: RecipientInfo = { id: "rcp-002", name: "Trần Thị Bình", accountNumber: "0099 8877 6655" };
const recipientSaoMai: RecipientInfo = { id: "rcp-003", name: "Công ty TNHH Sao Mai", accountNumber: "0123 4567 8901" };

const audience = (reason: AudienceEntry["reason"], names: string[]): AudienceEntry[] =>
  names.map((customerName, index) => ({
    customerId: `cus-${reason === "hasDraft" ? "d" : "t"}${index + 1}`,
    customerName,
    reason,
  }));

const saoMaiCase: CaseFile = {
  evidence: {
    kind: "screenshot",
    fileName: "tin-nhan-chuyen-khoan.png",
    text: "Quý khách vui lòng chuyển cọc 5.000.000đ để giữ suất ưu đãi, mã tham chiếu REF-7731.",
    submittedAt: "2026-11-23T08:12:00Z",
    linkedDraftLabel: "Draft #102 – Thanh toán đơn hàng",
    linkedOrderLabel: "Order #5002",
  },
  traceMatches: [
    { id: "tm-1", reference: "REF-7731", recordType: "issuance", recordId: "ISS-20931", match: "exact", matchedAt: "2026-11-23T08:14:00Z" },
    { id: "tm-2", reference: "0123 4567 8901", recordType: "access", recordId: "ACC-88412", match: "partial", matchedAt: "2026-11-23T08:14:00Z" },
  ],
  recipient: recipientSaoMai,
  restriction: null,
  audience: [
    ...audience("transferredRecently", ["Lê Minh Châu", "Phạm Quốc Dũng", "Võ Thanh Hà"]),
    ...audience("hasDraft", ["Đặng Gia Huy"]),
  ],
};

const binhCase: CaseFile = {
  evidence: {
    kind: "text",
    text: "Người này nhắn tôi chuyển tiền gấp để nhận quà, không gặp mặt bao giờ.",
    submittedAt: "2026-11-22T15:40:00Z",
  },
  traceMatches: [],
  recipient: recipientBinh,
  restriction: { id: "rs-001", level: "WARN", reason: "Nhiều báo cáo trong 7 ngày.", createdAt: "2026-11-20T10:00:00Z" },
  audience: audience("transferredRecently", ["Ngô Bảo Anh", "Lý Hoàng Nam"]),
};

export const mockReports: ReportItem[] = [
  { id: "RPT-1001", type: "scamRecipient", status: "new", priority: "high", summary: "Khách báo người nhận yêu cầu cọc trước khi giao hàng.", createdAt: "2026-11-23T08:20:00Z", caseFile: saoMaiCase },
  { id: "RPT-1002", type: "phishingMessage", status: "inReview", priority: "medium", summary: "Tin nhắn mạo danh yêu cầu chuyển tiền gấp.", createdAt: "2026-11-22T15:45:00Z", caseFile: binhCase },
  { id: "RPT-1003", type: "fraudOrder", status: "resolved", priority: "low", summary: "Đơn hàng không giao sau khi thanh toán.", createdAt: "2026-11-20T09:05:00Z", caseFile: { ...binhCase, evidence: null, traceMatches: [] } },
  { id: "RPT-1004", type: "scamRecipient", status: "dismissed", priority: "low", summary: "Báo cáo trùng với RPT-1001.", createdAt: "2026-11-19T11:30:00Z", caseFile: { ...saoMaiCase, evidence: null } },
];

export const mockHolds: HoldItem[] = [
  {
    id: "HLD-2001", transferId: "TRF-1763900001", customerName: "Lê Minh Châu", amount: 24_000_000, status: "pending",
    heldAt: "2026-11-24T02:10:00Z", deadline: "2026-11-25T02:10:00Z",
    signals: [
      { code: "reportedRecipient", kind: "recipient" },
      { code: "highAmount", kind: "behavioral" },
      { code: "drainsBalance", kind: "behavioral" },
    ],
    caseFile: saoMaiCase,
  },
  {
    id: "HLD-2002", transferId: "TRF-1763900002", customerName: "Ngô Bảo Anh", amount: 21_500_000, status: "pending",
    heldAt: "2026-11-24T03:45:00Z", deadline: "2026-11-25T03:45:00Z",
    signals: [{ code: "newRecipient", kind: "recipient" }, { code: "highAmount", kind: "behavioral" }],
    caseFile: binhCase,
  },
  {
    id: "HLD-2003", transferId: "TRF-1763800003", customerName: "Võ Thanh Hà", amount: 30_000_000, status: "approved",
    heldAt: "2026-11-23T01:00:00Z", deadline: "2026-11-24T01:00:00Z",
    signals: [{ code: "highAmount", kind: "behavioral" }],
    caseFile: { ...binhCase, restriction: null },
  },
];

export const getReport = (id: string) => mockReports.find((r) => r.id === id);
export const getHold = (id: string) => mockHolds.find((h) => h.id === id);
