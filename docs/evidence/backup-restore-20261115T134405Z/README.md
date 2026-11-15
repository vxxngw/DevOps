# Backup/restore dev đã chạy thật – 15/11/2026

[Metadata](metadata.json) ghi PASS trên PostgreSQL 17.12, DB nguồn `clinic` 8.517.299 byte. Dump 35.589 byte có SHA256 `7c1ca72c50b835f515aa873e66bce1ef11c3b10985d179865262537582ad7dbf`; dump ở `.infra-local/db-backups/eb63f6477a8c4ccb810f/dev`, bị loại khỏi Git/Docker context và giữ với ACL riêng.

Đã chạy chính Bash backup/restore profile dev, so count + SHA256 dữ liệu **9 bảng**, kiểm **46 constraint/index definitions** sau chuẩn hóa đúng các dạng cast varchar-array/text tương đương của PostgreSQL. Giữ raw schema trước/sau; không sửa schema DB nguồn để hash khớp.

9 kiểm tra API trên DB mới qua: đúng DB riêng, Alembic head khớp không migrate, login user thử, admin tạo doctor/slot, booking có reminder, replay idempotent, slot đã đặt trả 409, cancel trả slot, đúng hai outbox event. Chưa chạy broker/worker/SMTP trên bản phục hồi.

Retention thử bằng file riêng đã xóa đúng dump/checksum cũ, giữ file khác và dump mới. Restore vào DB tồn tại trả lỗi và không đổi dữ liệu. Bản sao sai checksum bị từ chối trước khi tạo DB. Các exit code khác 0 này là kết quả mong đợi của kiểm tra từ chối, không phải bỏ qua lỗi restore.

Dev restore → hết business smoke **6,945 giây**, gồm validation và negative checks; chưa đo RPO/RTO sự cố production. DB nguồn giữ fingerprint, DB thử duy nhất do lượt này tạo đã dọn; dump riêng được giữ. [Runbook](../../runbooks/restore.md) có điều kiện, giới hạn và cách chạy lại.

Các lượt chưa đạt giữ riêng:

- [13:39:46Z](../backup-restore-20261115T133946Z/metadata.json): dữ liệu bảng khớp, hash text schema khác do PostgreSQL viết lại array casts; FAIL, đã dọn DB thử.
- [13:40:49Z](../backup-restore-20261115T134049Z/metadata.json): tái hiện kèm schema diagnostic; FAIL, đã dọn DB thử.
- [13:43:06Z](../backup-restore-20261115T134306Z/metadata.json): chuẩn hóa đầu chưa gồm dấu ngoặc literal trong partial index; FAIL, đã dọn DB thử.

Lượt PASS trên working tree chưa commit, base `008183a`; metadata giữ hash source kiểm chứng. Không coi đây là Jenkins build, image publish, timer, Ansible convergence hoặc cluster restore.
