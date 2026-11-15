# Mốc 4 – chuẩn bị quan sát và bảo vệ

**IMPLEMENTED_NOT_RUN cho stack; chưa nghiệm thu Mốc 4.** Tiếp tục phần có thể chuẩn bị trên máy hiện tại. Mốc 2/3 vẫn có các chặn về Docker, credential và host VM; không bỏ qua chúng để công bố pipeline hay cluster đạt.

[ĐỀ BÀI] PDF trang 3 yêu cầu Prometheus/Grafana, CPU/RAM/request rate/error rate/p95 từng service, Alertmanager gửi Telegram/Discord/email, log tập trung EFK hoặc Loki/Promtail; trang 5 yêu cầu queue monitoring/KEDA; trang 6 yêu cầu 8 demo và sản phẩm nộp. [THIẾT KẾ] ở đây dùng Prometheus thu trực tiếp, Grafana provisioning, Telegram receiver, EFK 9.5.6/Fluentd 1.20.1, namespace monitoring/logging và lưu 7 ngày. Không triển khai tracing/SLO nâng cao.

| Sản phẩm | Kiểm chứng đã thực hiện | Chưa kiểm chứng |
|---|---|---|
| Prometheus jobs, recording rules và 14 alert rules vận hành | promtool 3.16.0 check config syntax, check rules; 14 tình huống fixture có kiểm tra thời gian chờ, FIRING và hết điều kiện | Scrape thật, dữ liệu đủ theo service, cảnh báo vận hành |
| Grafana export 37 panel và datasource/provider | Tất cả truy vấn qua parser PromQL; ConfigMap/Kubernetes schema | Grafana chạy, import/API export khớp nguồn và biểu đồ có dữ liệu |
| Alertmanager 0.35.0 receiver đọc token từ file, send_resolved | amtool check-config với file giả chỉ dùng cho parser, không gửi ra ngoài | Token/chat ID thật, nhận FIRING và RESOLVED trên Telegram |
| EFK có TLS, user ghi log riêng, ILM 7 ngày; CRI → JSON → namespace/service/level/ID | Manifest schema/policy, đối chiếu plugin và Elastic 9 theo Gemfile upstream | Fluentd --dry-run, TLS/auth ES, ingest, Kibana và truy vấn khớp request thật |
| 51 đối tượng operator sau render; 8 image ghim digest | Kustomize/schema, kiểm quyền đọc, mount CA công khai, hostPath hẹp và log read-only | Scan image, apply/PVC/probes và tài nguyên thực |
| API đếm cả 500 ngoài dự kiến; Nginx JSON không ghi URI/query; AMQP timestamp và histogram queue delay | Unit test phản hồi lỗi an toàn, metric 500, timestamp giữ mandatory/persistent, bỏ timestamp thiếu/tương lai | Build Nginx -t và chạy lại toàn bộ PostgreSQL/RabbitMQ/SMTP trên stack mới |
| Backup có metric lần chạy thành công/thất bại | Bash syntax, rule fixture missing/stale/failed backup | pg_dump/retention/restore thực |

Các fixture PromQL/Vault và parser token **không phải cảnh báo gửi thật**. Không dùng số liệu fixture để vẽ dashboard nghiệm thu. p95 HTTP chỉ dùng route nghiệp vụ /api; worker/publisher dùng throughput/outcome và duration xử lý. Queue delay đo từ lần publish AMQP gần nhất, gồm retry TTL, timestamp độ phân giải giây; không gồm thời gian chờ outbox trước publish và không thay thời gian gọi SMTP.

Bootstrap operator có gate Trivy CRITICAL cho toàn bộ 8 image; thiếu report/scan lỗi/CRITICAL đều chặn. Không dùng ignore-unfixed hay allowlist chung. Ngày14/11 chưa scan; cập nhật15/11 đã remote scan8/8digest không CRITICAL, xem [bằng chứng](../evidence/ops-security-latest.json). Chưa apply stack. Deployer ứng dụng không được cấp quyền quản trị monitoring/EFK.

Xem [bằng chứng local](../evidence/m4-latest.json), [runbook dựng và nghiệm thu](../runbooks/observability.md), [ánh xạ metric](metrics-map.md), [từng cảnh báo](../runbooks/alerts.md), [8 bước demo](demo-script.md), [ước tính cloud](cloud-cost-estimate.md). Mọi bước demo, tải, rollback 120 giây và video vẫn chưa có kết quả chạy thực tế.

Lượt kiểm cuối có 80 bài unit/regression đạt và8 integration bỏ qua. Native gates của bản cuối đều qua; WSL có lượt lỗi WSAENOTCONN và lượt cuối exit1 không có chẩn đoán. Evidence tổng hợp dẫn lượt Ansible/Bash/Vault thành công trước đó sau khi so hash nguồn liên quan trùng hoàn toàn và xác nhận ansible.cfg không đổi; giữ nguyên cả lượt WSL lỗi. Không gọi WSL hiện tại đã phục hồi. Jenkins parser mới vẫn BLOCKED:ConnectError; không có build Jenkins mới.

Cập nhật15/11/2026: WSL và Docker đã chạy lại, Jenkins riêng18090 đã cấu hình và parser qua sau khi bỏ timestamps() không có plugin. Xem [bằng chứng mới](ci-recovery.md); các lượt lỗi ở trên giữ nguyên theo thời điểm. [Di chuyển active disk Docker sangD đã kiểm chứng](../evidence/docker-storage-latest.json), giữ nguyên inventory/Jenkins và smoke image dev cũ qua. Agent/pipeline và stack/alert/demo vẫn chưa nghiệm thu; smoke này không thay build/test source M4.

Cập nhật security15/11: scan8image giám sát và kiểm tra raw receipt đã qua, không thay bằng chứng app release image/CI build hoặc runtime. Chi tiết timeout→retry và sanitization checksum công khai trong [CI recovery](ci-recovery.md).


Cập nhật **15/11/2026**: [CI và image SHA đã chạy thật](../evidence/ci-runtime-latest.json). Jenkins4/5SUCCESS, unit81passed/8skip; integration33passed/0skip; build/scan đủ5imageSHA và dependency không CRITICAL. Agent online/non-root, Docker rootless qua mutualTLS đã sửa SAN. Full-stack SHA riêng:7healthy/non-root, migration/seed0, health/ready/metrics/JSON và đặt/hủy lịch/email qua. GitHub push202 tự kích Jenkins5SUCCESS; gate âm1secret và4CRITICAL có FAILURE/push-deploy skipped thật. GHCR chưa có credential, PRmain phù hợp chưa chạy ở snapshot này; không staging/production/VM/cluster. Các đoạn ngày14/11 bên dưới là lịch sử, không phải trạng thái mới nhất.

Các sửa đổi metric/log M4 đã được kiểm lại trên imageSHA và runtime riêng; đây không phải Prometheus/Grafana/EFK/Alertmanager hoặc Kubernetes đã chạy.
