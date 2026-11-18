# Kiểm kê image – không miễn yêu cầu ngầm

PDF trang 2 yêu cầu Dockerfile mỗi service với multi-stage, non-root, HEALTHCHECK, .dockerignore và tag SHA/push. Bảng này chỉ ghi cách triển khai; runtime/build/scan/push có trạng thái riêng trong evidence. Chưa có SHA release, registry push hoặc Trivy gate được chứng minh.

| Service/image dùng | Dockerfile / stages | Runtime user khai báo | Health / công cụ | Nơi dùng | Giới hạn |
|---|---|---|---|---|---|
| API | services/Dockerfile, dependencies→runtime | 10001:10001 | Python urllib /health:8000 | compose api | Image dev dùng chung, chưa push SHA |
| Publisher | Cùng image API, entrypoint clinic.runtime publisher | 10001:10001 | Compose override urllib /health:8001 | compose publisher | Phải kiểm tra entrypoint/health thực; không tự miễn vì dùng chung image |
| Worker | Cùng image API, entrypoint clinic.runtime worker | 10001:10001 | Compose override urllib /health:8002 | compose worker | Cùng giới hạn như publisher |
| Migration/seed | Cùng image, job một lần | 10001:10001 | Exit code, không backend HTTP; health disable cho job | compose migrate/seed | Seed chỉ dev, migration production cần Job điều phối |
| Frontend | frontend/Dockerfile, node build→nginx | nginx | wget /health:8080 | compose frontend | Có .dockerignore riêng; port host18080 mặc định |
| PostgreSQL | images/postgres/Dockerfile, chuẩn bị script→runtime official pinned digest, bỏ gosu không dùng | postgres (Alpine UID70 ở M1) | /opt/health.sh gọi pg_isready | compose postgres | Nền có1CRITICAL ở gosu; custom đã bỏ binary thật nhưng chưa build/scan/initdb lại. Entry root không hỗ trợ; không đổi volume dev |
| RabbitMQ | images/rabbitmq/Dockerfile, enabled_plugins→runtime official | rabbitmq | rabbitmq-diagnostics ping | compose rabbitmq | Plugins thực dùng management và Prometheus; vhost dev riêng |
| Mailpit custom | images/mailpit/Dockerfile, binary upstream→configuration→Alpine runtime | 10001:10001 | /mailpit readyz | compose mailpit, ci/compose.test.yaml | Đã viết và config-check, chưa build/run/scan/push bản custom; không dùng evidence upstream để đánh dấu bản mới |
| Jenkins controller | ci/controller/Dockerfile, plugin configuration→runtime | jenkins | curl /login | compose.ci controller18090 | Chưa build/scan/kiểm tra quyền thực; plugins trực tiếp pin, transitive cần lưu kết quả resolver |
| Jenkins agent | ci/agent/Dockerfile, pinned tools→runtime | 1000:1000 | Kiểm tra tiến trình Java | compose.ci agent | Chưa build/scan/nối controller |
| Docker engine CI | ci/engine/Dockerfile, validation→runtime rootless | rootless | docker info qua socket nội bộ | compose.ci engine | Cần privileged để rootlesskit khởi tạo; không mount socket host, chưa chạy thực |
| Webhook relay CI | ci/webhook/Dockerfile, syntax validation→runtime | 10001:10001 | urllib /health | compose.ci webhook18085 | Chưa build/scan/nhận webhook thật; phụ trợ CI, không phải backend nghiệp vụ |
| Monitoring/exporters | Chưa chọn image/chart | Chưa có | Chưa có | Mốc 3–4 | Phải bổ sung vào bảng và xác minh; không đánh dấu đủ Docker cho toàn hệ thống |

Các build dev đã thực hiện không thay build theo commit SHA, scan CRITICAL và push digest registry. Docker healthcheck khác Kubernetes probes; cần cả hai theo rubric. Đối chiếu `Config.User`, `Config.Healthcheck`, effective health override và kết quả chạy non-root/volume sau build; không chỉ đọc USER từ Dockerfile rồi coi VERIFIED.
