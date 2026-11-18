# Kết quả tải – CHƯA CHẠY

Chưa có benchmark, RPS/VU, p95/error rate hay replica timeline thực. Unit/concurrency test không phải load test. Không đưa số ví dụ vào bảng kết quả.

Hai kịch bản cần tách: HTTP CPU→HPA API; event burst→RabbitMQ backlog→KEDA worker. Mỗi lượt ghi commit/image digest, phần cứng/requests/limits, replica min/max, workload/duration, tổng request/event/số lỗi, p50/p95/p99, CPU/RAM, queue ready/unacked, replica timeline, thời gian rút backlog, alert thật và link raw output. Dùng Mailpit cho tải; không gửi hàng loạt tới mailbox thật.
