# Frontend ↔ OpenAPI v1.3.0 Mapping & Backend Gap Report

Tài liệu đối chiếu toàn bộ màn hình hiện có trong `Frontend/` với [openapi.yaml](./openapi.yaml) (`v1.3.0`, base path `/api/v1`).

> **Trạng thái hiện tại của Frontend:** Toàn bộ UI vẫn chạy bằng **mock data**. Các tầng API client (Axios + TanStack Query), DTO types và hooks đã được viết sẵn kèm `TODO` để sẵn sàng nối khi Backend hoàn thiện các trường/endpoint bên dưới.

---

## 1. Tổng quan đối chiếu API theo Feature

### 1.1. Feature `home` (`src/features/home/`)
- **Trạng thái:** Giao diện tĩnh (Hero + 4 thẻ giới thiệu tính năng + điều hướng `/transfer`, `/operator`).
- **Yêu cầu Backend:** Không cần API.

### 1.2. Feature `transfer` — Khách hàng (`src/features/transfer/`)

| Khối UI trên Frontend | API khớp trong `openapi.yaml` | Mức độ khớp | Ghi chú ngắn |
| --- | --- | --- | --- |
| Tóm tắt số dư (`BalanceSummary`) | `GET /me` | **Đủ** | Dùng `accounts[0]` (`balance_vnd`, `reserved_vnd`, `available_vnd`). |
| Danh sách người nhận (`TransferForm`) | `GET /recipients` | **Thiếu field (tùy chọn)** | Không có `restriction` / `flags` nếu muốn hiện tag `Cảnh báo`/`Tạm giữ` trước khi chọn. |
| Tạo, đánh giá, xác nhận, hủy giao dịch (`TransferForm` + `RiskResult`) | `POST /transfers`, `POST /transfers/{id}/assess`, `POST /transfers/{id}/confirm`, `POST /transfers/{id}/cancel`, `GET /transfers/{id}` | **Đủ (khác flow/enum)** | Đủ dữ liệu lõi; cần đồng bộ flow 3 bước (`create → assess → confirm`) và enum `RiskReason.code`, `Transfer.status`. |
| Tab 2: Phân tích tin nhắn / ảnh (`ScreenshotAnalysis` + `AnalysisResultCard`) | `POST /analyses`, `GET /analyses/{id}`, `GET /analyses/{id}/evidence` | **Thiếu API & field** | Thiếu `GET /analyses` (list) và thiếu `analyzed_at`, `order_reference`, `original_amount_vnd` trong `Analysis`. |
| Tab 3 (trái): Bối cảnh hoàn tiền (`RefundContext`) | `GET /orders` | **Thiếu field** | `Refund` không có `updated_at`/`created_at` khi `status = APPROVED` (`settled_at = null`). |
| Tab 3 (phải): Cảnh báo & cập nhật (`AlertsList`) | `GET /notifications` | **Thiếu field & API phụ** | `Notice` thiếu `kind` (`risk`/`refund`/`info`) để tô màu badge; chưa có endpoint đánh dấu đã đọc (`read_at`). |
| Tab 4: Giao dịch gần đây (`RecentTransfers`) | `GET /transfers`, `POST /transfers/{id}/cancel` | **Đủ** | `Transfer` có đủ `id`, `recipient`, `amount_vnd`, `status`, `created_at`, `expires_at`, `reserved_amount_vnd`. |
| Tab 5: Báo cáo (`ReportsPanel`) | `POST /reports`, `GET /reports` | **Thiếu field** | `CreateReport` & `Report` không có `category`/`report_type`; `Report` thiếu `recipient` object (`display_name`, `masked_identifier`). |

### 1.3. Feature `operator` — Vận hành (`src/features/operator/`)

| Khối UI trên Frontend | API khớp trong `openapi.yaml` | Mức độ khớp | Ghi chú ngắn |
| --- | --- | --- | --- |
| Hàng đợi Báo cáo (`OperatorView` + `report-columns`) | `GET /ops/reports` | **Thiếu field** | `Report` thiếu `type`, `priority`, `recipient` summary. |
| Hàng đợi Tạm giữ (`OperatorView` + `hold-columns`) | `GET /ops/holds` | **Thiếu field** | `Transfer` thiếu `customer_name` (chỉ có `sender_account_id` UUID). |
| Chi tiết Báo cáo (`ReportDetailView` + `EvidenceCard` + `ReportReviewActions`) | `GET /ops/reports/{id}`, `PATCH /ops/reports/{id}`, `GET /analyses/{id}/evidence` | **Thiếu field** | `ReportDetail` thiếu `reporter`, `recipient` object, `evidence.file_name`, `evidence.submitted_at`, `linked_transfer`, `linked_order`, `restriction` & `restriction_history`. |
| Điều tra AI & Truy vết (`InvestigationCard`) | `POST /ops/reports/{id}/investigate`, `GET /ops/reports/{id}/trace` | **Thiếu API & field** | Thiếu `model_calls`, `tool_calls`, `ran_at`; `RelatedReport` thiếu `summary`, `status`; `AccessEvent` thiếu `partner_name`, `before_report`; thiếu API lấy kết quả điều tra gần nhất khi reload. |
| Hạn chế người nhận (`RecipientDecisionCard`) | `GET /ops/recipient-restrictions`, `POST /ops/recipient-restrictions`, `POST /ops/recipient-restrictions/{id}/revoke` | **Thiếu field & filter** | Thiếu query `?recipient_account_id=`; `Restriction` thiếu `created_by_name`, `revoked_at`, `revoked_by_name`. |
| Xem trước & gửi cảnh báo theo lô (`ReportNoticeCard`) | `GET /ops/reports/{id}/notice-preview`, `POST /ops/reports/{id}/notices` | **Thiếu field** | `NoticePreview` thiếu `batch_label`, `suggested_title`, `suggested_body`, `recipients[].order_label`, `already_published`. |
| Chi tiết Lệnh tạm giữ (`HoldDetailView` + `HoldDecisionCard` + `HoldSignalBoxes`) | `POST /ops/transfers/{id}/review` | **Thiếu API `GET` & nhiều field** | **Chưa có `GET /ops/holds/{id}`** cho Operator (`GET /transfers/{id}` là role Customer); thiếu `customer_name`, `evidence`, `decision` audit (`by`/`at`), `signals.recipient.source`, `restriction` & `history`. |

### 1.4. Các API có trong `openapi.yaml` nhưng FE hiện chưa hiển thị
- `GET /health` — healthcheck hạ tầng.
- `POST /demo/sessions`, `POST /demo/actors/select`, `POST /demo/refunds/{id}/settle` — nhóm điều khiển sandbox/demo (thanh vàng demo đã được ẩn khỏi UI theo yêu cầu).
- `GET /ops/audit-events` — nhật ký kiểm toán sandbox (chưa có tab hiển thị trên màn hình Operator).

---

## 2. Danh sách API đề xuất Backend làm thêm (Chưa có trong OpenAPI)

| # | Đề xuất Endpoint | Role | Màn hình FE cần dùng | Lý do cần thiết |
| --- | --- | --- | --- | --- |
| 1 | `GET /api/v1/ops/holds/{id}` *(hoặc `GET /api/v1/ops/transfers/{id}`)* | `OPERATOR` | `/operator/holds/[id]` (`HoldDetailView`) | Hiện `GET /transfers/{id}` chỉ cho phép Customer sở hữu giao dịch. Operator cần endpoint lấy chi tiết 1 lệnh tạm giữ kèm thông tin khách hàng, bằng chứng liên kết, tín hiệu rủi ro và hạn chế người nhận. |
| 2 | `GET /api/v1/analyses` | `CUSTOMER` | `/transfer` Tab 2 & Tab 5 (`ReportsPanel`) | Lấy danh sách các lần phân tích AI của khách hàng để sau khi reload trang vẫn chọn được bằng chứng đính kèm khi tạo báo cáo. |
| 3 | `GET /api/v1/ops/reports/{id}/investigations` *(hoặc trả `latest_investigation` trong `ReportDetail`)* | `OPERATOR` | `/operator/reports/[id]` (`InvestigationCard`, `ReportNoticeCard`) | Khôi phục kết quả điều tra AI gần nhất khi reload trang mà không phụ thuộc việc giữ `client_request_id` cũ ở bộ nhớ trình duyệt. |
| 4 | `GET /api/v1/ops/recipient-restrictions?recipient_account_id={uuid}` | `OPERATOR` | `RecipientDecisionCard` | Thêm query param lọc theo `recipient_account_id` để tránh phải tải toàn bộ danh sách hạn chế trong sandbox rồi lọc ở client. |
| 5 | `POST /api/v1/notifications/{id}/read` *(tùy chọn)* | `CUSTOMER` | `/transfer` Tab 3 (`AlertsList`) | Schema `Notice` đã có trường `read_at`, cần endpoint cập nhật nếu FE hỗ trợ đánh dấu đã đọc. |

---

## 3. Chi tiết các trường (Fields) đề xuất Backend bổ sung vào Response/Request hiện có

### 3.1. Nhóm Customer (`transfer`)
1. **`Recipient` (`GET /recipients`)** *(tùy chọn)*:
   - `active_restriction_action?: "WARN" | "HOLD" | null` — nếu muốn giữ tag cảnh báo trên thẻ chọn nhanh người nhận (nếu giữ nguyên tắc chỉ trả khi `assess` thì FE sẽ bỏ tag trên nút chọn nhanh).
2. **`Analysis` (`POST /analyses`, `GET /analyses/{id}`)**:
   - `created_at: string` (ISO date-time) — hiển thị thời gian phân tích (`analyzedAt`).
   - `order_reference?: string | null` và `order_amount_vnd?: number | null` trong `OfficialFacts` (hoặc top-level) — hiện `OfficialFacts` chỉ có `refund_amount_vnd`, `return_fee_vnd`, `fee_source`.
3. **`Refund` (`GET /orders`)**:
   - `updated_at: string` (ISO date-time) — hiện khi `status = APPROVED`, `settled_at` là `null` nên FE không có mốc thời gian để hiển thị.
4. **`Notice` (`GET /notifications`)**:
   - `kind?: "RISK" | "REFUND" | "INFO"` — dùng để hiển thị nhãn màu phân loại trong khối **Cảnh báo & cập nhật**.
5. **`CreateReport` & `Report` (`POST /reports`, `GET /reports`)**:
   - `category?: "SCAM_RECIPIENT" | "PHISHING_MESSAGE" | "FRAUD_ORDER"` — FE có dropdown chọn loại báo cáo và cột hiển thị loại.
   - `recipient?: Recipient` (hoặc `recipient_display_name: string`) trong `Report` — tránh phải gọi thêm `GET /recipients` để map UUID sang tên.

### 3.2. Nhóm Operations (`operator`)
1. **`Report` (`GET /ops/reports`)**:
   - `category?: "SCAM_RECIPIENT" | "PHISHING_MESSAGE" | "FRAUD_ORDER"` (cột Loại báo cáo).
   - `priority?: "LOW" | "MEDIUM" | "HIGH"` (cột Độ ưu tiên).
   - `recipient?: Recipient` (hiển thị tên/ngân hàng/tài khoản che của người nhận).
2. **`ReportDetail` (`GET /ops/reports/{id}`)**:
   - `reporter: { id: string; display_name: string }` — hiển thị trường `Người báo cáo`.
   - `recipient: Recipient` — hiển thị thông tin người nhận ở header và card quyết định.
   - `evidence_file_name?: string | null` và `evidence_submitted_at?: string | null` — hiển thị tên file gốc & thời điểm gửi bằng chứng.
   - `linked_transfer?: { id: string; amount_vnd: number; status: string } | null` và `linked_order_reference?: string | null`.
   - `active_restriction?: Restriction | null` và `restriction_history?: Restriction[]` (hoặc dùng `GET /ops/recipient-restrictions?recipient_account_id=...`).
3. **`Investigation` (`POST /ops/reports/{id}/investigate`)**:
   - `model_calls?: number`, `tool_calls?: number`, `ran_at?: string` — hiển thị mức dùng quota (`X/3 model`, `Y/4 tools`) và thời gian chạy.
   - Trong `RelatedReport`: bổ sung `summary: string` (hoặc `narrative`) và `status: ReportStatus` — FE đang hiển thị danh sách báo cáo liên quan kèm tóm tắt và badge trạng thái.
4. **`AccessEvent` (`GET /ops/reports/{id}/trace`)**:
   - `partner_name: string` — hiện chỉ có `partner_id` (UUID).
   - `before_report?: boolean` — đánh dấu sự kiện truy cập xảy ra trước thời điểm phát sinh báo cáo.
5. **`Restriction` (`GET/POST /ops/recipient-restrictions`, `POST .../revoke`)**:
   - `created_by_name?: string`, `revoked_at?: string | null`, `revoked_by?: string | null`, `revoked_by_name?: string | null` — để dựng timeline lịch sử tạo/thu hồi rõ ràng thay vì chỉ có UUID.
6. **`NoticePreview` (`GET /ops/reports/{id}/notice-preview`)**:
   - `batch_label?: string` — hiển thị nhãn lô thay vì UUID.
   - `suggested_title?: string`, `suggested_body?: string` — nội dung mẫu xem trước cho vận hành viên duyệt gửi.
   - `recipients[].order_reference?: string` — badge mã đơn hàng cạnh từng khách hàng bị ảnh hưởng.
   - `already_published?: boolean` — hiển thị trạng thái đã gửi nếu reload trang.
7. **`Transfer` trong `GET /ops/holds` và `GET /ops/holds/{id}`**:
   - `customer_name: string` (hoặc `sender: { id: string; display_name: string }`) — cột Khách hàng ở bảng hàng đợi và trang chi tiết.
   - `decided_by_name?: string | null`, `decided_at?: string | null` — hiển thị người và thời điểm duyệt/từ chối lệnh tạm giữ.
   - `linked_evidence?: Analysis | null` — hiển thị `EvidenceCard` trên trang chi tiết lệnh tạm giữ.
   - `restriction_source?: { report_ids: string[]; restricted_at: string } | null` — nguồn tạo hạn chế trong `HoldSignalBoxes`.

---

## 4. Khác biệt nghiệp vụ / Enum cần thống nhất trước khi nối thật

1. **Tạo hạn chế từ màn hình Hold (`HoldDetailView`)**:
   - OpenAPI `CreateRestriction` yêu cầu `evidence_report_ids` (`minItems: 1`, bắt buộc có ít nhất 1 report đã `RESOLVED`).
   - Hiện `HoldDetailView` đang truyền `evidenceReportIds: []`. Khi nối BE cần: hoặc chọn/gắn report liên quan, hoặc chỉ cho phép xem/thu hồi hạn chế tại màn Hold (tạo mới thực hiện ở màn Report).
2. **Quy trình chuyển tiền 3 bước & trạng thái `READY`**:
   - FE mock hiện gọi 1 bước `submit → risk`. Khi nối BE sẽ đi theo chuỗi: `POST /transfers` (tạo `DRAFT`) → `POST /transfers/{id}/assess` → `POST /transfers/{id}/confirm` (kèm `acknowledged_assessment_id` nếu là `WARN`).
   - Sau khi Operator duyệt `APPROVE` trên lệnh `RISK_HELD`, trạng thái chuyển thành `READY` và khách hàng cần xác nhận lại (`POST /transfers/{id}/confirm`).
3. **Đồng bộ tên Enum (UI mock ↔ OpenAPI)**:
   - `Transfer.status`: `DRAFT | RISK_HELD | READY | SUCCEEDED | CANCELED | REJECTED | EXPIRED` (FE mock hiện chỉ có `completed | held | cancelled`).
   - `Refund.status`: `APPROVED | SETTLED` (FE mock hiện có `pending | approved | completed | rejected`).
   - `RiskReason.code`: `AMOUNT_ABOVE_BASELINE | RECIPIENT_WARNING | RECIPIENT_HOLD` (FE mock hiện dùng `newRecipient | reportedRecipient | unusualAmount | drainsBalance | highAmount`).
