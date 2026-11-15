# Kịch bản bảo vệ – 8 bước bắt buộc [ĐỀ BÀI trang 6]

**Chưa chạy/nghiệm thu 8 bước.** Thời lượng PDF: 20 phút demo +10 phút vấn đáp; video dự phòng nộp ≤10 phút. Phân bổ dưới là thiết kế 18 phút +2 phút dự phòng, không phải lịch giảng viên. Người A/B/C/D chỉ là vai trò dự kiến; cần gán tên thật trong team-workflow.md.

Điều kiện chung: có 3 VM Terraform/Ansible quản lý thật, Jenkins/webhook/registry/credential, staging/production lab tách dữ liệu và vhost, TLS trusted, HPA/KEDA, monitoring/EFK, receiver Telegram/Discord thật, release tốt có digest và backup đã kiểm tra. Chỉ fault injection trên namespace demo xác định; chưa có các điều kiện này thì ghi BLOCKED, không chạy lệnh phá lỗi trên tài nguyên không rõ chủ sở hữu. Tên tài nguyên đã có trong cấu hình Mốc 3; các lệnh dưới vẫn **chưa chạy** trên cluster.

| Bước / thời gian / owner | Thao tác và lệnh dự kiến | Cửa sổ / bằng chứng | Thành công và reset |
|---|---|---|---|
| 1 /2 phút /C | `terraform apply` cấu hình đã plan, sau đó `ansible-playbook` đúng inventory máy trắng | Terminal Terraform/Ansible; `kubectl get nodes -o wide`; video dựng trước nếu lâu | VM/mạng thuộc state đúng, playbook exit0, node Ready; recap lần2 changed0. Teardown đúng workspace, không destroy môi trường khác |
| 2 /3 phút /A+B | Sửa chuỗi version UI → branch/PR/review/merge → push kích webhook → staging smoke → input duyệt → production cùng digest | Git PR, Jenkins stage/input, release manifest, UI version, request loop | Image/config đúng release, không lỗi trong loop. Giữ release tốt trước để rollback; không build lại khi promote |
| 3 /1,5 phút /B+D | Nhánh thử chứa secret giả nhận diện được hoặc image dependency lỗi đã biết; kích pipeline | Failed gitleaks/Trivy stage và scanner report, deployment vẫn digest cũ | Gate exit≠0, không push/deploy mới; dọn nhánh thử qua quy trình, không chứa credential thật |
| 4 /1 phút /C | Chạy request loop; chọn một pod API demo; `kubectl -n staging delete pod <pod-api-đã-xác-định>` | Pod watch/events, request raw output, Grafana | Pod thay thế Ready; tổng request/số lỗi/p95 chứng minh không gián đoạn. Đợi replica ổn định trước bước sau |
| 5 /3 phút /D+C | Load HTTP bằng scripts/infra/load-http.py theo budget để tăng CPU API; `kubectl -n staging get hpa -w` | HTTP load output, Grafana CPU/replicas/p95/errors, Telegram/Discord nhận alert | HPA tăng và metric đồng thời; receiver nhận FIRING/RESOLVED. Dừng tải, đợi stabilization, kiểm tra replicas về mức gốc |
| 6 /2 phút /B+C+D | Deploy release lỗi dành riêng demo → phát hiện qua metrics/alert → chạy runbook rollback | Timestamp lỗi/phát hiện/rollback/recovery, digest trước/sau, smoke | Phát hiện→smoke bình thường ≤120 giây; báo cả lỗi→recovery. Giữ schema tương thích; khôi phục release/config tốt |
| 7 /1,5 phút /A+D | Tạo request lỗi hợp lệ, lưu X-Request-ID → Kibana lọc namespace/service/level/request_id/correlation_id | Request/response đã che token, truy vấn Kibana và log sự kiện liên quan | Tìm đúng request và xử lý event tương ứng; không ảnh dựng/log minh họa. Dọn dữ liệu demo theo nghiệp vụ hủy |
| 8 /4 phút /A+C+D | Burst booking events độc lập tải HTTP; delay worker chỉ trong demo nếu cần → theo dõi queue/KEDA → email | Queue ready/unacked/backlog/consumer/DLQ, worker replicas/KEDA events, Mailpit hoặc mailbox chỉ định | Backlog tăng→worker tăng→queue rút→worker giảm; email và delivery đúng. Bỏ delay, dừng burst, xác minh không còn retry/DLQ chưa xử lý |

Không dùng “500 người đặt vé” của đề tài khác làm ngưỡng bắt buộc. HPA API theo CPU khác KEDA worker theo queue. Không dùng health p95 làm latency nghiệp vụ. Không công bố endpoint HTTPS khi chỉ chạy curl -k hoặc khai báo TLS chưa có chứng thư trusted. Mỗi evidence phải có môi trường, timestamp, lệnh, commit/source hash và hạn chế.

## Lệnh và điều kiện cụ thể cho buổi chạy sau

Chưa chạy các lệnh này trong phiên chuẩn bị. Xác minh operator context đúng lab, URL API và namespace staging trước mọi thao tác phá lỗi. Password/CA/kubeconfig giữ ngoài Git; các đường dẫn dưới do operator điền. Không dùng production làm namespace fault injection.

1. Dùng scripts/infra/lab.py plan/apply và Ansible theo runbooks/infra-lab.md; giữ state/output/recap và node Ready. Phiên này thiếu host nên bước1BLOCKED.
2. Dùng Jenkinsfile và runbooks/deploy.md; có PR/review thật, webhook delivery/build ID, scan/digest/staging evidence/input approver/production receipt. Chạy request loop suốt cửa sổ rollout; không suy không gián đoạn từ rollout status.
3. Job SECURITY_DEMO=secret hoặc critical phải dừng trước push/deploy; so sánh deployment digest trước/sau và archive failed stage. Scanner local đã fail đúng không thay failed build Jenkins.
4. Mở request loop và pod watch trước khi chọn/xóa1pod API; đợi pod thay thế Ready và giữ số lỗi ngay cả khi kết quả chưa đạt.

```bash
python scripts/infra/load-http.py --url https://staging.anuyen.test --password-file PRIVATE_PASSWORD_FILE --ca-file LAB_CA_FILE --seconds 180 --concurrency 1 > .infra-local/rollout-requests.json
# Another terminal, same verified lab context:
kubectl -n staging get pods -l app.kubernetes.io/name=api -w
# Choose and verify the exact API pod, then:
kubectl -n staging delete pod ACTUAL_API_POD --wait=false
```

5. Tăng tải có giới hạn bằng --seconds 180 --concurrency 16 (tối đa64 sau khi xem tài nguyên); đồng thời xem `kubectl -n staging get hpa api -w`, Grafana CPU/replicas/error/p95 và receiver. Script báo request/success/error/RPS/elapsed và p95 của request thành công; đối chiếu lỗi kết nối riêng. Không đảm bảo tải này luôn đủ kích HPA trên mọi máy, phải đo và hiệu chỉnh.
6. Chuẩn bị release lỗi thử chỉ cho staging, giữ snapshot tốt và schema tương thích; không sửa scanner report hay bypass gate để đưa image chưa scan vào demo. Hiện chưa tạo/built bản lỗi đủ điều kiện, nên bước6BLOCKED. Rule demo15 s chỉ staging theo runbook observability; ghi thời điểm lỗi, phát hiện, nhận alert, bắt đầu rollback và smoke đạt; dùng ci.rollback theo runbook. Báo cả hai khoảng lỗi→recovery và phát hiện→recovery, không làm tròn số vượt120 giây thành đạt.
7. Theo runbooks/observability.md, chọn lỗi thực có X-Request-ID; dùng KQL namespace/service/level và request_id/correlation_id. Giữ request/response đã che token, truy vấn và kết quả. Lỗi HTTP trước transaction không có event là bình thường; dùng ID booking để kiểm chuỗi API/publisher/worker.
8. Theo runbooks/infra-lab.md: bật worker delay2giây chỉ staging, chạy load-queue.py burst, lưu receipt các appointment ID; watch worker/HPA và queue ready/unacked/consumer/DLQ. Chụp email thật trong receiver thử và trạng thái delivery. Cleanup theo receipt, gỡ WORKER_DELAY_SECONDS cả khi lỗi, chờ backlog/retry rút và replica giảm sau stabilization; không purge message.

## Quay video và hồ sơ

Video nộp tối đa10phút, khác buổi demo20 phút. Kế hoạch đề xuất: kiến trúc/VM2phút, pipeline/approval/security2phút, pod/HPA/alert2phút, rollback/log1,5phút, RabbitMQ/KEDA/email2phút, tổng9,5phút. Chỉ dùng footage hệ thống thật, hiện chưa quay. Mỗi bước ghi owner tên thật, commit/digest, UTC/giờ Việt Nam, lệnh, đầu vào, raw kết quả và ảnh/tin đã che nhạy cảm; đánh dấu bước fail/chặn nếu thiếu. Giữ kịch bản reset và video backup dựng VM lâu, không tạo screenshot/link giả.
