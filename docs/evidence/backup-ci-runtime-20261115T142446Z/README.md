# Jenkins 13 và runtime image SHA sau sửa đường dẫn

[Tổng hợp](metadata.json) xác nhận source `d2ba14ceea8d99802db438351d6c6e96e88dca9b`, nhánh `codex/backup-restore-verification`. Hai commit code/evidence đã push; [GitHub push delivery202](github-webhook.json) tự kích [Jenkins13](http://localhost:18090/job/an-uyen/job/clinic-pipeline/13/) bằng user hạn chế `clinic-webhook`, không redelivery hoặc trigger thủ công.

- **SUCCESS** qua secret scan, lint/typecheck, unit, kiểm hạ tầng/observability, build, integration và image/dependency scan.
- [JUnit unit](jenkins-13/junit-unit.xml): **110 đạt/8 bỏ qua**; [JUnit integration](jenkins-13/junit-integration.xml): **33 đạt/0 bỏ qua**.
- [Security summary](jenkins-13/security-summary.json): đủ **5 image SHA, 0 CRITICAL**, dependency0CRITICAL; [Gitleaks gate](jenkins-13/secret-gate.json) không finding. [Bảy raw report](security-reports-verified.json) đã tải từ artifact Jenkins và đối chiếu SHA256 chính xác; bản gốc được giữ private/Jenkins, không sửa hoặc thay report dùng cho gate.
- [Hạ tầng tĩnh](jenkins-13/infra/metadata.json): Terraform1.17.2,28resource mỗi namespace,7source Ansible và6file Bash qua. Không provision hoặc hội tụ Ansible/cluster từ bước này.

[Runtime SHA](sha-runtime/metadata.json) dùng chính image ID đã scan, thay vào Compose nguyên bản của source này và bỏ published ports. Network/volume/project thử riêng trong CI engine; không đổi DB, image hoặc volume dev. **7 dịch vụ healthy/non-root**, migration/seed exit0;9health/ready/metrics backend và frontend200; stdout của cả3backend đều JSON. Đặt rồi hủy lịch đều nhận đúng nội dung email trong Mailpit, final CANCELLED/SENT. Runner exit0 và cleanup exit0.

`PUBLISH_IMAGES=false`, `DEPLOY=false`. Tag có tên GHCR chỉ là tên image local của CI, chưa chứng minh đã push registry. File token chưa có; publish/pull digest, PRmain phù hợp/review thật, timer/VM/Ansible/K8s/HPA/KEDA/monitoring runtime vẫn chưa nghiệm thu. [Backup/restore DB dev](../backup-restore-20261115T134405Z/README.md) có bằng chứng riêng, không lấy runtime Compose thay toàn bộ yêu cầu hạ tầng.

Raw snapshot trước đây được giữ nguyên. `ci-runtime-latest.json` là chỉ mục có thể cập nhật; báo cáo này cố định source/build đã thực sự chạy, không tự nâng sang commit docs sau đó.
