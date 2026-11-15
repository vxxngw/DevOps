# Báo cáo kỹ thuật đồ án – bản nháp có giới hạn kiểm chứng

Đề tài: **Đặt lịch khám có thông báo – An Uyên Hospital**. Các yêu cầu học phần nằm trong compliance-matrix.md; công nghệ và ngưỡng là lựa chọn thiết kế, không phải nguyên văn PDF.

Kiến trúc: frontend React/Nginx → FastAPI → PostgreSQL appointment/outbox → publisher → RabbitMQ → worker SMTP. Xem architecture.md và contracts. M1 có evidence đặt/hủy lịch, broker outage, retry/dedupe và UI trên stack lịch sử; không suy sang image mới chưa chạy.

Pipeline chuẩn bị: checkout → secret scan → lint/unit → IaC/observability checks → build/integration → Trivy → push digest → staging/migration/smoke → người duyệt → production cùng digest. Xem ci-cd.md/Jenkinsfile. Stage và credential M2–M4 chưa được nghiệm thu trên Jenkins mới.

Hạ tầng dự kiến: libvirt3 VM, Ansible, k3s2 node, staging/production riêng namespace/PVC/broker/vhost/credential; cert-manager, RBAC, API HPA, worker KEDA. Monitoring/EFK dùng tài khoản operator riêng. Resource budget và cloud estimate tách thiết kế khỏi benchmark.

Kết quả có thật được lưu tại docs/evidence: kiểm thử và parser local, schema/provider thực; các lượt lỗi cũng được giữ. Thống kê mới nhất lấy từ m4-latest.json/JUnit, không sao chép số minh họa. Load-test-results.md hiện chưa có benchmark cluster/HPA/KEDA hoặc rollback120 giây. Không có ảnh dashboard hay tin nhắn alert thật trong báo cáo này.

Sự cố đã quan sát và phạm vi nguyên nhân được mô tả ở postmortem.md; nhóm cần review, gán người chịu trách nhiệm/hạn thật. Phân công và đóng góp dùng team-workflow.md, Git/PR có thật; còn thiếu thông tin thành viên và review.

Sản phẩm và video theo submission.md. Báo cáo này chưa phải bản nộp cuối kỳ: cần runtime, tải/demo, ảnh/receipt, phân công xác nhận và video≤10 phút. Không có cơ sở kết luận điểm số hoặc hoàn thành toàn bộ từ cấu hình.
