# Backup và khôi phục PostgreSQL

Cập nhật 15/11/2026. PDF trang 6 yêu cầu runbook khôi phục DB. Dùng `pg_dump -Fc`, SHA256, retention 7 ngày, systemd timer và DB khôi phục riêng là lựa chọn triển khai của nhóm.

## Đã kiểm chứng và phần còn thiếu

[Lượt dev thực tế](../evidence/backup-restore-20261115T134405Z/metadata.json) đã tạo dump 35.589 byte trên PostgreSQL 17.12, kiểm SHA256, restore vào DB mới, so sánh dữ liệu **9 bảng** và **46 định nghĩa constraint/index**, rồi chạy 9 kiểm tra API/nghiệp vụ. Đã kiểm từ chối DB tồn tại và checksum sai; retention xóa đúng file thử cũ, giữ file khác và backup mới. DB nguồn không đổi, DB restore thử đã được xóa sau kiểm chứng. Dump được giữ local với quyền truy cập riêng, không commit.

Thời gian dev từ bắt đầu restore đến hết business smoke là **6,945 giây**, gồm kiểm dữ liệu và các kiểm tra từ chối. Đây là số đo trên dữ liệu nhỏ, chưa phải RTO sự cố production. RPO sự cố chưa đo. Lượt này không chạy publisher/worker/SMTP trên DB phục hồi; chỉ xác nhận API và hai sự kiện outbox. Timer, health host Linux, VM/Ansible, cluster staging/production, offsite và HA chưa kiểm chứng runtime.

Ba lượt lỗi trước khi hoàn thiện bộ so sánh schema vẫn giữ trong [báo cáo evidence](../evidence/backup-restore-20261115T134405Z/README.md). PostgreSQL có thể chuyển `ARRAY[varchar]::text[]` thành cast `text` trên từng phần tử. Bộ kiểm chỉ chuẩn hóa đúng các dạng tương đương này; vẫn so sánh giá trị, toán tử, kiểu khác và giới hạn kiểu. Không bỏ kiểm constraint/index để làm kết quả đạt.

## Diễn tập dev trên checkout hiện tại

Điều kiện: Docker local, PostgreSQL project `clinic-dev` healthy, `.env` đúng credential local, Python đã cài `requirements.lock`; Windows cần Git Bash. Không cần build image mới. Chạy từ root:

```powershell
.\.venv\Scripts\python.exe scripts/dev/check-backup-restore.py
```

Linux dùng Python trong virtualenv tương ứng. Script tìm root theo file sentinel, không gắn đường dẫn ổ D. Runner giới hạn DB tối đa 128 MiB để fingerprint trong bộ nhớ, yêu cầu dung lượng còn ít nhất `5 × pg_database_size + 2 GiB`. Với dữ liệu lớn cần đối chiếu theo chunk và đo tải riêng.

Runner thực hiện:

1. Xác nhận Docker endpoint local, container có label project `clinic-dev`, service `postgres` và đang chạy. Tạo `.infra-local/db-backups/<run-id>`; Windows giới hạn ACL cho user chạy và SYSTEM.
2. Lưu fingerprint tổng hợp DB nguồn; không đưa dữ liệu hàng hoặc credential vào evidence.
3. Chạy chính `scripts/infra/backup.sh dev`; kiểm custom dump, size và SHA256. Thử retention bằng bản sao do lượt này tạo trong thư mục riêng.
4. Chạy chính `scripts/infra/restore.sh dev <dump> clinic_restore_<run-id>`. `createdb` phải tạo mới, không ghi đè DB sẵn có. Đối chiếu dữ liệu và schema.
5. Kiểm DB tồn tại bị từ chối mà dữ liệu không đổi; bản sao sai checksum bị từ chối trước khi tạo DB.
6. Dùng source API hiện tại và DB phục hồi để đăng nhập user thử, tạo bác sĩ/slot thử, đặt lịch, replay idempotent, từ chối slot đã đặt, hủy và kiểm outbox. Không migrate hoặc seed để che lỗi backup.
7. Kiểm DB nguồn không đổi. Chỉ xóa DB mà lượt này xác nhận đã tạo mới qua marker `restore_database_created`; giữ dump và xuất log đã che secret/metadata vào `docs/evidence/backup-restore-<UTC>/`.

Nếu restore lỗi sau khi tạo DB, runner vẫn thử dọn DB thuộc lượt đó. Nếu cleanup thất bại, kiểm tên DB/ownership trong metadata trước khi xử lý; không xóa hàng loạt theo prefix. Dump/checksum không được đưa vào Git, artifact công khai hoặc Docker context. Không dùng `set -x` hay in `.env` khi chẩn đoán.

## Vận hành staging bằng Ansible/systemd

Đây là quy trình đã chuẩn bị, **chưa chạy trên VM/cluster**. Role backup cài `backup.sh`, `restore.sh`, `backup-common.sh` từ `scripts/infra` vào `/usr/local/sbin/clinic-*`; `host-health.sh` do role common cài trên mọi máy kèm timer 15 phút. Bản chạy thật trên một VM cloud (hồ sơ `dev`) ở [linux-cloud-lab.md](linux-cloud-lab.md). CI kiểm mọi source copy/template và Bash từng file, kể cả thư mục con. Kiểm tĩnh không thay playbook thật hoặc recap idempotency.

Timer dự kiến chạy hằng ngày 02:15 giờ host, delay ngẫu nhiên 300 giây, `Persistent=true`; kiểm timezone trước demo. Dump staging/production ở `/srv/clinic-backups/NAMESPACE`, ngoài DB pod/node lưu trữ, umask 077/checksum. Retention chỉ áp dụng tên backup đúng prefix trong thư mục đã kiểm. Node exporter textfile xuất trạng thái lần chạy và thời điểm thành công gần nhất; cần alert lỗi/mất metric/backup cũ theo [runbook cảnh báo](alerts.md).

```bash
sudo systemctl start clinic-backup@staging.service
sudo journalctl -u clinic-backup@staging.service --no-pager
sudo systemctl list-timers 'clinic-backup@*'
# Thay timestamp và tên DB bằng giá trị thực, DB phải chưa tồn tại:
sudo /usr/local/sbin/clinic-restore.sh staging /srv/clinic-backups/staging/clinic-staging-YYYYMMDDTHHMMSSZ.dump clinic_restore_DRILL_ID
```

Lưu journal/timestamp/exit code, artifact/checksum/size, Alembic, dữ liệu/constraint và business smoke trên app riêng. Operator giữ DB staging thử để kiểm thêm rồi dọn đúng DB đã tạo; shell restore không tự xóa. Credential chỉ đọc từ env bên trong PostgreSQL pod, không nằm trong argv/log. Host cần quyền Kubernetes đúng namespace theo [lab](infra-lab.md).

## Khôi phục khi có sự cố production

Ghi thời điểm sự cố và backup cuối dùng được để tính RPO. Khi cần, dừng ghi theo kế hoạch; chọn artifact, copy sang môi trường phục hồi riêng, kiểm checksum và restore bằng quyền được cấp cho sự cố. Script tự động từ chối profile production: review schema, dữ liệu, secret, kết nối và nghiệp vụ trước khi phê duyệt cutover.

RTO tính đến khi nghiệp vụ phục hồi thành công, gồm hạ tầng/kết nối/cutover thực tế. Không lấy thời gian `pg_restore` hoặc số đo dev thay RTO production. App rollback và phục hồi dữ liệu là hai quy trình riêng; xem [rollback](rollback.md).

Backup cùng server chưa phải offsite/HA và vẫn mất khi Terraform destroy server. Trước teardown xuất bản đã kiểm checksum ra ngoài cả lab; ghi nơi lưu và quyền truy cập. Không xóa backup Docker trên ổ D để chạy drill.
