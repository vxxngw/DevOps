# Toàn bộ unit test trên Linux – source 0bd3fb3

[Metadata](metadata.json) và [JUnit](junit.xml) xác nhận **110 passed, 8 skipped, 0 failed/error**. [Log](full-unit.log) giữ đầu ra thật, gồm cảnh báo TestClient/httpx hiện có; không tắt cảnh báo để che lỗi.

Source được xuất từ Git commit `0bd3fb303f50999a54d08648f2c7d9a83edc6188`, bỏ thư mục docs để giảm dữ liệu chuyển; metadata lưu SHA256 và kích thước archive. Không đưa `.env`, token, dump, state hoặc dữ liệu local vào agent. Chạy bằng UID1000 trong thư mục riêng có khoảng trắng trên agent Linux đang rảnh, dùng Python/dependency đã cài sẵn. Workspace chạy Jenkins được giữ nguyên.

Lượt này gọi `pytest tests ci/tests` trực tiếp, dùng SQLite và fake transport theo fixture. 8 skip thuộc integration cần môi trường riêng, chưa được tính là đã chạy PostgreSQL/RabbitMQ/SMTP. Không build/pull image, không publish, không tạo VM/cluster hoặc khởi chạy Jenkins job.

[Kiểm tra đường dẫn Linux riêng](../linux-paths-20261115T141048Z/README.md) xác nhận thêm 7 source Ansible và 6 Bash script bằng công cụ thật. [Backup/restore dev](../backup-restore-20261115T134405Z/README.md) có PostgreSQL/API thực và phạm vi riêng. Full Jenkins/image verification cho source bổ sung vẫn chờ đủ dung lượng; GHCR chờ credential đúng quyền.

[Preflight Windows](local-preflight.json) là snapshot độc lập sau lượt kiểm đường dẫn: ổ hệ thống còn khoảng1,73GiB, file `.registry-token` chưa có; scope header của Git credential hiện tại không có `write:packages`. Không ghi token vào evidence. Quét secret của nội dung chuẩn bị commit được ghi riêng trong `indexed-secret-scan.json` sau khi scanner thực sự hoàn tất.
