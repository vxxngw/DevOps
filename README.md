# An Uyên Hospital · Đặt lịch khám có thông báo

Repo public hiện tại: [vxxngw/DevOps](https://github.com/vxxngw/DevOps) (chuyển từ Organization `vuongvo2207-gmail-com`, cùng repository ID; URL cũ tự redirect).

Nhóm **4 thành viên: Vuong, Hoang, Long, Thien**, bắt đầu từ [checklist onboarding](docs/guides/team-onboarding.md) và [bảng phân công 50 task](https://docs.google.com/spreadsheets/d/1py3DJf2rO_x2zK0-LcE8tERMtrn2S5lINx7nbnM8-48/edit). GitHub/kênh trao đổi thực tại [quy trình nhóm](docs/guides/team-workflow.md); trạng thái kiểm chứng xem [ma trận](docs/compliance-matrix.md) và [CI evidence](docs/evidence/ci-runtime-latest.json).

**Đọc lại 16/11/2026:** [bằng chứng bàn giao 4 người](docs/evidence/team-four-handoff-20261115T201450Z/README.md) xác nhận Docker/container healthy, 11 endpoint trả 200 và Jenkins #14 SUCCESS cho `adb5dbd` (publish/deploy=false). Không chạy build mới của thay đổi tài liệu: C chỉ còn khoảng 0,20GiB; GHCR credential chưa có, main protection vẫn 403. VM/cluster/monitoring runtime còn bị chặn.

Đồ án DevOps đề tài số 8: React/TypeScript → FastAPI → PostgreSQL/outbox → RabbitMQ → worker email. API, publisher và worker là ba tiến trình riêng; có health, readiness, Prometheus metrics và JSON logs. Chỉ sử dụng dữ liệu giả lập.

**Trạng thái 15/11/2026:** source `d2ba14c` có **Jenkins #13 SUCCESS** qua webhook GitHub202:110unit đạt/8bỏ qua,33integration đạt/0bỏ qua,5image SHA/dependency0CRITICAL. Stack đúng image ID đã scan có7dịch vụ healthy/non-root, migration/seed0, health/metrics/JSON và email đặt/hủy qua, cleanup0. Xem [bằng chứng](docs/evidence/backup-ci-runtime-20261115T142446Z/README.md), [CI runtime](docs/evidence/ci-runtime-latest.json) và [bố cục source](docs/guides/source-structure.md). GHCR push/pull digest, PR/review và staging/production chưa hoàn tất; publish/deploy đều tắt. Docker data ở D; vẫn đo dung lượng Windows trước build lớn.

**Mốc 3:** [cấu hình và kiểm chứng chuẩn bị](docs/guides/milestone-3.md) đã có Terraform/Ansible/Kubernetes/HPA/KEDA/TLS/RBAC/backup/rollback. Người dùng chọn chuẩn bị trên máy hiện tại; chưa tạo VM/cluster. [Runbook lab](docs/runbooks/infra-lab.md) và [evidence](docs/evidence/m3-latest.json) phân biệt kiểm tra local với runtime còn bị chặn.

**Bổ sung sau refactor:** đã sửa source động của Ansible backup role và kiểm Bash đệ quy từng file; Jenkins13 đã chạy qua các thay đổi này. [Backup/restore dev thật](docs/evidence/backup-restore-20261115T134405Z/README.md) xác nhận9bảng/46định nghĩa schema khớp, API đặt/hủy/idempotency/outbox qua, DB nguồn không đổi và DB thử đã dọn. Timer/VM/cluster và GHCR chưa hoàn tất.

## Bố cục repo

[Mục lục tài liệu](docs/README.md) và [bố cục source](docs/guides/source-structure.md) là điểm bắt đầu cho thành viên mới.

| Phần | Vị trí |
|---|---|
| UI theo tính năng | frontend/src/app, features, components/ui, lib |
| API, nghiệp vụ, notification | services/clinic/api.py, routers, schemas, application; publisher.py và worker.py |
| CI/CD | ci/, Jenkinsfile, compose.ci*.yaml |
| IaC và deployment | infra/, deploy/k8s/ |
| Giám sát | observability/ |
| Công cụ | scripts/dev, scripts/ci, scripts/infra, scripts/maintenance |
| Tài liệu và bằng chứng | docs/guides, docs/runbooks, docs/evidence; ma trận tại docs/compliance-matrix.md |

Các thư mục cache/local/output đã được Git ignore và ẩn trong Explorer qua .vscode/settings.json. Không di chuyển hoặc xóa dữ liệu Docker, env, backup để dọn cây source.

## Khởi động dev (cần Docker engine hoạt động)

Prerequisites: Git, Docker Desktop/Linux engine có Docker Compose; Python 3.12 để sinh env. Khi chạy native/test cần Python 3.12 và Node 24/npm. Cổng dev: 18080, 8000–8002, 5433, 5673, 15673, 15693, 1025, 8025 phải trống; không mở cổng DB/broker/metrics ra Internet. FRONTEND_PORT có thể đổi; 8080 đang được Jenkins sẵn có sử dụng nên được giữ nguyên.

```powershell
python scripts/dev/init-env.py
docker compose up -d --build --wait
```

`init-env.py` tạo secret ngẫu nhiên trong `.env`, không ghi đè và không in secret. Compose dựng DB/broker/Mailpit, chạy migration rồi seed dev, khởi động app. Seed lặp an toàn, không đổi password tài khoản đã có, bị cấm khi ENVIRONMENT=production. Lệnh up/build/wait đã chạy thành công trên máy khảo sát; chưa kiểm chứng dựng toàn bộ IaC/K8s từ máy trắng.

URL dev: [frontend](http://localhost:18080), [API/OpenAPI](http://localhost:8000/docs), [Mailpit](http://localhost:8025), [RabbitMQ management](http://localhost:15673). Frontend/API/Mailpit và management API đã được truy cập thực; endpoint `/health`, `/ready`, `/metrics` của API/publisher/worker (8000/8001/8002) đều200 tại snapshot. Management dùng user `clinic`, mật khẩu trong .env, chỉ dùng local. Đây là HTTP dev; chưa có HTTPS cert-manager.

Tài khoản synthetic: `patient@example.test`, `other@example.test`, `admin@example.test`; mật khẩu đọc **cục bộ** ở `DEMO_PASSWORD` trong .env. Không đưa mật khẩu lên chat/Git. Xem [local setup](docs/guides/local-setup.md) để chạy từng thành phần, migration/seed, đặt lại password và kiểm tra email.

## Kiểm thử và bằng chứng

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe scripts/dev/verify.py
cd frontend
npm ci
npm run build
cd ..
.\scripts\dev\check-ui.ps1
```

Kiểm tra mặc định dùng SQLite riêng và fake channel/sender cho các unit test reliability. Không chứng minh khóa PostgreSQL, RabbitMQ hay SMTP thật. UI check ở trên dùng API thật + SQLite thử riêng, Edge headless; tự dừng hai tiến trình test, không xóa DB dev. Sau khi Compose thật healthy, dùng runner Linux đã được kiểm chứng:

```powershell
.\scripts\dev\check-integration.ps1
```

Integration tạo DB `clinic_test_<uuid>` riêng rồi xóa **DB thử đó**, queue/exchange prefix ngẫu nhiên rồi dọn đúng prefix. Cần role dev được CREATE DATABASE (official POSTGRES_USER dev có quyền này); không chạy bằng production credential. Test SMTP gửi vào Mailpit và thử connection-refused để kiểm tra retry/DLQ/replay, không gửi tải tới người thật. Native `scripts/dev/verify.py --integration` từng treo trên Windows và chưa được coi là pass; có timeout120s. Runner Compose mới đạt30/30. Test nhắc lịch truyền đồng hồ tương lai vào scheduler trên DB test, không tuyên bố đã chờ một giờ thực.

Diễn tập thật trên chính project dev: `.venv/Scripts/python.exe scripts/dev/smoke-runtime.py --faults` (có stop/start broker và SIGKILL đúng worker của clinic-dev, không dùng trên production). Script đã kiểm tra recovery và gỡ delay demo. Browser trên stack thật được kiểm chứng riêng trong evidence; xem local-setup.md để chạy lại.

## Các mốc còn lại

[Kiến trúc](docs/guides/architecture.md), [ADR](docs/guides/decisions.md), [quy trình nhóm](docs/guides/team-workflow.md), [nguồn/phiên bản](docs/guides/versions.md), [security](docs/guides/security.md) và [kịch bản 8 bước](docs/guides/demo-script.md) giải thích yêu cầu và cách kiểm chứng.

Mốc 2 còn thiếu GHCR publish/pull digest, PR/review và toàn luồng deploy; Docker move và baseline Jenkins/webhook push đã có bằng chứng thật. Ổ C vẫn cần đủ dung lượng cho Windows/log/pagefile trước build lớn. Terraform tạo3VM, Ansible, k3s/staging/production/TLS/RBAC/HPA/KEDA, Prometheus/Grafana/Alertmanager/EFK còn chưa triển khai. Provider libvirt và domain test đã được chọn ở mức thiết kế; chưa provision host/cluster hoặc có receiver chạy thật. Không có triển khai hoặc rollback K8s đã chạy để công bố; xem [deploy](docs/runbooks/deploy.md), [rollback](docs/runbooks/rollback.md), [restore](docs/runbooks/restore.md), [alerts](docs/runbooks/alerts.md). Runbook sự kiện dev: [notifications](docs/runbooks/notifications.md).

## Dừng và khắc phục lỗi

`docker compose stop` chỉ dừng các service của project `clinic-dev`; `docker compose down` gỡ container/network của project và giữ named volumes. **Không dùng `down -v` khi muốn giữ dữ liệu**. Dọn volume/DB cần xác nhận đúng project và có backup; không phải bước khởi động lại mặc định. Teardown Terraform chưa có vì chưa provision.

Nếu Docker `EOF`, HTTP 500 hoặc mất engine pipe: kiểm tra `docker version`, trạng thái Docker Desktop/WSL và tài nguyên host. Không tiếp tục coi build/up là thành công. Nếu cổng đã dùng, chọn cổng test khác hoặc dừng đúng tiến trình của mình; không kill dịch vụ không biết chủ sở hữu. Nếu login lỗi, kiểm tra seed/mật khẩu hiện tại, không reset DB. Nếu notification PENDING, kiểm tra publisher/broker/outbox trước; xem runbook. Mọi kiểm tra có evidence và scope riêng trong ma trận.


Phần chuẩn bị **Mốc 4** ở [docs/guides/milestone-4.md](docs/guides/milestone-4.md): Prometheus/Grafana/Alertmanager/EFK, dashboard37panel, alert rules và [runbook quan sát](docs/runbooks/observability.md). Kiểm tra local: `python scripts/infra/install-observability-tools.py` rồi `python scripts/ci/verify-m4-local.py`. [Evidence](docs/evidence/m4-latest.json) chỉ xác nhận parser/schema/unit/fixture; chưa có stack hoặc cảnh báo gửi thật. [Cloud estimate](docs/guides/cloud-cost-estimate.md), [8 bước demo](docs/guides/demo-script.md), [checklist nộp](docs/guides/submission.md), [vấn đáp](docs/guides/viva-preparation.md).
