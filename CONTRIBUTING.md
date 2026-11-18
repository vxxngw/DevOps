# Đóng góp

Đọc docs/compliance-matrix.md và docs/guides/architecture.md trước khi đổi mã. Quy trình nhóm, phân vai và vòng review ở [docs/guides/team-workflow.md](docs/guides/team-workflow.md). Không tự tạo lịch sử đóng góp cho thành viên khác.

## Git

```bash
git config user.name "Tên thật"
git config user.email "email-gắn-với-tài-khoản-GitHub"
pip install pre-commit
pre-commit install   # cài hook pre-commit (ruff check/format) và commit-msg (Conventional Commits)
```

- Làm trên nhánh của mình (`Hoang`, `Long`, `Thien`, `VietAnh`, hoặc `codex/<task>`); đồng bộ `origin/main` trước khi bắt đầu.
- Commit theo Conventional Commits: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`, ví dụ `fix(worker): retry khi SMTP timeout`.
- `main` được bảo vệ: chỉ nhận PR có ≥1 approve, không push thẳng/force-push. Tiêu đề PR cũng phải theo Conventional Commits (workflow `pr-title`), merge bằng **Squash and merge**.
- Release do release-please quản lý: sau mỗi merge vào main, bot mở Release PR cập nhật `CHANGELOG.md`; merge Release PR thì tạo tag semver `vX.Y.Z`. Không tự gắn tag tay.

## Kiểm tra trước PR

Trước PR chạy `.venv/Scripts/python.exe scripts/ci/install-ci-tools.py`, rồi `scripts/ci/verify-m2-local.py` bằng cùng Python; gồm lint/typecheck/build/unit, Gitleaks, Trivy lockfile và demo lỗi scanner. Khi có Docker CI chạy pipeline integration riêng, mọi skip integration đều chặn publish. Kiểm tra UI khi sửa giao diện bằng `scripts/dev/check-ui.ps1` (Windows + Edge). Lưu evidence không chứa .env/token/địa chỉ thật. Không đánh dấu test broker pass từ fake channel. Xem docs/guides/ci-cd.md.

Không commit secret/state/backup dữ liệu. `.env.example` chỉ mô tả cấu hình. Thay đổi contract phải có schema/version; không xóa dữ liệu hoặc chạy migration phá lịch sử trong deploy thông thường. Repo public nên mọi file commit đều công khai. Webhook/registry cần kiểm chứng runtime theo docs/guides/ci-cd.md, chưa được bật chỉ bởi file này.
