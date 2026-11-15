# Chạy Mốc 1 và phạm vi kiểm chứng

Hướng dẫn Windows PowerShell; Linux/macOS dùng `.venv/bin/python` thay `.venv/Scripts/python.exe` và `export PYTHONPATH=services`. Secrets chỉ lưu local hoặc kho bí mật của môi trường. `.env` có secret dev sinh ngẫu nhiên và bị ignore; không dùng tài khoản demo cho production.

## Compose

Từ root: `python scripts/dev/init-env.py` (một lần), rồi `docker compose up -d --build --wait`. Migration và seed là hai job riêng trong Compose dev. Kiểm tra `docker compose ps -a`, endpoint health/ready và Mailpit. Không chạy `docker compose config` không lọc vào evidence vì có thể in secret; dùng `docker compose config --quiet` để kiểm tra cú pháp.

Để chạy migration/seed thủ công trên DB dev: `docker compose run --rm migrate`, `docker compose run --rm seed`. Không dùng seed để đổi password hiện có. Không dùng migrate downgrade trong deploy thông thường; rollback app phải theo migration tương thích.

## Native (cần PostgreSQL/RabbitMQ/Mailpit thật)

```powershell
docker compose up -d --wait postgres rabbitmq mailpit
$env:PYTHONPATH = 'services'
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m clinic.seed
.\.venv\Scripts\python.exe -m uvicorn clinic.api:app --host 127.0.0.1 --port 8000 --no-access-log --log-config services/logging.json
```

Hai terminal khác, từ root và có PYTHONPATH=services: `python -m clinic.runtime publisher --port 8001`, `python -m clinic.runtime worker --port 8002` (dùng python trong .venv). Frontend: `cd frontend`, `npm ci`, `npm run dev`; Vite proxy /api đến localhost:8000. Worker/publisher reconnect có backoff khi dependency lỗi; API pool_pre_ping loại kết nối DB hỏng, request khi DB unavailable trả 503, request sau phục hồi có thể hoạt động lại.

## Đặt lại password demo

Dừng dùng tài khoản cũ, chọn `DEMO_EMAIL` và password mới trong `DEMO_PASSWORD` qua biến môi trường/.env trên máy riêng; chạy `python -m clinic.reset_password`. Không truyền password ở tham số dòng lệnh hoặc ghi vào log. Lệnh cấm production; người vận hành phải dùng quy trình quản lý tài khoản riêng cho production. Đổi JWT_SECRET làm token cũ mất hiệu lực; chỉ sửa env rồi restart app, không đổi DB password bằng cách chỉ sửa env của volume DB đã tạo.

## Kiểm chứng

`scripts/dev/verify.py` lưu metadata, source hashes, stdout/stderr đã che DSN/JWT, JUnit và exit code; commit ghi UNCOMMITTED nếu chưa có commit. `--integration` native tạo DB/queue test riêng nhưng một lượt Windows đã treo, không tính pass; có timeout120s. Dùng `scripts/dev/check-integration.ps1` sau Compose up: runner Linux với compose.test.yaml đã đạt30/30 sau bổ sung nhắc lịch. Khi thiếu dịch vụ, integration thất bại là kết quả đúng, không đổi sang fake để pass.

`scripts/dev/check-ui.ps1` chạy Edge headless → Vite:15173 → FastAPI:18000 → SQLite thử riêng trong tmp; kiểm tra login, chọn slot, đặt/hủy, phân tách lịch patient, admin thêm bác sĩ/slot, ảnh desktop/mobile, không tràn ngang. Kịch bản này không gửi email và không chứng minh cạnh tranh PostgreSQL. Nó không đụng tiến trình đã chiếm cổng; cleanup chỉ dừng hai process do script tạo. Metadata ảnh phải ghi phạm vi này.

Browser trên stack Compose thật: từ frontend, build bằng `npm run build`, đặt env `CLINIC_BASE_URL=http://127.0.0.1:18080`, chạy `node tests/smoke.cjs ../docs/evidence/<thư-mục-mới>`. Script đọc DEMO_PASSWORD cục bộ; tạo/hủy hai lịch synthetic để kiểm tra giờ hết chỗ và booking, thêm bác sĩ/slot thử rồi dọn đúng tài nguyên đã tạo; ghi11checks và ảnh. Lượt Soft Minimal Compose thật đã pass; [inspection riêng](soft-minimal.md) so served JS/CSS với dist. Không chạy đồng thời với integration đếm email trong Mailpit.

Nhắc lịch: mặc định60phút, cấu hình `REMINDER_LEAD_MINUTES`; giá trị hợp lệ1–1440. API và publisher phải cùng giá trị; sau đổi env phải recreate service để nạp. Công tắc có trong bước Xem lại và Lịch hẹn của tôi; khi đã qua hạn bật nhắc, email xác nhận vẫn có. Tác vụ đã lưu không tự đổi `due_at` khi sửa cấu hình. Client API cũ không gửi tùy chọn thì mặc định tắt; migration không tự bật nhắc cho dữ liệu cũ. Xem [luồng và bằng chứng](soft-minimal.md).

Nginx dev dùng resolver Docker127.0.0.11 để không giữ IP API cũ khi recreate. Cấu hình Kubernetes sau này phải dùng DNS/resolver của cluster, không copy nguyên IP này. Nếu Git báo dubious ownership do repo được init bằng tài khoản sandbox, sau khi xác nhận đúng workspace có thể chạy lệnh với phạm vi duy nhất: `git -c safe.directory=D:/CODE/OOPs/Do_An status`; không thêm wildcard trust toàn bộ máy.
