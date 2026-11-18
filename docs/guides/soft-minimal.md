# Giao diện Soft Minimal và nhắc lịch

Cập nhật 14/11/2026. Đây là yêu cầu giao diện bổ sung trực tiếp của chủ dự án và các lựa chọn triển khai ứng dụng. PDF yêu cầu ứng dụng đặt lịch, RabbitMQ và service thông báo; PDF không quy định bảng màu, Inter, ba bước hoặc nhắc trước một giờ. Ma trận DevOps vẫn giữ nguyên các phần chưa hoàn thành.

**Rà soát mới nhất:** [đối chiếu từng yêu cầu](ui-requirements-review.md). Đã sửa tải lại khung giờ sau lỗi chưa chọn ngày và bổ sung trạng thái chờ/đang gửi/thử lại/lỗi riêng cho email nhắc lịch. Lượt cuối15checks audit +11checks smoke thật đều pass; các snapshot ban đầu dưới đây được giữ làm lịch sử.

## Giao diện đã triển khai

| Thành phần | Giá trị |
|---|---|
| Nền trang / thẻ | #F3F7FA / #FFFFFF |
| Nút chính, lựa chọn, focus | #286789 |
| Chữ chính / phụ / viền | #223443 / #566874 / #D8E2E9 |
| Logo và tên An Uyên Hospital | #103783, giữ yêu cầu nhận diện trước đó |
| Font | Inter tự phục vụ, gồm tiếng Việt; weight400/500/600 |
| Chữ và bo góc | Nội dung16px; h1 28–32px, h2 24px; thẻ12px, nút/input8px |

CSS token ở `frontend/src/app/styles.css`; icon nét mảnh trong `icons.tsx`. Thẻ trắng, bóng nhẹ, khoảng cách theo nhóm thao tác; desktop có cột tóm tắt, mobile gom một cột. Nội dung xem lại luôn có bác sĩ, ngày, giờ và email. Không có ảnh bác sĩ hoặc thông tin chuyên môn giả do AI tạo.

Ba bước: **Chọn bác sĩ → Chọn lịch → Xem lại**. Tìm theo tên/chuyên khoa; ngày khám có nút riêng; giờ đã chọn có dấu kiểm và viền xanh, giờ hết chỗ có nhãn và bị vô hiệu hóa. Người dùng có thể quay lại sửa. Trước xác nhận có email nhận thông báo và công tắc nhắc lịch.

Trong khi gửi, nút xác nhận hiện “Đang đặt lịch…” và không bấm lặp được. Lỗi hiển thị hướng dẫn, giữ bác sĩ/khung giờ/công tắc và cùng Idempotency-Key khi gửi lại cùng dữ liệu. Nếu khung giờ bị người khác đặt, API trả409, UI tải lại khả dụng và yêu cầu chọn giờ khác. Đăng nhập lỗi giữ dữ liệu đã nhập; mật khẩu được xóa khỏi state khi đăng nhập thành công. Phiên chỉ ở bộ nhớ trình duyệt, tải lại trang cần đăng nhập lại.

Sau thành công, UI phân biệt lịch đã lưu với email PENDING/PROCESSING/RETRY/SENT/FAILED; lỗi gửi mail không biến lịch đã lưu thành thất bại. Lịch hẹn cho phép bật/tắt nhắc trước hạn và hủy lịch trước giờ khám. Phần quản trị bác sĩ, khung giờ và hoàn tất lịch được giữ hoạt động.

## Nhắc lịch có lưu và xử lý thực tế

Quyết định thiết kế: nhắc email trước **60 phút**, tùy cấu hình `REMINDER_LEAD_MINUTES` (1–1440). UI đọc giá trị từ `/api/options`; công tắc mặc định bật khi còn đủ thời gian, có thể tắt trước xác nhận. Khi còn dưới thời gian này, không cho bật nhắc mới; email xác nhận vẫn hoạt động. Tác vụ đã lưu giữ `due_at`, không tự đổi giờ nếu người vận hành đổi cấu hình.

- `POST /api/appointments` nhận `reminder_enabled`; mặc định false cho client cũ. PATCH `/api/appointments/{id}/reminder` chỉ cho chủ lịch hoặc admin đã xác thực và lịch sắp tới còn BOOKED. Response trả `reminder_enabled`, `reminder_at`, `reminder_status` riêng với trạng thái email xác nhận.
- Migration `20261114_01` thêm tùy chọn mặc định false cho lịch cũ và bảng `appointment_reminders`. Đã upgrade DB dev lên head, không reset volume hoặc xóa lịch sử.
- API ghi tùy chọn và tác vụ cùng transaction đặt lịch. Mỗi lịch chỉ có một tác vụ nhắc; bật lại trước hạn tái sử dụng tác vụ đó. Idempotency bao gồm tùy chọn nhắc; hash cũ vẫn được hỗ trợ khi reminder=false.
- Publisher quét tác vụ đến hạn, khóa appointment rồi reminder, ghi `appointment.reminder.v1` vào outbox và đánh dấu ENQUEUED cùng transaction. RabbitMQ/worker xử lý theo cơ chế confirm/manual ack/retry/DLQ hiện có. Thời gian gửi có thể muộn do outage hoặc backlog.
- Tắt nhắc, hủy hoặc hoàn tất dừng tác vụ chưa gửi. Worker kiểm tra lại trạng thái/version và tùy chọn ngay trước SMTP, bỏ qua nhắc đã tắt hoặc lịch đã bắt đầu. Email đã được SMTP tiếp nhận không thu hồi được; cửa sổ SMTP nhận xong nhưng worker chưa ghi SENT vẫn có thể gửi trùng sau crash. Không hứa exactly-once.

## Kiểm chứng và bằng chứng

| Cách kiểm chứng đã chạy | Kết quả |
|---|---|
| TypeScript/Vite và Docker build frontend/app, Compose up/wait | Build thành công; [log và trạng thái](../evidence/soft-minimal-inspection-20261113T193126Z/metadata.json); Alembic head20261114_01; 7 service long-running healthy |
| `scripts/dev/verify.py`, Windows/SQLite | [22pass,8skip](../evidence/20261113T193126Z/metadata.json), lint/format/pip check exit0; SQLite không chứng minh row lock hoặc broker |
| `scripts/dev/check-integration.ps1`, Linux/PostgreSQL | [30/30 pass](../evidence/integration-20261113T192650Z/metadata.json), [JUnit](../evidence/integration-20261113T192650Z/junit.xml); gồm10test tùy chọn/timer/khóa và5test adapter RabbitMQ/SMTP thật, các test khác có biên fake được ghi trong source |
| Browser → stack Compose thật | [11checks pass](../evidence/ui-soft-minimal-20261113T193104Z/metadata.json): sai đăng nhập, giờ bận, đang xử lý, lỗi503, giữ dữ liệu/key khi retry, email SENT, bật/tắt được lưu, hủy, quyền patient/admin |
| Đo CSS/font/asset và bố cục thực | [Inspection pass](../evidence/soft-minimal-inspection-20261113T193126Z/metadata.json): đúng màu, Inter thực tải local, bo góc/kích thước; served JS/CSS khớp dist; logo khớp asset; login/chọn giờ/xem lại không tràn ngang ở320/390/768/1440px |

Test nhắc lịch dùng **đồng hồ truyền vào scheduler trong DB test riêng** để kiểm tra đến hạn, rồi gửi qua RabbitMQ/SMTP Mailpit thật và kiểm tra dedupe. Không ghi rằng đã ngồi chờ một giờ theo thời gian thực. Native suite có1cảnh báo TestClient/httpx deprecation; Linux cũng có cảnh báo đó, không giấu cảnh báo.

Ảnh đã xem: [chọn giờ desktop](../evidence/soft-minimal-inspection-20261113T193126Z/slots-desktop.png), [xem lại mobile](../evidence/ui-soft-minimal-20261113T193104Z/review-mobile.png), [đang xử lý](../evidence/ui-soft-minimal-20261113T193104Z/review-processing.png), [lỗi giữ dữ liệu](../evidence/ui-soft-minimal-20261113T193104Z/review-error.png). Mailpit là hộp thư local; chưa chứng minh gửi ra hộp thư ngoài. Mã hiện UNCOMMITTED.

Chạy lại browser từ `frontend`: đặt `CLINIC_BASE_URL=http://127.0.0.1:18080`, rồi `node tests/smoke.cjs ../docs/evidence/<thư-mục-mới>`. Script chỉ dọn khung giờ/bác sĩ thử do chính nó tạo và hủy lịch thử theo ID, giữ lịch sử. Không chạy đồng thời với integration đếm thư Mailpit. Các thư mục lượt lỗi được giữ trong evidence index.
