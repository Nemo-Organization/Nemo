import type {
  AccountBalance,
  Draft,
  Notice,
  Order,
  Recipient,
  Refund,
} from "../types/transfer.types";

// TODO: remove once transfer API is ready.

export const mockAccount: AccountBalance = {
  balance: 25_000_000,
  available: 25_000_000,
};

export const mockRecipients: Recipient[] = [
  { id: "rcp-001", name: "Nguyễn Văn An", accountNumber: "0011 2233 4455", flags: [] },
  { id: "rcp-002", name: "Trần Thị Bình", accountNumber: "0099 8877 6655", flags: ["newRecipient"] },
  { id: "rcp-003", name: "Công ty TNHH Sao Mai", accountNumber: "0123 4567 8901", flags: ["reportedRecipient"] },
];

export const mockDrafts: Draft[] = [
  { id: "drf-101", label: "Draft #101 – Đặt cọc thuê nhà" },
  { id: "drf-102", label: "Draft #102 – Thanh toán đơn hàng" },
];

export const mockOrders: Order[] = [
  { id: "ord-5001", label: "Order #5001", amount: 1_250_000 },
  { id: "ord-5002", label: "Order #5002", amount: 3_400_000 },
];

export const mockRefunds: Refund[] = [
  { id: "rf-01", orderId: "ord-5001", amount: 1_250_000, status: "approved", updatedAt: "2026-11-22T09:30:00Z" },
  { id: "rf-02", orderId: "ord-5002", amount: 400_000, status: "pending", updatedAt: "2026-11-23T14:05:00Z" },
];

export const mockNotices: Notice[] = [
  { id: "nt-01", kind: "refund", key: "refundApproved", createdAt: "2026-11-22T09:31:00Z" },
  { id: "nt-02", kind: "info", key: "stayAlert", createdAt: "2026-11-20T08:00:00Z" },
];
