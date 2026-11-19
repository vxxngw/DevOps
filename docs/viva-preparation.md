# Chuẩn bị vấn đáp – trả lời theo mã và bằng chứng

1. **Vì sao outbox?** Appointment và event cùng transaction PostgreSQL; broker tạm dừng vẫn giữ lịch/event. Publisher confirms và mandatory phát hiện route lỗi; crash sau publish trước ghi DB vẫn có thể phát lại.
2. **Vì sao không hứa exactly-once email?** Dedupe và lease giảm gửi trùng; SMTP nhận xong nhưng worker chết trước ghi SENT vẫn còn crash window. Mailpit là test receiver, chưa chứng minh mailbox ngoài.
3. **ACK/retry/DLQ khác nhau thế nào?** Manual ACK sau xử lý hoặc chuyển retry/DLQ được confirm; retry TTL có giới hạn; DLQ giữ sự kiện để kiểm tra/replay có kiểm soát, không purge để che lỗi.
4. **HPA và KEDA có cùng điều khiển worker?** API HPA theo CPU; KEDA tạo HPA riêng cho worker theo queue ready+unacked. Không tạo HPA thứ hai trên worker. Hiện mới kiểm schema/policy, chưa có timeline scale thật.
5. **p95 được tính ra sao?** histogram_quantile trên sum(rate(bucket)) theo le và namespace/service; không lấy trung bình p95 replica. HTTP chỉ route nghiệp vụ; process time và queue wait là hai histogram khác nhau. Queue wait gồm retry TTL và sai số giây của AMQP timestamp.
6. **Không có metric có phải bằng0?** Không. ServiceDown dùng expected series để phát hiện mất target; backup thiếu metric cũng báo lỗi. Graph No data cần điều tra nguồn scrape.
7. **Terraform tạo gì?** Module libvirt cho VM/cloud-init/volume, mạng NAT/DHCP/DNS, outputs/inventory. Ansible cấu hình UFW bên trong guest. Validate thật đã qua; máy hiện tại chưa đủ RAM/disk/quyền để apply 3 VM.
8. **Ansible idempotency được chứng minh chưa?** Chưa. Syntax/Vault fixture đã chạy; phải chạy trên VM hai lần và lưu recap changed=0. Không gắn changed_when:false cho thao tác thay đổi để làm số đẹp.
9. **Ai giữ quyền cluster?** Operator bootstrap addon/RBAC/observability; Jenkins chỉ Role theo namespace; app không mount token. Prometheus/KSM chỉ đọc cần thiết, không đọc Secrets/nodes-proxy. Fluentd là ngoại lệ root/hostPath hẹp để đọc log, chưa chạy thực.
10. **HTTPS được chứng minh bằng CertificateReady chưa?** Chưa đủ. Cần client trust CA và hostname/SAN đúng, request HTTPS không bỏ verify. Elasticsearch client chỉ mount CA công khai, không nhận private TLS key.
11. **Rollback có hoàn tác DB không?** Snapshot phục hồi image/config, không downgrade hay restore DB tự động. Migration phải tương thích ngược; restore diễn tập vào DB staging mới. Chưa đo tiêu chí120 giây.
12. **Bằng chứng hiện có là gì?** Xem docs/evidence/README.md, m3-latest.json, m4-latest.json và source hashes. Unit/parser/fixture không thay runtime. Chưa có Jenkins mới, GHCR release digest, 3 VM, HPA/KEDA/EFK/Telegram/video nghiệm thu đầy đủ.
13. **Vì sao local và cloud estimate?** PDF cho phương án local kèm chi phí chuyển cloud. Bảng giá có nguồn/ngày/giả định, chưa mua dịch vụ. Cụm1server+1agent và DB1 replica chưa HA.
14. **Ai làm gì trong nhóm?** Chỉ dùng tên, commit và review có thật. Vai trò dự kiến trong team-workflow.md cần nhóm điền; không dùng lịch sử Codex để giả đóng góp nhiều người.
