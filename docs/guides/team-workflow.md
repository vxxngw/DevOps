# Quy trình nhóm [ĐỀ BÀI trang 2 + THIẾT KẾ]

Nhóm gồm **Vuong, Hoang và Long** theo thông tin người dùng. Cần điền GitHub từng người, xác nhận đăng ký backend và URL kênh trao đổi. Bảng dưới là phân công đề xuất cho công việc tiếp theo, chưa phải bằng chứng đóng góp. Bắt đầu từ [checklist onboarding và backlog cho 3 thành viên](team-onboarding.md).

| Vai trò dự kiến | Phụ trách chính | PR được review bởi | Người thực |
|---|---|---|---|
| TV1 / A | API/UI/event contract, QA và monitoring/logging/alert | TV3 / Long | Hoang; GitHub chưa điền |
| TV2 / B | Docker/Jenkins/registry, security, release và điều phối Git | TV1 / Hoang | Vuong; GitHub chưa điền |
| TV3 / C | Host/Linux, Terraform/Ansible/K8s, backup/restore | TV2 / Vuong | Long; GitHub chưa điền |

Vai trò D trong kịch bản demo cũ được chia cho TV1 (monitoring/tests) và TV2 (security), TV3 hỗ trợ operator/cluster. Owner cho từng bước đã được ánh xạ trong checklist onboarding. Mỗi người có PR đầu tiên và review chéo bằng tài khoản thật.

Nhóm chọn một kênh trao đổi thực; ghi quyết định quan trọng vào issue/PR và ADR. Mỗi người hiểu toàn hệ thống để vấn đáp. Không tạo tài khoản, tác giả, PR/review hay lịch sử giả.

Definition of Done: PR có ≥1 review thật; checks liên quan đã chạy và lưu output; security gate không bị bypass; config/deploy/runbook cập nhật; tiêu chí ma trận có evidence đúng môi trường; chưa chạy ghi IMPLEMENTED_NOT_RUN/BLOCKED. Dùng nhánh `codex/tv1/<task>`, `codex/tv2/<task>`, `codex/tv3/<task>`, Conventional Commits và semver khi đủ điều kiện release. Main protection cần kiểm quyền/enforcement thực, không coi quy định trong tài liệu là đã bật. Thay đổi migration phải tương thích bản app trước cho rollback.

Kiểm chứng quy trình cần remote branch rules, PR đã review/merge, Jenkins webhook build, tag và commit của từng người. Repo đã được push và CI/webhook push đã có bằng chứng tại [CI runtime](../evidence/ci-runtime-latest.json); tên ba thành viên đã được người dùng cung cấp, còn GitHub, xác nhận phân công, review/merge, semver và đóng góp của đủ ba người vẫn cần bằng chứng thật. Kết quả CI hiện có không được tính thành đóng góp cá nhân cho người chưa thực hiện.
