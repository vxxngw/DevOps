# Dựng và nghiệm thu monitoring/EFK – chưa chạy trên cluster

Điều kiện: hoàn tất Mốc 2/3, 2 node Ready, đúng context lab và staging/production, đủ disk/RAM, app đang chạy bằng digest đã scan, cert-manager/CA hoạt động. Cấu hình địa chỉ mặc định 192.168.150.10/11/12, pod CIDR 10.42/16, service CIDR 10.43/16; nếu Terraform đổi các giá trị này phải sửa scrape targets/NetworkPolicy và kiểm chứng lại. Không sửa truststore/hosts hoặc gửi thông báo trong bước kiểm tra local.

## Kiểm tra local

```powershell
.\.venv\Scripts\python.exe scripts/install-observability-tools.py
.\.venv\Scripts\python.exe scripts/verify-m4-local.py
```

Binary Prometheus/Alertmanager đối chiếu SHA256 release, cache trên .infra-local ở D và bị ignore. Kết quả chỉ gồm parser/schema/policy/unit/fixture. Nginx -t, Fluentd --dry-run và image scan cần chạy riêng trên môi trường Linux/container phù hợp; hiện chưa chạy. Jenkinsfile mới chưa qua parser do Jenkins không kết nối được, chưa có build pipeline Mốc 4.

## Chuẩn bị operator và scan

Chạy lại Ansible tag os cho cấu hình vm.max_map_count=1048576 và thư mục /var/lib/anuyen-fluentd mode0700 trên 2 node. UFW chỉ mở 9100/10250 từ pod CIDR và dải node; không mở ra Internet. Kubelet phải trình chứng thư có IP SAN và CA khớp /var/run/secrets/kubernetes.io/serviceaccount/ca.crt. Nếu xác minh TLS thất bại, lấy đúng CA công khai từ admin rồi sửa mount/config; không bật insecure_skip_verify.

```bash
python scripts/scan-observability.py
python scripts/prepare-observability-secrets.py --telegram-chat-id ACTUAL_CHAT_ID --telegram-token-file PRIVATE_TOKEN_FILE
python scripts/bootstrap-observability.py foundation --expected-server https://192.168.150.11:6443 --secrets-file .infra-local/observability/secrets.json
```

Chỉ chạy prepare khi chủ kênh đã chỉ định bot/chat thật; không dán token vào chat/Git. Secret file tạo một lần, từ chối ghi đè; bootstrap kiểm credential đang có và từ chối tự xoay password. Scan phải đúng digest, đủ 8 report, không CRITICAL và trong 24 giờ; metadata/report sửa hoặc thiếu đều chặn. Ngày15/11 đã scan8digest không CRITICAL và kiểm raw receipt; khi thực thi vẫn cần scan đúng version/digest trong24giờ. VM/cluster và receiver chưa có nên bootstrap runtime vẫn chưa đủ điều kiện. Trên Linux giữ private file mode0600; Windows/DrvFS cần ACL phù hợp, không coi chmod là đủ.

Foundation áp namespace/RBAC/config/PVC/certificate và Elasticsearch. TCP readiness không chứng minh ES đã xác thực/khỏe. Lấy CA **chỉ ca.crt**, không xuất tls.key, vào file riêng:

```bash
kubectl -n logging get secret elasticsearch-tls -o jsonpath='{.data.ca\.crt}' | base64 -d > .infra-local/observability/es-ca.crt
kubectl -n logging port-forward --address 127.0.0.1 service/elasticsearch 19200:9200
```

Trong cửa sổ khác, operator cần DNS/hosts ánh xạ elasticsearch.logging.svc tới loopback cho tunnel này; dùng đúng hostname có trong certificate, không bỏ TLS verify:

```bash
python scripts/configure-observability.py --expected-server https://192.168.150.11:6443 --secrets-file .infra-local/observability/secrets.json --ca-file .infra-local/observability/es-ca.crt
python scripts/bootstrap-observability.py complete --expected-server https://192.168.150.11:6443 --secrets-file .infra-local/observability/secrets.json
```

Configure tạo ILM/template và user Fluentd chỉ ghi clinic-logs-*, thiết lập kibana_system, user PostgreSQL clinic_metrics với pg_monitor và CONNECT; không cho exporter quyền ứng dụng hay superuser. Marker chỉ tạo sau tất cả thao tác thành công; complete kiểm marker đúng version. Chạy complete có thể gửi cảnh báo qua bot đã cấu hình: chỉ chạy khi chủ kênh đồng ý nhận cảnh báo vận hành. Không dùng Jenkins namespace deployer làm operator.

## Truy cập và kiểm chứng

```bash
kubectl -n monitoring port-forward --address 127.0.0.1 service/prometheus 19090:9090
kubectl -n monitoring port-forward --address 127.0.0.1 service/grafana 13000:3000
kubectl -n monitoring port-forward --address 127.0.0.1 service/alertmanager 19093:9093
kubectl -n logging port-forward --address 127.0.0.1 service/kibana 15601:5601
```

Mỗi lệnh ở cửa sổ riêng. Đây là URL dự kiến http://127.0.0.1:PORT, chưa được xác minh chạy. Kết nối tới Kubernetes dùng TLS; tunnel SSH/port-forward giữ UI chỉ loopback. Grafana user clinicops, password ở private Secret; Kibana operator đăng nhập bằng tài khoản quản trị đã cấu hình, không in password vào terminal/log.

Kiểm Prometheus /targets: từng pod api/publisher/worker, RabbitMQ per-object, PostgreSQL, cả 3 node exporter, 2 kubelet/cAdvisor, Fluentd và kube-state-metrics. Metric vắng hoặc target DOWN phải điều tra trước demo. So sánh panel/JSON export đang phục vụ với observability/grafana/dashboards/operations.json; chụp CPU/RAM/rate/error/p95 cho từng service có ý nghĩa, không thay No data bằng 0.

Tạo Kibana data view clinic-logs-*, time field timestamp. Truy vấn một lỗi thực:

```text
namespace:"staging" and level:"ERROR" and request_id:"ACTUAL_REQUEST_ID"
namespace:"staging" and (request_id:"ACTUAL_ID" or correlation_id:"ACTUAL_ID")
service:"notification-worker" and event_id:"ACTUAL_EVENT_ID"
```

HTTP lỗi trước tạo event có thể không có publisher/worker trace; dùng ID của booking cho kiểm tra chuỗi sự kiện. Fluentd chỉ giữ log JSON có timestamp chuẩn; log plain của DB/Nginx stderr không được coi là log backend JSON và bị lọc khỏi index này. Backend không ghi payload/email/token; Nginx không ghi URI/query/header Authorization. Giữ ảnh/truy vấn/kết quả đã che dữ liệu, không công bố index hoặc thông tin bệnh nhân thật.

## Nghiệm thu cảnh báo và demo

Mỗi loại cảnh báo có [runbook](alerts.md). Ghi lúc điều kiện lỗi bắt đầu, ALERTS thành FIRING, lúc tin nhắn nhận thật, khôi phục và RESOLVED; lưu receipt/ảnh phía người nhận đã che bot/chat nhạy cảm. Promtool fixture và Alertmanager API thấy FIRING chưa chứng minh gửi thành công.

Rule vận hành có thời gian chờ 30 giây–5 phút. Rule demo riêng observability/prometheus/demo/clinic-demo.yml chỉ chọn staging và for=15 s; operator chỉ thêm vào ConfigMap prometheus-rules khi diễn tập rồi restart Prometheus có kiểm soát để tải lại. Gỡ file demo và restart sau diễn tập; không sửa ngưỡng production. Scrape/evaluation=15 s, group_wait=5s là cấu hình, chưa chứng minh phát hiện/rollback ≤120 s. Đo cả lỗi→khôi phục và phát hiện→smoke đạt.

Retention Prometheus 7d/3GB; PVC 4GiB. EFK ILM 7d, một shard/0 replica, PVC 6GiB; phải đo tốc độ log thực và disk, không có bảo đảm đủ cho mọi tải. Buffer Fluentd tối đa64 MiB/node, root chỉ để đọc /var/log/pods read-only và ghi /var/lib/anuyen-fluentd; không privileged container/host network/API token. Namespace logging có ngoại lệ PSA privileged cho hostPath/root collector; không dành cho deployer ứng dụng.

Trước teardown xuất dashboard, evidence và backup ra ngoài lab. Không xóa PVC, queue hoặc log index chỉ để làm alert xanh. Chưa có rollout, ingest, delivery hay demo thực để nghiệm thu.

Sau khi app pod mới đã chạy, kiểm Nginx bằng `kubectl -n staging exec deployment/frontend -- nginx -t`. Đối chiếu Fluentd startup/config logs và `kubectl -n logging rollout status daemonset/fluentd`, sau đó kiểm index/tìm request thật; không dùng một process dry-run chia sẻ buffer với collector đang chạy. Các lệnh này hiện chưa thực hiện.
