# Xử lý cảnh báo – cấu hình đã chuẩn bị, chưa diễn tập thực

Rule: observability/prometheus/rules/clinic.yml; ngưỡng là thiết kế khởi đầu. Mỗi lần xử lý ghi UTC/giờ Việt Nam, namespace/service, alert bắt đầu/FIRING/nhận tin, nguyên nhân có bằng chứng, hành động và RESOLVED. Kiểm đúng context trước thao tác; các lệnh dưới dùng staging. Không tự áp thao tác phá lỗi, purge queue, reset DB hoặc đổi production để dập cảnh báo.

## Service down

ClinicServiceDown phát khi không còn pod backend được scrape hoặc mất hẳn target; ClinicDatabaseDown theo pg_up; ClinicDependencyDown theo dependency gauge. Kiểm kubectl -n staging get pods, describe/events, /targets và readiness. Xác định process chết, DNS, RBAC, TLS hay DB/broker thật sự lỗi trước restart. Kiểm log JSON bằng ID, không log env/credential. Khôi phục đúng release/config, chạy business smoke rồi kiểm target/alert hết lỗi. up=1 một mình chưa chứng minh nghiệp vụ tốt.

## Scrape failed

ClinicScrapeFailed: kiểm Service/port, discovery RBAC, NetworkPolicy/UFW và CA/SAN kubelet. So sánh pod Ready với target health. Không tắt TLS verify hoặc cấp nodes/proxy/cluster-admin để làm metric xuất hiện. Giữ lỗi lastError không chứa credential và chứng cứ target UP sau sửa.

## HTTP errors

ClinicHighHttpErrors hoặc ClinicDemoHttpErrors: xem rate 5xx / tổng request /api, xác định route và request_id trong EFK. Đối chiếu release digest, DB readiness và logs. Dừng bản lỗi, [rollback](rollback.md) release/config tốt; không hạ ngưỡng hay bỏ business smoke. Rule demo chỉ staging, cần gỡ sau diễn tập. Lưu đủ mốc để đánh giá 120 giây, không bắt đầu đồng hồ muộn.

## Latency

ClinicHighHttpLatency: xem p95 histogram nghiệp vụ và request rate cùng cửa sổ, CPU/RAM/restarts/DB connections. Không dùng health latency hay trung bình p95 replica. Giảm tải thử có kiểm soát, tìm query/dependency chậm hoặc rollback; khôi phục p95 dưới ngưỡng và lỗi không tăng. Chưa có benchmark để coi 1 giây là SLA.

## Queue backlog

ClinicQueueBacklog: đối chiếu ready/unacked/tổng, publish/delivery ACK rate, KEDA/HPA và worker Ready. Kiểm worker delay demo, SMTP test và requests/limits/Pending pods. Chờ KEDA điều khiển worker; không tạo HPA thứ hai hoặc purge message. Gỡ delay sau tải, xác minh email/DLQ và backlog rút, lưu timeline replica tăng/giảm.

## No consumer

ClinicQueueNoConsumer: có message nhưng consumer=0. Kiểm worker Pod/AMQP/vhost/credentials qua Secret metadata và readiness, không in password. Sửa cấu hình hoặc khôi phục worker release đã scan; consumer>0, delivery/ACK tăng và message được xử lý. Chỉ tăng replica khi nguyên nhân không phải lỗi cấu hình chung.

## DLQ

ClinicDlqNotEmpty: giữ nguyên message, xác định event_id/correlation_id và lý do bằng [runbook thông báo](notifications.md). Sửa nguyên nhân rồi replay đúng sự kiện được chọn, giữ ID/budget/audit. Không replay hàng loạt hoặc xóa DLQ để báo đạt. Lưu receipt xử lý và xác nhận cảnh báo hết điều kiện; vẫn ghi giới hạn crash window SMTP.

## Outbox

ClinicOutboxOld: kiểm publisher pending/oldest, DB/broker dependency, publisher confirms/unroutable và log theo correlation_id. API có thể vẫn nhận lịch nhờ outbox; không sửa tay published_at hoặc xóa event. Khôi phục broker/publisher rồi theo dõi pending/age giảm và email đúng.

## CPU

ClinicHighNodeCpu: xem node và container CPU, HTTP/burst đang chạy, desired/Ready/Pending. Dừng tải thử, điều chỉnh requests/capacity theo số đo, không hạ giới hạn dưới nhu cầu DB/broker tùy tiện. Kiểm CPU giảm bền vững và không phát sinh OOM/latency/queue lỗi.

## Memory

ClinicHighNodeMemory: kiểm MemAvailable, working set, restart/OOMKilled và buffers/cache/PVC; requests fit không bảo đảm tổng limits fit. Dừng tác vụ thử không cần thiết, điều chỉnh workload/capacity có kiểm soát. Không xóa dữ liệu Docker/PVC hoặc swap/reset WSL để che lỗi. Chụp usage trước/sau và kiểm lại readiness/nghiệp vụ.

## Backup

ClinicBackupFailed hoặc ClinicBackupStale: xem systemctl status clinic-backup@staging.service/timer, journal, dung lượng /srv/clinic-backups và quyền kubeconfig. Không in password/DSN. Kiểm artifact dump không rỗng và SHA256; chạy lại backup sau khi sửa, chỉ ghi last_success khi thật sự hoàn tất. Dùng [restore](restore.md) vào DB staging mới để xác nhận sử dụng được; không khôi phục đè production. Metric mất cũng bị cảnh báo, không phải trạng thái thành công.

Tất cả mục trên hiện IMPLEMENTED_NOT_RUN cho diễn tập. Cần ảnh tin nhắn nhận FIRING/RESOLVED và số liệu thực mới xác nhận vận hành; các rule fixture đã qua không thay các bằng chứng này.
