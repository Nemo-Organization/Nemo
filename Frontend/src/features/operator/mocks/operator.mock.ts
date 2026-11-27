import type {
  HoldItem,
  HoldSignals,
  RecipientAccount,
  ReportCase,
  ReportItem,
  Restriction,
  RestrictionHistoryEntry,
  TraceResult,
} from "../types/operator.types";

// TODO: remove once operator API is ready. Shaped by the operator UI.

// ----- Shared recipients and restrictions -----

const saoMaiRecipient: RecipientAccount = { id: "rcp-003", name: "Công ty TNHH Sao Mai", bankCode: "ACB", maskedAccount: "••••8901" };
const binhRecipient: RecipientAccount = { id: "rcp-002", name: "Trần Thị Bình", bankCode: "VCB", maskedAccount: "••••6655" };

const saoMaiHoldReason = "Hai báo cáo độc lập về yêu cầu đặt cọc/phí trước khi giao hàng hoặc hoàn tiền.";
const saoMaiRestriction: Restriction = {
  id: "rs-0991", level: "HOLD", reason: saoMaiHoldReason,
  createdAt: "2026-11-21T03:00:00Z", createdBy: "OPS", expiresAt: "2026-12-21T03:00:00Z",
  evidenceReportIds: ["RPT-0991", "RPT-0994"],
};
const saoMaiHistory: RestrictionHistoryEntry[] = [
  { id: "rh-0991", action: "created", level: "HOLD", at: "2026-11-21T03:00:00Z", by: "OPS", reason: saoMaiHoldReason },
];

const binhWarnReason = "Nhiều báo cáo trong 7 ngày.";
const binhRestriction: Restriction = {
  id: "rs-0978", level: "WARN", reason: binhWarnReason,
  createdAt: "2026-11-20T10:00:00Z", createdBy: "OPS", expiresAt: "2026-12-20T10:00:00Z",
  evidenceReportIds: ["RPT-0978"],
};
const binhHistory: RestrictionHistoryEntry[] = [
  { id: "rh-0978", action: "created", level: "WARN", at: "2026-11-20T10:00:00Z", by: "OPS", reason: binhWarnReason },
];

const noTrace: TraceResult = { status: "NO_REFERENCE", references: [], accessEvents: [], candidateCustomerCount: 0 };

const rpt1001: ReportCase = {
  reporter: { id: "cus-linh", name: "Nguyễn Thùy Linh" },
  recipient: saoMaiRecipient,
  evidence: {
    fileName: "tin-nhan-chuyen-khoan.png",
    text: "Chi ung giup em 20k phi thu hoi, ben kho moi tra 500k don SHOP-4502. Ma tra soat A-017.",
    textSource: "transcription",
    submittedAt: "2026-11-25T07:12:00Z",
    linkedTransfer: { amount: 20_000, status: "CANCELED" },
    linkedOrder: "SHOP-4502",
    customerAnalysis: {
      verdict: "MISMATCH",
      summary: "Yêu cầu PAY_FEE 20.000 ₫ để nhận hoàn tiền 500.000 ₫; phí trả hàng chính thức 0 ₫.",
    },
  },
  restriction: saoMaiRestriction,
  restrictionHistory: saoMaiHistory,
  investigation: {
    modelCalls: 3,
    toolCalls: 2,
    findings: [
      { id: "f1", relation: "supportsConcern", signal: "USES_ORDER_DETAILS", statement: "Bằng chứng trích mã A-017, khớp chính xác hồ sơ phát hành thuộc BATCH_A.", sources: [{ id: "S1", kind: "IMAGE_TRANSCRIPTION" }, { id: "S2", kind: "TRACE_REFERENCE" }] },
      { id: "f2", relation: "supportsConcern", statement: "PARTNER_A có lượt READ với BATCH_A lúc 24/11 09:14, trước khi khách hàng nhận tin nhắn.", sources: [{ id: "S3", kind: "ACCESS_EVENT" }] },
      { id: "f3", relation: "countersConcern", statement: "Lượt READ phù hợp quyền truy cập hỗ trợ hoàn tiền của PARTNER_A; không có lượt EXPORT.", sources: [{ id: "S3", kind: "ACCESS_EVENT" }] },
      { id: "f4", relation: "unresolved", statement: "Không xác định được ảnh là bản gốc hay bản chuyển tiếp; không thể quy trách nhiệm cho đối tác.", sources: [{ id: "S1", kind: "IMAGE_TRANSCRIPTION" }] },
    ],
    relatedReports: [
      { id: "RPT-0991", summary: "Cùng người nhận, yêu cầu đặt cọc kèm mã tham chiếu REF-7731.", status: "resolved" },
      { id: "RPT-0994", summary: "Cùng người nhận, mạo danh bộ phận hoàn tiền, yêu cầu phí xử lý.", status: "resolved" },
    ],
    trace: {
      status: "MATCHED_SCOPE",
      batch: "BATCH_A",
      references: [{ code: "A-017", batch: "BATCH_A", partner: "PARTNER_A", issuedAt: "2026-11-18T03:00:00Z" }],
      accessEvents: [{ id: "ae-1", action: "READ", partner: "PARTNER_A", occurredAt: "2026-11-24T02:14:00Z", beforeReport: true }],
      candidateCustomerCount: 3,
    },
    recommendedChecks: [
      "Đối chiếu ảnh gốc với bản chép trước khi dựa vào mã A-017.",
      "Xác minh với PARTNER_A mục đích lượt READ lô BATCH_A.",
      "Cân nhắc thông báo phòng ngừa cho khách hàng có đơn trong BATCH_A.",
    ],
    limitations: [
      "Mô hình chỉ đọc dữ liệu được cấp quyền. Không có nhật ký bên ngoài; không thể phát hiện xâm nhập khi không có dữ liệu truy cập.",
      "Khớp mã chỉ thu hẹp phạm vi, không chứng minh đối tác làm lộ dữ liệu. Ảnh có thể đã được chuyển tiếp; một lượt READ hợp lệ không phải bằng chứng rò rỉ.",
    ],
    missingInformation: [],
    activity: [
      { step: 1, tool: "lookup_reference", status: "SUCCEEDED", summary: "A-017 → BATCH_A · PARTNER_A" },
      { step: 2, tool: "get_batch_access_events", status: "SUCCEEDED", summary: "1 lượt READ · 0 lượt EXPORT" },
    ],
    citationWarningCount: 1,
  },
  notice: {
    batch: "BATCH_A",
    title: "Cảnh báo yêu cầu phí để nhận hoàn tiền",
    body: "Thông tin đơn hàng của bạn có thể đã bị dùng trong tin nhắn lừa đảo. Không chuyển phí để nhận hoàn tiền và không làm theo hướng dẫn chuyển tiền qua tin nhắn.",
    recipients: [
      { customerId: "cus-linh", customerName: "Nguyễn Thùy Linh", orderLabel: "SHOP-4502" },
      { customerId: "cus-an", customerName: "Trần Minh An", orderLabel: "SHOP-4507" },
      { customerId: "cus-binh", customerName: "Lê Thanh Bình", orderLabel: "SHOP-4511" },
    ],
  },
};

const rpt1002: ReportCase = {
  reporter: { id: "cus-baoanh", name: "Ngô Bảo Anh" },
  recipient: binhRecipient,
  evidence: {
    text: "Người này nhắn tôi chuyển tiền gấp để nhận quà, không gặp mặt bao giờ.",
    textSource: "customerText",
    submittedAt: "2026-11-22T15:40:00Z",
    customerAnalysis: {
      verdict: "UNCERTAIN",
      summary: "Tin nhắn thúc giục chuyển tiền nhưng không có giao dịch hay đơn hàng liên kết để đối chiếu.",
    },
  },
  restriction: binhRestriction,
  restrictionHistory: binhHistory,
  investigation: {
    modelCalls: 2,
    toolCalls: 2,
    findings: [
      { id: "f1", relation: "supportsConcern", signal: "URGENCY_PRESSURE", statement: "Tin nhắn yêu cầu chuyển tiền gấp để nhận quà.", sources: [{ id: "S1", kind: "CUSTOMER_TEXT" }] },
      { id: "f2", relation: "unresolved", statement: "Không có giao dịch hay đơn hàng liên kết để kiểm tra người gửi.", sources: [{ id: "S1", kind: "CUSTOMER_TEXT" }] },
    ],
    relatedReports: [
      { id: "RPT-0978", summary: "Cùng người nhận, hứa tặng quà nếu chuyển phí nhận thưởng.", status: "resolved" },
    ],
    trace: noTrace,
    recommendedChecks: [
      "Hỏi khách hàng kênh liên lạc và ảnh chụp tin nhắn gốc.",
      "Xem các giao dịch gần đây tới người nhận này.",
    ],
    limitations: ["Không có mã tham chiếu nên không thể truy vết lô dữ liệu."],
    missingInformation: ["Ảnh chụp tin nhắn gốc.", "Giao dịch hoặc đơn hàng liên quan."],
    activity: [
      { step: 1, tool: "read_case", status: "SUCCEEDED", summary: "Đọc báo cáo gốc và văn bản khách hàng gửi" },
      { step: 2, tool: "search_related_reports", status: "SUCCEEDED", summary: "1 báo cáo cùng người nhận" },
    ],
    citationWarningCount: 0,
  },
  notice: null,
};

const rpt1003: ReportCase = {
  reporter: { id: "cus-nam", name: "Lý Hoàng Nam" },
  recipient: binhRecipient,
  evidence: null,
  restriction: binhRestriction,
  restrictionHistory: binhHistory,
  investigation: {
    modelCalls: 1,
    toolCalls: 1,
    findings: [],
    relatedReports: [],
    trace: noTrace,
    recommendedChecks: ["Yêu cầu khách hàng bổ sung bằng chứng về đơn hàng."],
    limitations: ["Báo cáo không có bằng chứng đính kèm."],
    missingInformation: ["Bằng chứng về đơn hàng hoặc tin nhắn."],
    activity: [{ step: 1, tool: "read_case", status: "SUCCEEDED", summary: "Đọc báo cáo gốc · không có bằng chứng đính kèm" }],
    citationWarningCount: 0,
  },
  notice: null,
};

const rpt1004: ReportCase = {
  reporter: { id: "cus-huy", name: "Đặng Gia Huy" },
  recipient: saoMaiRecipient,
  evidence: null,
  restriction: saoMaiRestriction,
  restrictionHistory: saoMaiHistory,
  investigation: {
    modelCalls: 2,
    toolCalls: 2,
    findings: [
      { id: "f1", relation: "unresolved", statement: "Nội dung trùng với RPT-1001; không có bằng chứng mới.", sources: [{ id: "S1", kind: "REPORT" }] },
    ],
    relatedReports: [
      { id: "RPT-1001", summary: "Cùng người nhận, yêu cầu ứng phí để nhận hoàn tiền.", status: "new" },
    ],
    trace: noTrace,
    recommendedChecks: ["Gộp xử lý cùng RPT-1001."],
    limitations: ["Báo cáo không có bằng chứng đính kèm."],
    missingInformation: [],
    activity: [
      { step: 1, tool: "read_case", status: "SUCCEEDED", summary: "Đọc báo cáo gốc · không có bằng chứng đính kèm" },
      { step: 2, tool: "search_related_reports", status: "SUCCEEDED", summary: "1 báo cáo trùng nội dung" },
    ],
    citationWarningCount: 0,
  },
  notice: null,
};

export const mockReports: ReportItem[] = [
  { id: "RPT-1001", type: "scamRecipient", status: "new", priority: "high", summary: "Khách hàng báo người nhận yêu cầu ứng phí để nhận hoàn tiền.", createdAt: "2026-11-25T07:12:00Z", detail: rpt1001 },
  { id: "RPT-1002", type: "phishingMessage", status: "inReview", priority: "medium", summary: "Tin nhắn mạo danh yêu cầu chuyển tiền gấp.", createdAt: "2026-11-22T15:45:00Z", detail: rpt1002 },
  { id: "RPT-1003", type: "fraudOrder", status: "resolved", priority: "low", summary: "Đơn hàng không giao sau khi thanh toán.", createdAt: "2026-11-20T09:05:00Z", detail: rpt1003 },
  { id: "RPT-1004", type: "scamRecipient", status: "dismissed", priority: "low", summary: "Báo cáo trùng với RPT-1001.", createdAt: "2026-11-19T11:30:00Z", detail: rpt1004 },
];

// ----- Hold detail mocks -----

const saoMaiHoldSignal: HoldSignals["recipient"] = {
  level: "HOLD",
  summary: "Người nhận có hạn chế HOLD đang hiệu lực, đã được xác minh.",
  source: { reportIds: ["RPT-0991", "RPT-0994"], restrictedAt: "2026-11-21T03:00:00Z" },
};

export const mockHolds: HoldItem[] = [
  {
    id: "HLD-2001",
    transferId: "7c1e4b2a-93f0-4d1c-8e6a-5b0f2c3da90b",
    customerName: "Lê Hoài An",
    recipient: saoMaiRecipient,
    amount: 150_000,
    status: "pending",
    heldAt: "2026-11-25T07:37:00Z",
    deadline: "2026-11-25T07:52:00Z",
    signals: {
      recipient: saoMaiHoldSignal,
      behavior: {
        level: "INSUFFICIENT_HISTORY",
        summary: "Chưa đủ 5 giao dịch đã tất toán trong 30 ngày để đánh giá hành vi.",
        note: "Tín hiệu người nhận vẫn được đánh giá độc lập.",
      },
    },
    evidence: null,
    restriction: saoMaiRestriction,
    restrictionHistory: saoMaiHistory,
  },
  {
    id: "HLD-2002",
    transferId: "3f9a0d71-2c4e-4b8a-9d15-6e7b8c2f41d6",
    customerName: "Ngô Bảo Anh",
    recipient: saoMaiRecipient,
    amount: 2_500_000,
    status: "pending",
    heldAt: "2026-11-25T07:55:00Z",
    deadline: "2026-11-25T08:10:00Z",
    signals: {
      recipient: saoMaiHoldSignal,
      behavior: {
        level: "WARN",
        summary: "Số tiền gấp 6 lần trung vị 30 ngày (420.000 ₫) và trên 2.000.000 ₫.",
        note: "Bất thường hành vi tự nó không dẫn tới HOLD.",
      },
    },
    evidence: {
      text: "Bên bán hẹn giao hàng hôm nay nếu tôi chuyển đủ tiền trước, có gửi mã đơn SHOP-4520.",
      textSource: "customerText",
      submittedAt: "2026-11-25T07:54:00Z",
      linkedOrder: "SHOP-4520",
      customerAnalysis: {
        verdict: "UNCERTAIN",
        summary: "Tin nhắn nêu mã đơn nhưng chưa có số tiền hay phí chính thức để đối chiếu.",
      },
    },
    restriction: saoMaiRestriction,
    restrictionHistory: saoMaiHistory,
  },
  {
    id: "HLD-2003",
    transferId: "b52e8c10-7d3a-4f6e-a1c9-0e4d5f6a7c38",
    customerName: "Võ Thanh Hà",
    recipient: saoMaiRecipient,
    amount: 300_000,
    status: "approved",
    heldAt: "2026-11-24T02:00:00Z",
    deadline: "2026-11-24T02:15:00Z",
    signals: {
      recipient: saoMaiHoldSignal,
      behavior: {
        level: "NONE",
        summary: "Số tiền nằm trong khoảng thường gặp của 30 ngày gần nhất.",
      },
    },
    evidence: null,
    restriction: saoMaiRestriction,
    restrictionHistory: saoMaiHistory,
    decision: {
      action: "approved",
      by: "OPS",
      at: "2026-11-24T02:07:00Z",
      reason: "Khách hàng xác nhận qua kênh chính thức đây là thanh toán dịch vụ đã đặt trước.",
    },
  },
];

export const getReport = (id: string) => mockReports.find((r) => r.id === id);
export const getHold = (id: string) => mockHolds.find((h) => h.id === id);
