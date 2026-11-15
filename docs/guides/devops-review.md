# Rà soát yêu cầu DevOps

Ngày 14/11/2026. Đã đọc lại toàn bộ brief (464 dòng) và PDF (7 trang), đối chiếu repo, công cụ và runtime. **Chưa hoàn thành yêu cầu DevOps; chưa sẵn sàng nộp/bảo vệ đủ đề bài.** Mốc1 đã có luồng ứng dụng/sự kiện được kiểm chứng; Mốc2 mới một phần, Mốc3–4 chưa triển khai đầy đủ. Không lấy kết quả giao diện hoặc số test ứng dụng thay tiêu chí hạ tầng.

Nguồn rubric: [PDF gốc](<C:/Users/Acer/Downloads/Đề tài đồ án môn DevOps.pdf>), trang1–3,5–7. [Brief](C:/Users/Acer/Downloads/CODEX_BRIEF_Dat_lich_kham_DevOps.txt) là kế hoạch triển khai người dùng yêu cầu áp dụng. Phân loại từng dòng và cách kiểm chứng ở [compliance-matrix.md](../compliance-matrix.md).

## Đối chiếu 12 nhóm bắt buộc

| Bài | Trạng thái tổng hợp | Đã có | Phần bắt buộc chưa đủ |
|---|---|---|---|
| 1. Quy trình DevOps | Một phần, thiếu thông tin nhóm | Kiến trúc, DoD, vai trò dự kiến | Tên3–4thành viên, phân công và kênh trao đổi thật; bằng chứng quy trình |
| 2. Git | Chưa đạt | Git local, ignore, CONTRIBUTING và PR template | **0file tracked, chưa có HEAD/commit, remote hoặc tag**; chưa branch protection, PR/review thật và commit từng thành viên |
| 3. Linux | Chưa triển khai | Có WSL phục vụ môi trường local | Chưa script Bash backup định kỳ/health host, retention/backup artifact; chưa user vận hành/SSH key/cấm root SSH/UFW trên máy đích |
| 4. Docker | Một phần | Build/run app, frontend, PostgreSQL, RabbitMQ; user non-root và healthcheck đã kiểm tra | Chưa tag commitSHA, push registry/digest; Mailpit dùng upstream trực tiếp, chưa đủ Dockerfile theo diễn giải chặt; chưa kiểm kê image monitoring còn phải thêm |
| 5. Docker Compose | Đã kiểm chứng phạm vi dev | compose.yaml/compose.test.yaml, .env.example, dependencies, network, volume, jobs migration/seed,7service healthy | Chỉ chứng minh môi trường dev; không thay Terraform/Ansible dựng máy trắng hoặc Kubernetes production |
| 6. Jenkins | Chưa triển khai pipeline | Máy có container my-jenkins sẵn | **Chưa Jenkinsfile**, webhook và pipeline checkout/lint/test/build/scan/push/staging/approval/production của đồ án; chưa release digest hay Credentials IDs được nối |
| 7. Ansible | Chưa triển khai | Có phương án trong ADR | **Chưa infra/ansible**, roles/inventory/Vault; chưa dựng máy trắng hoặc evidence lần2idempotent |
| 8. Terraform | Chưa triển khai; runtime chưa có nền tảng đích | Có thiết kế3VM lab | **Chưa infra/terraform**, module/variables/outputs/provider lock; chưa chọn provider/quyền tạo VM, chưa plan/apply thật |
| 9. Kubernetes | Chưa triển khai | Có kubectl trên Windows | **Chưa deploy/k8s**; chưa có context Windows được đặt. Chưa cluster đồ án, staging/prod, probes/resources/Ingress/TLS, HPA, rolling update/rollback |
| 10. Monitoring/logging | Một phần | API/publisher/worker có health/ready/metrics và log JSON; RabbitMQ exporter bật | **Chưa observability/**: Prometheus scrape, Grafana/dashboard per-service CPU/RAM/rate/error/p95, Alertmanager receiver thật, EFK/log tập trung |
| 11. Security | Một phần nền ứng dụng | JWT/hash/ownership, non-root, env ignored, port dev loopback | Chưa gitleaks/Trivy gate trong pipeline và demo chặn CRITICAL/secret giả; chưa cert-manager/HTTPS/RBAC. Không có báo cáo scanner sạch để công bố |
| 12. Cloud/chi phí | Chưa đạt | Chủ trương local; có file đánh dấu BLOCKED | Chưa production theo mô hình mục tiêu; bảng chi phí cloud mới là mô tả cần làm, chưa provider/region/cấu hình/nguồn giá/tổng chi phí |

Chưa có Jenkinsfile/IaC/Kubernetes/observability là **chưa triển khai**, không chỉ là “đã tạo xong nhưng thiếu credential”. Remote/registry, provider VM, receiver cảnh báo và thông tin nhóm là những điều kiện bên ngoài chưa được xác nhận. Vẫn có thể viết cấu hình và kiểm tra cục bộ trước khi có đủ các điều kiện này.

## Thử thách riêng đề tài8 — PDF trang5

| Phần bắt buộc | Kết quả |
|---|---|
| Event-driven, RabbitMQ, service gửi email/Telegram | Đã chạy trong dev: appointment→outbox→RabbitMQ→worker→SMTP/Mailpit. Email là kênh được chọn; không bắt buộc đồng thời có Telegram |
| Giám sát độ dài queue | Có endpoint exporter/management, **chưa dashboard và giám sát queue được nghiệm thu** |
| Consumer tăng/giảm theo queue bằng KEDA | **Chưa triển khai**, chưa có ScaledObject/TriggerAuthentication hoặc timeline backlog/replica |

Toàn bộ thử thách riêng **chưa đạt**. KEDA là bắt buộc, không phải nâng cao; HPA theo CPU không thay KEDA theo queue.

## Tám bước demo — PDF trang6

**0/8bước được nghiệm thu trọn vẹn**. Có kịch bản trong demo-script.md, chưa có đủ hệ thống để chạy kịch bản này.

| Bước | Phần phải chứng minh | Hiện còn thiếu |
|---|---|---|
| 1 | Terraform→Ansible từ máy trắng→K8s Ready | IaC, VM/provider, cluster và recap |
| 2 | Push→Jenkins→staging→duyệt→production liên tục | Git/SCM, pipeline, registry,2môi trường và request loop |
| 3 | Secret giả/dependency lỗi bị pipeline chặn | Scanner/gate/pipeline và failed-build evidence |
| 4 | Xóa pod, tạo lại, dịch vụ không gián đoạn | Cluster/deployment nhiều replica và timeline/request loop |
| 5 | Load→HPA→Grafana→Telegram/Discord | Load script, HPA, dashboard và cảnh báo nhận thật |
| 6 | Bản lỗi→phát hiện→rollback≤2phút | Release/config tốt/xấu, monitoring và rollback app có đo thời gian |
| 7 | Request lỗi→log tập trung tương ứng | EFK/truy vấn request_id; stdout JSON hiện tại chưa đủ |
| 8 | Queue backlog→KEDA scale→thông báo | Dashboard queue, KEDA, tải queue và timeline consumer/replica |

Worker từng phục hồi114.781giây trong fault smoke **không phải** bằng chứng rollback ứng dụng≤120giây. Khởi động lại Docker cũng không thay bất kỳ bước demo nào trên.

## Toàn bộ sản phẩm nộp — PDF trang6

| Sản phẩm | Đã có | Còn thiếu để hoàn tất |
|---|---|---|
| Repo app/hạ tầng và README máy trắng | Mã local, README khởi động Mốc1 | Remote/revision thật và toàn bộ IaC/CI/K8s; tái dựng máy trắng |
| Báo cáo kiến trúc/pipeline/công nghệ/load/phân công/postmortem | Architecture/ADR và postmortem kỹ thuật có phân định bằng chứng | Báo cáo cuối, pipeline thực, số liệu load, tên phân công; nhóm review và gán owner thật |
| Runbook deploy/rollback/restore/từng alert | Các file mô tả phạm vi và quy trình cần hoàn thiện | Lệnh vận hành đích, backup/restore artifact và diễn tập deploy/rollback/FIRING/RESOLVED thực |
| Video≤10phút | Kịch bản demo | Chưa có video nộp hoặc link kiểm tra được |
| Grafana export và alert rules | Chưa có | DashboardJSON/rules import/validate được, query có dữ liệu và alert nhận thật |

## Bằng chứng và môi trường

Các đường dẫn snapshot thực, thời điểm, exit code và giới hạn được cập nhật ở [evidence index](../evidence/README.md). Lượt rà soát này không sửa mã ứng dụng, không provision VM, không gửi tải, không chạy fault injection hay scan để giả lập thành đạt.

Các sự kiện môi trường quan sát trong lượt này:

- [Snapshot đầu đầy đủ](../evidence/devops-review-20261114T062507Z/metadata.json):7service healthy;3backend×3endpoint health/ready/metrics đều200;2endpoint RabbitMQ metrics đều200; mẫu log146/146dòng là JSON. Git0tracked/0remote/0tag, chưa HEAD. Các file hạ tầng/pipeline nêu trên không tồn tại.
- [Snapshot engine mất kết nối](../evidence/devops-review-20261114T062627Z/metadata.json): docker compose ps/docker ps/Alembic exit1 vì pipe engine không có. Các HTTP trong metadata tham chiếu inspection trước đó, **không phải kiểm tra HTTP mới lúc outage**. Compose rỗng trong snapshot lỗi nghĩa không đọc được trạng thái, không chứng minh đã xóa container.
- Trước đó một lượt thu dữ liệu gặp WinError1455 (paging file quá nhỏ) khi tạo process kubectl; thử lại thu được dữ liệu. Chưa xác định nguyên nhân gốc của Docker mất kết nối, không kết luận chắc chắn do RAM. Đã mở lại Docker Desktop và chạy lại Compose đúng project, không reset volume hoặc thay đổi Jenkins hiện có. Snapshot sau phục hồi được gắn ở evidence index.
- [Sau phục hồi](../evidence/devops-review-20261114T063937Z/metadata.json):7service healthy, migration/seed exit0,11/11endpoint health/ready/metrics HTTP200. Engine từng trả lỗi WSL bootstrap0xc00000fd trong quá trình khởi động; sau engine hoạt động, hai cổng host8000/8001 còn lỗi dù container healthy. Đã recreate **chỉ API/publisher của clinic-dev**, các cổng hoạt động trở lại. [Inspection mới](../evidence/inspection-20261114T063904Z/metadata.json) giữ log/user/health/metrics thực. Snapshot trung gian5/11HTTP không được coi là phục hồi đầy đủ.

Các bài test đã có: suiteLinux30/30 (unit+integration,5test RabbitMQ/SMTP thật), browser smoke11checks và auditUI15checks. Đây là bằng chứng nghiệp vụ/ứng dụng; không thay build Jenkins, security scan, IaC apply, load/autoscale hoặc rollout/rollback. Nhắc lịch60phút, outbox, retry10/30/60giây, replica/threshold đề xuất là thiết kế; không phải tất cả đều là con số PDF bắt buộc.

## Thứ tự thực hiện tiếp theo theo brief

1. **Hoàn tất Mốc2:** hoàn thiện Docker image audit, Git workflow thật, Jenkinsfile/test/scanner gate; sau đó nối SCM/registry và kiểm chứng build/webhook/push. Không đợi credential mới bắt đầu viết các phần cấu hình chưa có.
2. **Mốc3:** chốt nền tảng VM và resource budget; Terraform/Ansible→Kubernetes staging/prod, TLS/RBAC, HPA/KEDA, backup/restore và release/rollback.
3. **Mốc4:** Prometheus/Grafana/Alertmanager/EFK, hai bài tải HTTP/queue, đo đủ8bước demo, báo cáo/runbook/video/export.

Đây là thứ tự kế hoạch của brief, không tự gắn tuần hay điểm số hoàn thành. Ưu tiên bắt buộc trước tính năng ứng dụng/nâng cao tiếp theo.

Kiểm tra sau phục hồi: [11checks browser thật](../evidence/ui-devops-recovery-20261114T063956Z/metadata.json) đều pass, gồm đặt/hủy lịch và nhận email qua RabbitMQ/Mailpit. Không chạy lại suite backend30test hoặc fault smoke trong lượt rà soát này. Không có build Jenkins/scan/load/IaC/KEDA/rollback mới để công bố.
