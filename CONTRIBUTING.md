# Đóng góp

Đọc docs/compliance-matrix.md và docs/guides/architecture.md trước khi đổi mã. Dùng nhánh theo tính năng; commit dạng `feat(api): ...`, `fix(worker): ...`, `docs: ...`. Mọi thay đổi lên main qua PR có ít nhất một review thật. Release dùng tag semver sau checks. Không tự tạo lịch sử đóng góp cho thành viên khác.

Trước PR chạy `.venv/Scripts/python.exe scripts/ci/install-ci-tools.py`, rồi `scripts/ci/verify-m2-local.py` bằng cùng Python; gồm lint/typecheck/build/unit, Gitleaks, Trivy lockfile và demo lỗi scanner. Khi có Docker CI chạy pipeline integration riêng, mọi skip integration đều chặn publish. Kiểm tra UI khi sửa giao diện bằng `scripts/dev/check-ui.ps1` (Windows + Edge). Lưu evidence không chứa .env/token/địa chỉ thật. Không đánh dấu test broker pass từ fake channel. Xem docs/guides/ci-cd.md.

Không commit secret/state/backup dữ liệu. `.env.example` chỉ mô tả cấu hình. Thay đổi contract phải có schema/version; không xóa dữ liệu hoặc chạy migration phá lịch sử trong deploy thông thường. GitHub Free/private hiện trả403 khi bật main protection; đây là blocker thực, chưa đổi visibility. Webhook/registry cần kiểm chứng runtime theo docs/guides/ci-cd.md, chưa được bật chỉ bởi file này.
