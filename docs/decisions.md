# Quyết định triển khai

Ngày 13/11/2026. Tất cả mục dưới là [THIẾT KẾ], không phải trích nguyên văn rubric.

| ADR | Quyết định và lý do | Trạng thái / kiểm chứng |
|---|---|---|
| 001 | Python/FastAPI theo brief, frontend React/TS; nghiệp vụ gọn để tập trung DevOps | Tạm chọn; cần nhóm đối chiếu backend đã đăng ký. API test + frontend build |
| 002 | PostgreSQL là DB đích; Alembic migration bất biến; seed riêng, dữ liệu .test và slot động 7 ngày | SQLite dùng kiểm tra cục bộ trong khi Docker lỗi; không thay chứng cứ PostgreSQL |
| 003 | Shared package/image cho API/publisher/worker, tách entrypoint và health/metrics | Giảm drift contract/model; cần build và chạy ba container |
| 004 | Transactional outbox, DB unique index, row locks, lease và idempotency | Test biên cục bộ; cạnh tranh PostgreSQL phải chạy riêng |
| 005 | Email SMTP; Mailpit trong dev/test, retry hữu hạn và DLQ/replay có audit | Unit test không thay SMTP/RabbitMQ thật; mailbox thật chưa cấu hình |
| 006 | Môi trường local dự kiến 3 VM, k3s server/agent và Jenkins | Cập nhật ADR012: đã thấy KVM trong WSL và chọn cấu hình Linux/libvirt; chỉ chuẩn bị, chưa quyền/daemon/capacity để apply |
| 007 | EFK cho logging vì PDF cho phép trực tiếp; không chọn Promtail | Chưa dựng; mọi thay đổi sang Alloy cần đối chiếu rubric. Xem nguồn chính thức trong versions.md |
| 008 | Không tự tạo remote/registry/domain/credentials/commit giả | User đã cung cấp repo vxxngw/DevOps và đã có commit/push thật. GHCR writecredential/VMsecrets vẫn thiếu; nhập qua localignored/Jenkins/Vault, không chat |
| 009 | HPA API min2/max5 CPU60%; KEDA worker min1/max5 backlog20 là khởi điểm brief | Chưa benchmark, không phải thông số PDF. Cần resource budget toàn cụm gồm EFK trước khi áp dụng |
| 010 | UI Soft Minimal theo yêu cầu trực tiếp: #286789, Inter tự phục vụ, wizard3bước; logo giữ #103783 | [Thiết kế và kiểm chứng](soft-minimal.md); đây là yêu cầu UI bổ sung, không gán vào PDF |
| 011 | Nhắc email tùy chọn trước60phút, timer bền vững trong DB/publisher, dùng outbox và worker hiện có | UI mặc định bật khi đủ thời gian; API/client cũ mặc định tắt; migration không bật lịch cũ. Test timer truyền đồng hồ + broker/SMTP thật, không hứa exactly-once |

Phương án 1 server + 1 agent không HA control plane; PostgreSQL/RabbitMQ một replica không HA dữ liệu. Không suy ra demo xóa pod API không gián đoạn thành chịu lỗi cả node. PDF trang 3 cho phép k3s/minikube/kind/cloud, nhưng demo máy trắng vẫn cần Terraform và Ansible quản lý tài nguyên thực.

## ADR012 – Mốc3 local preparation

[THIẾT KẾ] Ngày14/11/2026, phát hiện KVM trong WSL nhưng thiếu quyền/daemon và capacity. Người dùng chọn chuẩn bị trên máy hiện tại. Dùng Terraformlibvirt0.9.9/module3VM, WSL làm controlnode, Ansible2.22/Python3.13, K3s1.36 để nằm trong phạm vi KEDA2.21 đã công bố kiểm thử; namespace là môi trườngứngdụng của cùngcluster. Chưa apply. Chọn CAriêng .test cho lab; clienttrust/RBAC/HTTPS thực chờ kiểm chứng. Không dùng kind thay3VM hoặc coi schemaunit là runtime. ProfileVM/capacity ở infra/lab-budget.json và runbookinfra-lab.


## ADR013 – quan sát Mốc 4 [THIẾT KẾ]

Chọn Prometheus scrape trực tiếp + Grafana provisioning, Alertmanager Telegram receiver và EFK9/Fluentd1.20 thay Promtail đã EOL. KSM2.20 phù hợp Kubernetes1.36. Dùng operator riêng cho cluster/RBAC/Secrets; Prometheus không có nodes/proxy hoặc quyền đọc Secrets; app không nhận API token. Collector Fluentd root chỉ đọc host log và buffer hẹp, tách namespace logging/PSA ngoại lệ, không privileged container.

Giữ lab libvirt hiện tại và chuẩn bị local; estimate SGP1 chỉ là phương án tính chi phí, chưa chọn thuê cloud. Mọi pin/schema/unit/fixture không thay runtime, CVE scan, ingest hay delivery. Chưa triển khai tracing/SLO nâng cao; ưu tiên nghiệm thu đầy đủ bắt buộc khi có môi trường.
