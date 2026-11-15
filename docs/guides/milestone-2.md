# Mốc 2 – Container và CI

Cập nhật **15/11/2026**: [source d2ba14c/Jenkins13 SUCCESS](../evidence/backup-ci-runtime-20261115T142446Z/README.md),110unit/8skip,33integration/0skip,5image/dependency0CRITICAL, webhook push202 tự kích đúngSHA. Stack imageSHA riêng có7healthy/non-root, jobs0 và email đặt/hủy qua, cleanup0. Mốc2 vẫn thiếu GHCR publish/pull digest và PRmain phù hợp/review thật; chuỗi staging/approval/production còn chưa chạy. Các bảng/đoạn snapshot14/11 dưới đây là lịch sử, không thay kết quả mới hoặc ngụ ý source hiện còn thiếu IaC/monitoring code.

Trạng thái ngày 14/11/2026: **chưa nghiệm thu Mốc 2**. Mã CI đã triển khai; kết quả local và phần runtime bị chặn được tách dưới đây. Không suy việc Jenkinsfile hợp lệ thành pipeline chạy thành công.

| Tiêu chí trong brief | Phân loại | Sản phẩm | Kiểm chứng thực tế | Trạng thái |
|---|---|---|---|---|
| Dockerfile mỗi service, Compose, chạy dev một lệnh | PDF trang 2, Bài 4–5 | services/, frontend/, images/{postgres,rabbitmq,mailpit}/, compose.yaml | Mốc 1 đã chạy app/frontend/DB/broker; Mailpit custom mới chỉ kiểm tra cấu hình, chưa build/run | IMPLEMENTED_NOT_RUN |
| Lint/unit/integration | PDF Bài 6; tích hợp Compose riêng là thiết kế | ci/pipeline.py, ci/compose.test.yaml, frontend/eslint.config.js | Local Ruff/format/ESLint/typecheck/build đạt; 56 passed, 8 skipped. 8 skip cần dịch vụ thật. Mốc 1 có 30/30 Linux nhưng chưa phải image CI SHA mới | VERIFIED trong phạm vi local; integration CI BLOCKED |
| Git workflow, credential setup | PDF Bài 2/6 | CONTRIBUTING.md, PR template, scripts/ci/bootstrap-ci.py | Baseline b4d0fbc đã push origin/main, tác giả cấu hình thật; branch main protection trả 403 do gói Free/private | BLOCKED một phần |
| Jenkins webhook push/PR | PDF Bài 6 | compose.ci.yaml, ci/webhook/, bootstrap-ci.py | Unit kiểm tra HMAC, repo/SHA, PR/fork, replay; chưa có delivery GitHub → Jenkins thật | IMPLEMENTED_NOT_RUN |
| Pipeline build/scan/push | PDF Bài 4/6/11 | Jenkinsfile, ci/{pipeline,security,release}.py | Jenkins parser trên controller cũ xác nhận cú pháp hợp lệ; không cài credential/sửa job cũ. Chưa có build của controller mới | BLOCKED |
| Cổng bảo mật thất bại thật | PDF Bài 11; kịch bản âm là thiết kế brief | ci.security demo-secret/demo-critical | Gitleaks phát hiện 1 token synthetic, exit1; Trivy phát hiện 4 CRITICAL trong alpine:3.12.0, exit1. Chưa có Jenkins failed-build/skip-push evidence | VERIFIED scanner; Jenkins BLOCKED |
| Image gắn SHA, push và digest release | PDF Bài 4; manifest là thiết kế | ci/release.py | Chưa build/scan/push 5 image SHA; chưa có release-manifest. Không đặt digest giả | BLOCKED |

[Bằng chứng local](../evidence/m2-local-20261114T084619Z/metadata.json) ghi HEAD nền, working tree và SHA256 từng file được kiểm tra; đó là mã đang sửa, chưa phải kiểm thử của một commit Mốc 2 cuối cùng. [Chính sách Git](../evidence/m2-git-policy-20261114T081335Z/metadata.json) giữ nguyên lỗi 403. [Backup Docker](../evidence/docker-storage-20261114T073814Z/backup-manifest.json) có hash đối chiếu nguồn khi Docker đã dừng.

Các cổng được triển khai theo hướng fail closed: báo cáo scanner thiếu/rỗng/lỗi không được thông qua; CRITICAL chưa có bản vá vẫn bị chặn; không dùng ignore-unfixed. Trivy quét cả Python lock và Node lock, gồm dev dependencies. Build từ working tree thay đổi hoặc có file chưa tracked bị từ chối. Push kiểm tra commit, image ID, hash báo cáo và JUnit; PR không chạy stage cấp credential registry/deploy. Release dùng 5 image: app dùng chung cho API/publisher/worker, frontend, PostgreSQL, RabbitMQ, Mailpit.

Jenkins riêng ở 18090 có đăng nhập, controller 0 executor, agent Linux non-root, Docker engine rootless riêng; không mount Docker socket host. Engine lồng vẫn cần privileged để khởi tạo rootlesskit: đây là giới hạn cô lập của thiết kế local, cần VM CI riêng ở Mốc 3. Jenkins cũ 8080 không được dùng giữ credential mới.

Blocker ở snapshot14/11 (xem cập nhật15/11 phía trên):

- Docker Desktop đã đọc lại dữ liệu cũ nhưng đĩa C vẫn đang được mount; bản sao trên D chưa active. Không build lớn lên C khi chưa chuyển xong. [Runbook chuyển ổ](../runbooks/docker-storage-migration.md) ghi rõ thử nghiệm cấu hình không có hiệu lực.
- `.registry-token` chưa có tại lần kiểm tra cuối. Git push được cấp quyền; credential Git hiện có không có write:packages. Chỉ nhập PAT classic phù hợp vào file local bị ignore, không vào chat/Git.
- Controller/agent/relay mới chưa build, bootstrap, validate quyền hoặc chạy pipeline; webhook cần URL HTTPS trỏ riêng relay.
- GitHub Free/private không bật được main protection trong repo hiện tại. Giữ repo private. Cần người review thật; không tự tạo review hoặc tác giả thành viên. Chưa có stable semver release.

Chuỗi staging → approval → production là PDF Bài 6 nhưng thuộc triển khai Mốc 3 trong brief. Jenkinsfile có stage dự kiến, `DEPLOY=false` mặc định; ci.deploy từ chối nếu thiếu overlay/credential thật. Chưa có migration Job/overlay/cluster/smoke/rollback để nghiệm thu chuỗi đó. KEDA, Terraform, Ansible và monitoring tiếp tục là yêu cầu bắt buộc ở các mốc sau.

Sau commit67eaf2d, remote scan phát hiện nền Python cũ9CRITICAL, Nginx cũ3, Mailpit cũ3, PostgreSQL1 ở gosu; RabbitMQ0. Dockerfile đã đổi Python3.12.16-slim-trixie, Nginx1.30.6-alpine3.24, Mailpit1.33.1 sang digest nguồn mới được quét0CRITICAL. PostgreSQL giữ dòng17/volume, bỏ binary gosu chỉ dùng khởi động root; image này luôn USERpostgres. **Chưa build/scan image custom hoặc kiểm tra initdb/SMTP/nginx sau đổi nền**. Không suy0CRITICAL của base thành release sạch; [bằng chứng và nguồn](../evidence/m2-base-images-20261114T085952Z/metadata.json).

Cách dựng và lấy evidence còn lại: [CI/CD](ci-cd.md). Chỉ đổi trạng thái Mốc 2 sau khi có pipeline xanh, webhook thật, hai build âm bị chặn trước push, image scan đầy đủ và pull lại bằng digest.


Kiểm chứng gate bổ sung15/11: [Jenkins6/7](../evidence/ci-agent-20261115T064424Z/publish-requested-negative-checks.json) yêu cầu PUBLISH_IMAGES=true, DEPLOY=false nhưng scanner thật phát hiện1secret/4CRITICAL, buildFAILURE và push SKIPPED_FOR_FAILURE; không chỉ chứng minh stage bị tắt bởi tham số. Không đăng nhập/push registry hoặc deploy.
