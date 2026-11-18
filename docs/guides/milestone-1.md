# Mốc 1 – kết quả kiểm chứng dev

Cập nhật 14/11/2026 (Asia/Ho_Chi_Minh). Đã đọc toàn bộ brief và PDF 7 trang, khảo sát workspace rỗng và tạo ma trận trước khi triển khai code. Mã hiện UNCOMMITTED, chưa có remote; evidence ghi source hash thay commit giả. Đây là kết quả Mốc 1 trong Compose dev, không phải chứng nhận đủ 12 bài hoặc đủ đồ án cuối kỳ.

## Đã thực hiện

- UI React/TypeScript tiếng Việt, responsive, login patient/admin, chọn bác sĩ/slot, đặt/xem/hủy lịch, trạng thái email; admin thêm bác sĩ/slot, xem/lọc/hoàn tất lịch hợp lệ. Các nút gọi API thật; token giữ trong bộ nhớ.
- FastAPI + SQLAlchemy + Alembic/PostgreSQL; seed synthetic có 2 bác sĩ, 224 slot tương lai và 3 tài khoản, chạy lặp an toàn, cấm seed/reset demo ở production. Kiểm tra ownership/admin, thời gian UTC/giờ Việt Nam, trạng thái BOOKED/CANCELLED/COMPLETED, cấm xóa slot có lịch.
- DB partial unique index và row locks chống trùng; idempotency theo user/operation/key lưu cùng transaction với lịch/outbox/delivery.
- Publisher/worker riêng, contract versioned chỉ chứa ID, durable/quorum RabbitMQ, persistent/mandatory/confirm, manual ack, prefetch1, retry TTL hữu hạn, DLQ/replay audit/budget, dedupe SENT/SKIPPED, lease phục hồi và stale-event policy. SMTP gửi vào Mailpit, không tuyên bố exactly-once.
- Dockerfile app/frontend/PostgreSQL/RabbitMQ, Compose jobs migration/seed, healthy dependencies, network/volumes và env random. Mailpit còn dùng image upstream trực tiếp; Docker rubric toàn hệ thống chưa đủ. Backend container user10001, cap_drop ALL/no-new-privileges đã inspect thực.
- Health/ready/metrics của cả ba backend đều HTTP200 sau phục hồi; capture JSON stdout: API100/100 dòng, publisher32/32, worker7/7 parse JSON tại snapshot inspection. RabbitMQ management/Prometheus exporter đã có listener và endpoint metrics/per-object HTTP200. Chưa có Prometheus/Grafana/Alertmanager/EFK/KEDA.

## Kết quả thực

| Kiểm chứng | Kết quả / phạm vi |
|---|---|
| Python dependency/lint/format/unit cuối | pip check, Ruff check/format exit0; SQLite API/unit có 13 pass, 6 skip đúng lý do PostgreSQL/broker; không suy 6 skip thành đạt |
| Suite Linux (unit + integration) | 19/19 pass: 8API/DB test trên PostgreSQL,1schema test,6unit reliability dùng fake channel/sender nhưng DB thật,4test broker/SMTP adapter thật. Không gọi cả19là SMTP/broker integration |
| Browser dev riêng | 5 checks pass trên SQLite preview; scope cũ được giữ nguyên trong evidence |
| Browser Compose thật | 6 checks pass: booking đạt SENT, hủy, patient khác không thấy lịch, admin thêm bác sĩ/slot, không lỗi JS, mobile không tràn ngang. Hash JS/CSS đang phục vụ khớp build local; có ảnh desktop/mobile |
| Business/fault smoke | Đọc được email đúng appointment/status; recreate API rồi proxy phục hồi; dừng RabbitMQ vẫn booking/DB outbox unpublished; start broker thì gửi được; kill worker trước ack rồi phục hồi; hủy 3 lịch test và gửi email hủy |
| Worker crash recovery | 114,781 giây trong lần đo, lease mặc định120s và delay10s chỉ khi diễn tập. Đã gỡ override về0. Không phải phép đo rollback app≤120s của DEMO6 |
| Native Windows integration | Một lượt bị treo, đã dừng đúng tiến trình pytest và dọn đúng DB test; exit4294967295, không tính pass. Khuyến nghị dùng runner Compose/Linux; harness native có timeout120s |

Chi tiết lệnh, thời điểm, raw output, JUnit, source hashes và ảnh ở [evidence index](../evidence/README.md). Các lượt thất bại được giữ lại, không ghi đè thành thành công. Các lịch synthetic của lượt smoke thất bại đã được hủy qua API đúng phạm vi và giữ lịch sử.

## Lỗi phát hiện và đã sửa

Docker engine ban đầu EOF/HTTP500/mất pipe, sau phục hồi báo phiên bản mới. Image PostgreSQL Bookworm cục bộ có passwd rỗng; chuyển sang variant Alpine17.12 đã xác minh user/version, dùng volume mới và giữ volume cũ. File plugin RabbitMQ cục bộ rỗng được thay bằng source file có guard; listener quản trị/metrics đã xác nhận. Nginx dùng DNS động Docker để phục hồi khi API recreate. Chi tiết phân biệt quan sát và giả thuyết ở postmortem.md.

## Còn lại và bước tiếp theo

- Mốc 2: Git remote/main protection/PR/review/semver, Docker SHA/registry push, hoàn thiện audit mọi image, Jenkins declarative/webhook/test/build/gitleaks/Trivy gate và evidence thất bại bảo mật. Có container my-jenkins8080 nhưng chưa nối/cấu hình pipeline đồ án; không sửa instance sẵn có.
- Mốc 3: cần chọn provider/host tạo3VM, tài nguyên đủ, credential qua kênh riêng, domain/CA. Terraform/Ansible/K8s/TLS/RBAC/HPA/KEDA/backup/restore chưa triển khai. Không thay bằng vài file YAML hoặc VM tạo tay.
- Mốc 4: dashboard/export/rules/alert receiver thật/EFK/load/rollback8demo/video/báo cáo/vấn đáp. Mailpit chỉ chứng minh email dev/test, không chứng minh mailbox bên ngoài hay Alertmanager.
- Nhóm cần xác nhận backend đã đăng ký, tên/kênh trao đổi và review code/evidence. Các trạng thái NOT_STARTED/IMPLEMENTED_NOT_RUN/BLOCKED còn lại giữ trong ma trận; không công bố hoàn thành toàn bộ.
