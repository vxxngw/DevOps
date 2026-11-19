# Ánh xạ metric theo service – cấu hình, chưa có dữ liệu cluster

CPU/RAM của mọi container lấy từ kubelet/cAdvisor qua HTTPS có CA và quyền nodes/metrics; không cấp nodes/proxy. Recording rules tổng hợp theo namespace/container. Tên service trong log, Kubernetes và event metric khác nhau có chủ đích:

| Thành phần K8s / log | Request hoặc throughput | Error | Latency | CPU/RAM |
|---|---|---|---|---|
| api / appointment-api | clinic_http_requests_total, route /api/... | status 5xx / tổng request nghiệp vụ | clinic_http_duration_seconds_bucket, histogram_quantile 0.95 | container=api |
| frontend / frontend | clinic_frontend_requests_total từ access JSON qua Fluentd | status 5xx, bỏ category health | clinic_frontend_duration_seconds_bucket, gồm cả thời gian proxy API | container=frontend |
| publisher / outbox-publisher | clinic_events_total{service="outbox-publisher",outcome="published"} | outcome failed / tổng outcome đã ghi nhận | clinic_event_duration_seconds_bucket | container=publisher |
| worker / notification-worker | clinic_events_total theo sent/retry/failed_dlq/done/stale | (retry + failed_dlq) / tổng outcome đã ghi nhận | clinic_event_duration_seconds_bucket cho lần xử lý được ghi nhận; clinic_queue_delay_seconds_bucket riêng cho chờ queue/retry | container=worker |
| postgres | pg_stat_activity_count, pg_database_size_bytes; pg_up từ user pg_monitor riêng | pg_up=0 / scrape failure | Không áp HTTP p95 cho DB; chưa đo query latency | container=postgres |
| rabbitmq | rabbitmq_queue_messages_published_total, delivered_ack_total, acked_total; ready/unacked/total/consumers/DLQ | DLQ, backlog không consumer, scrape failure | Không áp HTTP p95 cho AMQP broker | container=rabbitmq |
| mailpit | Inbox dùng business smoke; không xem là nhà cung cấp SMTP bên ngoài | Smoke phải tìm đúng mã lịch hẹn | Không có histogram SMTP riêng; duration worker gồm xử lý/delay/provider | container=mailpit |

Scrape pod từng replica, không scrape Service cân bằng tải cho backend. honor_labels giữ service trên event metric thay vì biến nó thành exported_service; namespace/pod vẫn lấy từ discovery. Không dùng ID/email làm nhãn. Tổng throughput dùng sum(rate), p95 dùng histogram gộp bucket; không lấy trung bình các p95 riêng.

RabbitMQ dùng /metrics/per-object để có queue/vhost; worker manual ACK nên delivery graph dùng delivered_ack_total. HPA/KEDA desired/current/Ready lấy kube-state-metrics 2.20.0 (client-go 1.36); KEDA quản lý HPA keda-hpa-worker. ScaledObject/Events cần đối chiếu kubectl riêng, không gọi graph replica là bằng chứng operator Ready.

Các nguồn chưa được scrape thật trong phiên này. Dữ liệu vắng phải hiển thị No data và điều tra, không thay bằng vector(0) để che thiếu telemetry. Frontend metric phụ thuộc Fluentd, có thể trễ/mất nếu collector dừng; metric log dựa trên bộ đếm trong RAM, không có bảo đảm exactly-once khi đọc lại log. Dashboard xuất từ repo chưa chứng minh UI Grafana chạy.
