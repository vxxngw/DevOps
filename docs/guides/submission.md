# Checklist sản phẩm nộp [ĐỀ BÀI trang 6]

**Chưa sẵn sàng nộp cuối kỳ.** Đối chiếu toàn bộ dòng SUB trong compliance-matrix.md; không đánh dấu hoàn thành chỉ từ tài liệu/cấu hình.

Owner bàn giao đồng bộ [nhóm 4 người](team-onboarding.md): Vuong tập hợp repo/README/báo cáo/postmortem; Hoang kết quả tải, cảnh báo/dashboard và video; Long restore DB/chi phí; Thien deploy/rollback và phần Kubernetes. Cả 4 review báo cáo và trình bày phần mình. Phân công không thay bằng chứng nghiệm thu hoặc đóng góp thật.

| Sản phẩm | Đã có | Còn thiếu |
|---|---|---|
| Link repo và README dựng lại từ máy trắng | Repo vxxngw/DevOps, nhánh/PR thật; README, hướng dẫn M1–M4, Terraform/Ansible/CI/K8s | Review thật, branch protection phù hợp gói GitHub, dựng máy trắng/pipeline/runtime và release tag đã nghiệm thu |
| Báo cáo kiến trúc/pipeline/lý do/tải/phân công/postmortem | architecture.md, ci-cd.md, decisions.md, project-report.md, postmortem kỹ thuật có bằng chứng | Kết quả tải thật, tên thành viên/commit/review thật và nhóm xác nhận postmortem; không gán tác giả giả |
| Runbook deploy/rollback/khôi phục DB/từng alert | docs/runbooks; [restore dev thực tế](../evidence/backup-restore-20261115T134405Z/README.md) đã kiểm dữ liệu/schema/API và cleanup | Timer/host/cluster, offsite/RPO/RTO sự cố, deploy/rollback và nhận cảnh báo thật; dev drill chưa thay toàn bộ nghiệm thu production |
| Video tối đa10 phút | Kịch bản8 bước và kế hoạch quay trong demo-script.md | Chưa quay, chưa có file hoặc URL; không tạo link giả |
| Grafana dashboard export và alert rules | observability/grafana/dashboards/operations.json (37 panel), rules vận hành/demo, 14 ca promtool | Import/UI/export từ Grafana đang chạy, metric thật, Alertmanager FIRING/RESOLVED phía nhận |

Evidence ghi đúng revision trước commit và hash source tại thời điểm chạy; một số bài integration cần PostgreSQL/RabbitMQ/SMTP nên bị skip. M1 có evidence lịch sử chạy thật, không tự suy sang stack mới M2–M4. Các cấu hình/giá tra cứu không chứng minh cloud hay cluster đã được triển khai.
