# An Uyên Hospital · Đặt lịch khám có thông báo

Đồ án DevOps đề tài số 8: React/TypeScript → FastAPI → PostgreSQL/outbox → RabbitMQ → worker email. API, publisher và worker là ba tiến trình riêng; có health, readiness, Prometheus metrics và JSON logs. Chỉ sử dụng dữ liệu giả lập.

**Trạng thái:** Mốc 1 có snapshot Compose dev đạt30/30 Linux và11kiểm tra browser. Giao diện [Soft Minimal](docs/soft-minimal.md) dùng #286789, logo #103783, Inter; đặt lịch3bước và nhắc email có lưu thực tế. **Mốc 2 đang triển khai, chưa nghiệm thu:** [Jenkins/CI và security gates](docs/milestone-2.md) đã có mã, lint/build local đạt và56test passed/8integration skipped; chưa pipeline/webhook/registry digest thật. Baseline b4d0fbc đã push repo private vxxngw/DevOps. Docker đang chuyển dữ liệu sang D; URL/snapshot M1 bên dưới là lịch sử, không khẳng định đang online. Xem [ma trận](docs/compliance-matrix.md), [CI/CD](docs/ci-cd.md) và [evidence](docs/evidence/README.md).

**Mốc 3:** [cấu hình và kiểm chứng chuẩn bị](docs/milestone-3.md) đã có Terraform/Ansible/Kubernetes/HPA/KEDA/TLS/RBAC/backup/rollback. Người dùng chọn chuẩn bị trên máy hiện tại; chưa tạo VM/cluster. [Runbook lab](docs/runbooks/infra-lab.md) và [evidence](docs/evidence/m3-latest.json) phân biệt kiểm tra local với runtime còn bị chặn.

## Khởi động dev (cần Docker engine hoạt động)

Prerequisites: Git, Docker Desktop/Linux engine có Docker Compose; Python 3.12 để sinh env. Khi chạy native/test cần Python 3.12 và Node 24/npm. Cổng dev: 18080, 8000–8002, 5433, 5673, 15673, 15693, 1025, 8025 phải trống; không mở cổng DB/broker/metrics ra Internet. FRONTEND_PORT có thể đổi; 8080 đang được Jenkins sẵn có sử dụng nên được giữ nguyên.

```powershell
python scripts/init-env.py
docker compose up -d --build --wait
```

`init-env.py` tạo secret ngẫu nhiên trong `.env`, không ghi đè và không in secret. Compose dựng DB/broker/Mailpit, chạy migration rồi seed dev, khởi động app. Seed lặp an toàn, không đổi password tài khoản đã có, bị cấm khi ENVIRONMENT=production. Lệnh up/build/wait đã chạy thành công trên máy khảo sát; chưa kiểm chứng dựng toàn bộ IaC/K8s từ máy trắng.

URL dev: [frontend](http://localhost:18080), [API/OpenAPI](http://localhost:8000/docs), [Mailpit](http://localhost:8025), [RabbitMQ management](http://localhost:15673). Frontend/API/Mailpit và management API đã được truy cập thực; endpoint `/health`, `/ready`, `/metrics` của API/publisher/worker (8000/8001/8002) đều200 tại snapshot. Management dùng user `clinic`, mật khẩu trong .env, chỉ dùng local. Đây là HTTP dev; chưa có HTTPS cert-manager.

Tài khoản synthetic: `patient@example.test`, `other@example.test`, `admin@example.test`; mật khẩu đọc **cục bộ** ở `DEMO_PASSWORD` trong .env. Không đưa mật khẩu lên chat/Git. Xem [local setup](docs/local-setup.md) để chạy từng thành phần, migration/seed, đặt lại password và kiểm tra email.

## Kiểm thử và bằng chứng

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe scripts/verify.py
cd frontend
npm ci
npm run build
cd ..
.\scripts\check-ui.ps1
```

Kiểm tra mặc định dùng SQLite riêng và fake channel/sender cho các unit test reliability. Không chứng minh khóa PostgreSQL, RabbitMQ hay SMTP thật. UI check ở trên dùng API thật + SQLite thử riêng, Edge headless; tự dừng hai tiến trình test, không xóa DB dev. Sau khi Compose thật healthy, dùng runner Linux đã được kiểm chứng:

```powershell
.\scripts\check-integration.ps1
```

Integration tạo DB `clinic_test_<uuid>` riêng rồi xóa **DB thử đó**, queue/exchange prefix ngẫu nhiên rồi dọn đúng prefix. Cần role dev được CREATE DATABASE (official POSTGRES_USER dev có quyền này); không chạy bằng production credential. Test SMTP gửi vào Mailpit và thử connection-refused để kiểm tra retry/DLQ/replay, không gửi tải tới người thật. Native `scripts/verify.py --integration` từng treo trên Windows và chưa được coi là pass; có timeout120s. Runner Compose mới đạt30/30. Test nhắc lịch truyền đồng hồ tương lai vào scheduler trên DB test, không tuyên bố đã chờ một giờ thực.

Diễn tập thật trên chính project dev: `.venv/Scripts/python.exe scripts/smoke-runtime.py --faults` (có stop/start broker và SIGKILL đúng worker của clinic-dev, không dùng trên production). Script đã kiểm tra recovery và gỡ delay demo. Browser trên stack thật được kiểm chứng riêng trong evidence; xem local-setup.md để chạy lại.

## Các mốc còn lại

[Kiến trúc](docs/architecture.md), [ADR](docs/decisions.md), [quy trình nhóm](docs/team-workflow.md), [nguồn/phiên bản](docs/versions.md), [security](docs/security.md) và [kịch bản 8 bước](docs/demo-script.md) giải thích yêu cầu và cách kiểm chứng.

Jenkins/registry/webhook cần chạy nghiệm thu theo [Mốc 2](docs/milestone-2.md); hiện bị chặn bởi chuyển Docker và GHCR credential. Terraform tạo3VM, Ansible, k3s/staging/production/TLS/RBAC/HPA/KEDA, Prometheus/Grafana/Alertmanager/EFK còn chưa triển khai. Chưa chọn provider VM/domain/receiver. Không có triển khai hoặc rollback K8s đã chạy để công bố; xem [deploy](docs/runbooks/deploy.md), [rollback](docs/runbooks/rollback.md), [restore](docs/runbooks/restore.md), [alerts](docs/runbooks/alerts.md). Runbook sự kiện dev: [notifications](docs/runbooks/notifications.md).

## Dừng và khắc phục lỗi

`docker compose stop` chỉ dừng các service của project `clinic-dev`; `docker compose down` gỡ container/network của project và giữ named volumes. **Không dùng `down -v` khi muốn giữ dữ liệu**. Dọn volume/DB cần xác nhận đúng project và có backup; không phải bước khởi động lại mặc định. Teardown Terraform chưa có vì chưa provision.

Nếu Docker `EOF`, HTTP 500 hoặc mất engine pipe: kiểm tra `docker version`, trạng thái Docker Desktop/WSL và tài nguyên host. Không tiếp tục coi build/up là thành công. Nếu cổng đã dùng, chọn cổng test khác hoặc dừng đúng tiến trình của mình; không kill dịch vụ không biết chủ sở hữu. Nếu login lỗi, kiểm tra seed/mật khẩu hiện tại, không reset DB. Nếu notification PENDING, kiểm tra publisher/broker/outbox trước; xem runbook. Mọi kiểm tra có evidence và scope riêng trong ma trận.


Phần chuẩn bị **Mốc 4** ở [docs/milestone-4.md](docs/milestone-4.md): Prometheus/Grafana/Alertmanager/EFK, dashboard37panel, alert rules và [runbook quan sát](docs/runbooks/observability.md). Kiểm tra local: `python scripts/install-observability-tools.py` rồi `python scripts/verify-m4-local.py`. [Evidence](docs/evidence/m4-latest.json) chỉ xác nhận parser/schema/unit/fixture; chưa có stack hoặc cảnh báo gửi thật. [Cloud estimate](docs/cloud-cost-estimate.md), [8 bước demo](docs/demo-script.md), [checklist nộp](docs/submission.md), [vấn đáp](docs/viva-preparation.md).
