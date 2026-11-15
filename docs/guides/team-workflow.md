# Quy trình nhóm [ĐỀ BÀI trang 2 + THIẾT KẾ]

Nhóm gồm **Vuong, Hoang, Long và Thien**, đồng bộ 16/11/2026 với [bảng phân công 50 task](https://docs.google.com/spreadsheets/d/1py3DJf2rO_x2zK0-LcE8tERMtrn2S5lINx7nbnM8-48/edit). Cần điền GitHub từng người, xác nhận đăng ký backend và URL kênh trao đổi. Đây là phân công cho công việc tiếp theo, chưa phải bằng chứng đóng góp. Bắt đầu từ [checklist onboarding và backlog cho 4 thành viên](team-onboarding.md).

| Vai trò dự kiến | Phụ trách chính | PR được review bởi | Người thực |
|---|---|---|---|
| TV1 | API/UI/event contract, QA và monitoring/logging/alert | TV3 / Long | Hoang; GitHub chưa điền |
| TV2 | Docker/Compose/Jenkins/GHCR, CI security, release, Git | TV1 / Hoang | Vuong; GitHub chưa điền |
| TV3 | Host/Linux/Bash, Terraform/Ansible, backup/timer, chi phí | TV4 / Thien | Long; GitHub chưa điền |
| TV4 | Kubernetes, HPA/KEDA, TLS/RBAC, rollout/rollback | TV2 / Vuong | Thien; GitHub chưa điền |

Vòng review: **Vuong → Hoang → Long → Thien → Vuong**. Kịch bản demo dùng tên thật, không dùng các chữ A/B/C/D của bản cũ. Thien hỗ trợ Hoang phần operator/cluster; Long bàn giao host/node Ready, Vuong bàn giao image/CI. Mỗi người có PR đầu tiên và review chéo bằng tài khoản thật.

Nhóm chọn một kênh trao đổi thực; ghi quyết định quan trọng vào issue/PR và ADR. Mỗi người hiểu toàn hệ thống để vấn đáp. Không tạo tài khoản, tác giả, PR/review hay lịch sử giả.

Definition of Done: PR có ≥1 review thật; checks liên quan đã chạy và lưu output; security gate không bị bypass; config/deploy/runbook cập nhật; tiêu chí ma trận có evidence đúng môi trường; chưa chạy ghi IMPLEMENTED_NOT_RUN/BLOCKED. Dùng nhánh `codex/tv1/<task>`, `codex/tv2/<task>`, `codex/tv3/<task>` hoặc `codex/tv4/<task>`, Conventional Commits và semver khi đủ điều kiện release. Main protection cần kiểm quyền/enforcement thực, không coi quy định trong tài liệu là đã bật. Thay đổi migration phải tương thích bản app trước cho rollback.

Kiểm chứng quy trình cần remote branch rules, PR đã review/merge, Jenkins webhook build, tag và commit của từng người. Repo thuộc Organization `vuongvo2207-gmail-com/DevOps`, vẫn private. [Đọc lại 16/11](../evidence/team-four-handoff-20261115T201450Z/README.md): main protected=false, API protection/rulesets 403, chưa có tag; PR #2 đang draft và base không phải main. CI/webhook push có [bằng chứng riêng](../evidence/ci-runtime-latest.json). GitHub, kênh trao đổi, đăng ký lớp, review/merge, semver và đóng góp của đủ 4 người còn cần xác nhận thật. Kết quả CI hiện có không được tính thành đóng góp cá nhân cho người chưa thực hiện.
