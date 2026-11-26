import type {
  AccountBalance,
  AlertItem,
  CustomerReport,
  Draft,
  Order,
  RecentTransfer,
  Recipient,
  Refund,
} from "../types/transfer.types";

// TODO: remove once transfer API is ready.
export const mockAccount: AccountBalance = {
  balance: 25_000_000,
  held: 0,
  available: 25_000_000,
};

export const mockRecipients: Recipient[] = [
  {
    id: "rcp-001",
    name: "Nguyễn Văn An",
    bankCode: "VCB",
    accountNumber: "0011 2233 4455",
    flags: [],
  },
  {
    id: "rcp-002",
    name: "Trần Thị Bình",
    bankCode: "TCB",
    accountNumber: "0099 8877 6655",
    flags: ["newRecipient"],
    restriction: "WARN",
  },
  {
    id: "rcp-003",
    name: "Công ty TNHH Sao Mai",
    bankCode: "MBB",
    accountNumber: "0123 4567 8901",
    flags: ["reportedRecipient"],
    restriction: "HOLD",
  },
];

export const mockDrafts: Draft[] = [
  { id: "drf-101", label: "Draft #101 – Đặt cọc thuê nhà", amount: 3_000_000 },
  { id: "drf-102", label: "Draft #102 – Phí xử lý hoàn tiền", amount: 500_000 },
];

export const mockOrders: Order[] = [
  { id: "ord-5001", label: "Order #5001", amount: 1_250_000, feeVnd: 0 },
  { id: "ord-5002", label: "Order #5002", amount: 3_400_000, feeVnd: null },
];

export const mockRefunds: Refund[] = [
  {
    id: "rf-01",
    orderId: "ord-5001",
    amount: 1_250_000,
    status: "approved",
    updatedAt: "2026-11-22T09:30:00Z",
  },
  {
    id: "rf-02",
    orderId: "ord-5002",
    amount: 400_000,
    status: "pending",
    updatedAt: "2026-11-23T14:05:00Z",
  },
];

export const mockAlerts: AlertItem[] = [
  {
    id: "al-01",
    kind: "risk",
    key: "refundImpersonation",
    createdAt: "2026-11-24T08:15:00Z",
  },
  {
    id: "al-02",
    kind: "refund",
    key: "refundApproved",
    createdAt: "2026-11-22T09:31:00Z",
  },
  {
    id: "al-03",
    kind: "info",
    key: "stayAlert",
    createdAt: "2026-11-20T08:00:00Z",
  },
];

export const mockRecentTransfers: RecentTransfer[] = [
  {
    id: "TRF-20261124-01",
    recipientId: "rcp-001",
    recipientName: "Nguyễn Văn An",
    accountNumber: "0011 2233 4455",
    amount: 1_200_000,
    status: "completed",
    createdAt: "2026-11-24T07:20:00Z",
  },
  {
    id: "TRF-20261123-02",
    recipientId: "rcp-002",
    recipientName: "Trần Thị Bình",
    accountNumber: "0099 8877 6655",
    amount: 650_000,
    status: "completed",
    createdAt: "2026-11-23T11:10:00Z",
  },
  {
    id: "TRF-20261121-03",
    recipientId: "rcp-003",
    recipientName: "Công ty TNHH Sao Mai",
    accountNumber: "0123 4567 8901",
    amount: 500_000,
    status: "cancelled",
    createdAt: "2026-11-21T16:40:00Z",
  },
];

export const mockCustomerReports: CustomerReport[] = [
  {
    id: "RPT-1001",
    recipientId: "rcp-003",
    recipientName: "Công ty TNHH Sao Mai",
    category: "scamRecipient",
    description:
      "Yêu cầu chuyển trước 500.000đ phí xác minh để nhận hoàn tiền đơn Order #5002 (REF-7731).",
    evidenceId: "EVD-7731",
    status: "inReview",
    createdAt: "2026-11-23T08:20:00Z",
  },
];

export const mockSampleSuspiciousText =
  "Chào bạn, đơn Order #5002 (mã REF-7731) đã được duyệt hoàn tiền. Vui lòng chuyển gấp phí xác minh 500.000đ tới tài khoản 0123 4567 8901 để giải ngân ngay.";
