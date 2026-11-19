# Chuyển Docker sang D – 15/11/2026 giờ Việt Nam

**VERIFIED cho di chuyển ổ và runtime local được giữ lại.** Không phải build image M2/M4, chạy pipeline Jenkins, publish GHCR hoặc provisioning VM/cluster.

- `before-inventory.json`, `after-inventory.json`, `inventory-comparison.json`: Docker engine29.9.3, giữ nguyên14container ID,14volume,15image ID; Jenkins riêng18090 authenticated HTTP200, useSecurity=true, anonymous API403 và folder job giữ nguyên.
- `fresh-backup-manifest.json`: data VHDX13.668.188.160byte được copy khi giữ nguồn mở chỉ đọc độc quyền, đối chiếu SHA256 bản sao; settings cũng được sao lưu. Bootstrap vẫn bị Windows giữ sau khi terminate riêng docker-desktop nên không có bản bootstrap mới trong snapshot này; mọi bản bootstrap đã kiểm hash trước đó được giữ. Không thay thế/xóa backup cũ.
- `migration-request.json`: protocol đọc từ mã tĩnh frontend Docker Desktop đã cài, SHA256 app.asar và payload chỉ đổi vm.resources.wslDataFolder. `GET .../do_changes_need_restart` trả200/true trước áp dụng. Đây là API nội bộ của phiên bản đã cài, không phải CLI công khai.
- `migration-response.json`: backend Docker `POST /app/settings/gui` trả200 và nhận đúng locationD. Full response chỉ ở tmp private; chỉ công bố trường lưu trữ.
- `storage-verification.json`: VHD data và bootstrap trênD bị giữ mở (exclusive read Win32 error32), đường dẫn resolved nằm trênD, source data C không còn; backend setting đúngD. Không tự tạo junction, sửa registry/settings-store hay di chuyển/xóa VHD bằng tay. Chính Docker thực hiện chuyển.
- `application-verification.json`: bảy service dev healthy,13HTTP check200. Bốn container postgres/rabbitmq/mailpit/frontend được start lại từ bản sẵn có, không recreate/build. Container migration/seed giữ exit0 từ lần chạy cũ, không được coi đã chạy lại.
- [Smoke thật](../runtime-20261114T194613Z/metadata.json): frontend→API→PostgreSQL→RabbitMQ→SMTP/Mailpit, đặt lịch có email chứa đúng ID rồi hủy lịch notification SENT; exit0. Dùng tài khoản demo local, không bật fault injection. Không phải integration của source hiện tại vì image dev không được build lại.

Trước chuyển C trống2.183.680.000byte; sau probe C trống15.941.672.960byte (~14,85GiB), D trống8.110.608.384byte (~7,55GiB). Các số là snapshot, không cam kết dung lượng không đổi. Bản active: `D:\DockerData\active\DockerDesktopWSL\disk\docker_data.vhdx`. Giữ bản D cũ, D:\DockerBackup và hai snapshot private trong .ci-local/recovery-backups. Cần tính lại dung lượng trước build lớn; không tự xóa backup.

[Runbook và lịch sử thất bại trước đó](../../runbooks/docker-storage-migration.md). Nguồn cơ chế storage/backup: [Docker settings](https://docs.docker.com/desktop/settings-and-maintenance/settings/), [Docker whole-VM backup](https://docs.docker.com/desktop/settings-and-maintenance/backup-and-restore/). Protocol API lấy từ app đã cài, không suy từ hai trang tài liệu này.
