# Quy trình nhóm [ĐỀ BÀI trang 2 + THIẾT KẾ]

CHƯA HOÀN THÀNH phân công thực: cần tên 3–4 thành viên, đăng ký backend và URL kênh trao đổi. Không coi bảng vai trò dự kiến là bằng chứng đóng góp.

| Vai trò dự kiến | Phụ trách chính | Review chéo | Người thực / GitHub |
|---|---|---|---|
| TV1 (Hoang) | API/UI/event contract, Monitoring, QA | TV3 (Long) | Hoàng |
| TV2 (Vuong) | Điều phối, Docker/Jenkins/CI/registry | TV1 (Hoang) | Vương (`@vxxngw`) |
| TV3 (Long) | Terraform, Ansible, Host Linux, Backup | TV4 (Thien) | Long |
| TV4 (Thien) | Kubernetes, HPA/KEDA, TLS/RBAC, Rollback | TV2 (Vuong) | Nguyễn Thành Thiện (`@Thientao0609`) |

Nhóm chọn một kênh trao đổi thực; ghi quyết định quan trọng vào issue/PR và ADR. Mỗi người hiểu toàn hệ thống để vấn đáp. Không tạo tài khoản, tác giả, PR/review hay lịch sử giả.

Definition of Done: PR có ≥1 review thật; checks liên quan đã chạy và lưu output; security gate không bị bypass; config/deploy/runbook cập nhật; tiêu chí ma trận có evidence đúng môi trường; chưa chạy ghi IMPLEMENTED_NOT_RUN/BLOCKED. Main bảo vệ, branch `feat/...`, `fix/...`, commit Conventional Commits, tag release semver. Thay đổi migration phải tương thích bản app trước cho rollback.

Kiểm chứng quy trình cần remote branch rules, PR đã review/merge, Jenkins webhook build, tag và commit của từng người. Hiện chỉ có mã local, chưa chứng minh các mục đó.
