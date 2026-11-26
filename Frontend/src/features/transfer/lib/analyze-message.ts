import type { AnalysisResult, Draft, Order } from "../types/transfer.types";

// Mock AI evidence analyzer (TODO: replace with backend analysis API).
export function analyzeSuspiciousMessage({
  text,
  fileName,
  draft,
  order,
}: {
  text: string;
  fileName?: string;
  draft?: Draft;
  order?: Order;
}): AnalysisResult {
  const normalized = text.toLowerCase();
  const refs = Array.from(
    new Set(text.match(/\b(?:REF|ORD|MGD|TRX)-?\d{3,8}\b/gi) ?? []),
  );

  const hasRefundTrap =
    /hoàn tiền|phí|đặt cọc|chuyển trước|refund|fee|deposit|otp/i.test(normalized);
  const hasUrgency = /gấp|ngay|khẩn|hết hạn|urgent|immediately/i.test(normalized);

  const verdict =
    hasRefundTrap || (order && /phí|fee|cọc/i.test(normalized))
      ? "MISMATCH"
      : hasUrgency || (!text.trim() && Boolean(fileName))
        ? "UNCERTAIN"
        : "CONSISTENT";

  const requestedAction = hasRefundTrap
    ? "Yêu cầu chuyển tiền/đóng phí trước để mở khóa hoặc nhận hoàn tiền"
    : text.trim()
      ? "Yêu cầu xác nhận hoặc thực hiện giao dịch theo nội dung tin nhắn"
      : "Cần trích xuất nội dung từ ảnh chụp màn hình đính kèm";

  const claimedPurpose = hasRefundTrap
    ? "Giả danh hỗ trợ hoàn tiền / thu phí xử lý đơn hàng"
    : "Trao đổi giao dịch thông thường";

  const sourceExcerpts = text.trim()
    ? text
        .split(/[.!?\n]+/)
        .map((line) => line.trim())
        .filter(Boolean)
        .slice(0, 2)
    : fileName
      ? [`Ảnh đính kèm: ${fileName}`]
      : [];

  const missingInfo: string[] = [];
  if (!order) missingInfo.push("Chưa liên kết đơn hàng để đối chiếu số tiền và phí gốc.");
  if (!refs.length) missingInfo.push("Không tìm thấy mã tham chiếu giao dịch/đơn hàng trong nội dung.");
  if (order && order.feeVnd === null) {
    missingInfo.push("Hệ thống không ghi nhận khoản phí hoàn tiền cho đơn hàng này.");
  }

  return {
    id: `EVD-${Date.now().toString().slice(-4)}`,
    verdict,
    requestedAction,
    claimedPurpose,
    extractedReferences: refs.length ? refs : fileName ? ["REF-7731"] : [],
    sourceExcerpts,
    missingInfo,
    orderComparison: order
      ? {
          orderLabel: order.label,
          orderAmount: order.amount,
          feeVnd: order.feeVnd,
        }
      : undefined,
    draftLabel: draft?.label,
    fileName,
    analyzedAt: new Date().toISOString(),
  };
}
