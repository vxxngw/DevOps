# Bàn giao 4 người và kiểm tra chỉ đọc 16/11/2026

Thời điểm khảo sát: **03:14:50 ngày 16/11/2026 Việt Nam**, tương ứng 20:14:50 UTC ngày 15/11; Jenkins được đọc lại lúc 03:16:08 Việt Nam. Source trước chỉnh tài liệu: `adb5dbdc692a0aaa6d4e710c5143f223abb4c032`, nhánh `codex/backup-restore-verification`, working tree sạch trước khi tạo bundle này. Tài liệu tiếp theo được sửa trên `codex/team-four-handoff`.

[metadata.json](metadata.json) là kết quả thật của các lệnh chỉ đọc (`docker info`, `docker ps`, HTTP GET, Git status/rev-parse và GitHub REST GET). Không chạy build, publish, deploy, fault injection hoặc đổi cài đặt repo. Không thu thập giá trị credential, env, mật khẩu, log bệnh nhân hoặc nội dung email.

| Phần | Quan sát thực tế | Phạm vi và giới hạn |
|---|---|---|
| Docker | Engine 29.9.3; 4 container clinic-ci và 7 clinic-dev healthy | Trạng thái container ở thời điểm đọc, không phải một lượt build mới |
| Ứng dụng | Frontend và Mailpit HTTP200; `/health`, `/ready`, `/metrics` ở cả 3 backend đều200 (11 URL) | Chỉ GET không thay dữ liệu; không chạy lại booking/email smoke hoặc load test |
| Jenkins | #14 SUCCESS, không building, source đúng `adb5dbd`, publish/deploy=false; anonymous API403 | Đọc lại build đã có; lỗi đọc tạm trước đó do URL `tree` trong helper có thừa dấu `]`, không phải Jenkins bị dừng. Truy vấn hợp lệ dùng tham số `tree` đã đọc được |
| CI đầy đủ trước đó | [Jenkins13/runtime](../backup-ci-runtime-20261115T142446Z/README.md) | 110 unit đạt/8 bỏ qua, 33 integration đạt/0 bỏ qua, 5 image/dependency0CRITICAL và stack SHA đã kiểm tại source `d2ba14c`; không tuyên bố chạy lại cho tài liệu mới |
| Git | Organization private `vuongvo2207-gmail-com/DevOps`, repo ID1457478642; main protected=false, protection/rulesets403 | Main SHA `5cac55cd32b0a4466d6a6eb05236c517fd3c7101`; không PUT hoặc đổi main/visibility/gói |
| PR/tag | Một PR mở #2, draft, base `codex/milestone-2`, head `codex/milestone-3`; danh sách tag rỗng | Chưa chứng minh PR phù hợp main/review, semver và commit của đủ 4 người |
| Credential GHCR | `.registry-token` chưa tồn tại | Chỉ kiểm tồn tại; chưa đăng nhập/push/pull registry. Không in credential Git đã cấu hình |
| Dung lượng | C khoảng0,20GiB, D9,09GiB | Không chạy build lớn hoặc tạo VM. Không xóa backup hoặc thay đổi Docker/WSL/pagefile |

Kết nối GitHub của ứng dụng chưa đọc được repo private (404/422). Kiểm chứng GitHub REST trong bundle dùng credential Git đã cấu hình và trả200 cho đúng repo ID; không thay credential hoặc cấp quyền mới. Đây là giới hạn của kết nối, không kết luận repo mất dữ liệu.

## Đồng bộ phân công

[Google Sheet hiện có](https://docs.google.com/spreadsheets/d/1py3DJf2rO_x2zK0-LcE8tERMtrn2S5lINx7nbnM8-48/edit) được đọc lại: 3 tab, 4 thành viên, 50 task; Hoang11, Vuong14, Long13, Thien12; số task đã đóng vẫn0. Không ghi thay trạng thái cá nhân hoặc tạo commit/review đứng tên thành viên khác.

Repo đồng bộ [onboarding](../../guides/team-onboarding.md), [quy trình nhóm](../../guides/team-workflow.md), [8 demo](../../guides/demo-script.md), [hồ sơ nộp](../../guides/submission.md), [Mốc2](../../guides/milestone-2.md) và [ma trận](../../compliance-matrix.md). Thien nhận Kubernetes/HPA/KEDA/TLS/RBAC/rollback; Long giữ host/Terraform/Ansible/Bash/backup/chi phí; Hoang app/QA/monitoring; Vuong Git/CI/release.

PDF trang1–3 được đọc lại: local cần3VM; RAM32GiB/disk160GiB là dự trù thiết kế. Restore drill là nâng cao Bài3; KEDA là bắt buộc đề tài8. Chưa VM/cluster/TLS/HPA/KEDA/monitoring/alert delivery runtime. Tài liệu dự kiến cho PR đầu tiên của thành viên vẫn là task chưa hoàn thành.

Kiểm tra tài liệu, hash nguồn và kết quả `git diff --check` được ghi tại [checks.json](checks.json). Chỉ các phép kiểm thực sự đã chạy mới được ghi pass. Jenkins14 xác nhận mã cũ; không phải CI của nhánh tài liệu mới. Push vẫn chặn ở dung lượng host vì webhook nhận push sẽ tự xếp build.
