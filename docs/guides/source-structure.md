# Bố cục source và cách chạy sau tái cấu trúc

Cập nhật 15/11/2026. Đây là lựa chọn tổ chức repo của nhóm, không phải cấu trúc thư mục bắt buộc trong PDF.

## Ranh giới thư mục

| Thư mục | Nội dung | Phụ trách bàn giao |
|---|---|---|
| frontend/src/app | App shell, controller điều phối trạng thái chung, CSS | Hoang |
| frontend/src/features | Màn hình auth, booking, appointments, admin | Hoang |
| frontend/src/components/ui | Button, Notice, Toggle và icons dùng chung | Hoang |
| frontend/src/lib | HTTP client, kiểu dữ liệu và hàm thời gian | Hoang |
| services/clinic/api.py | ASGI entrypoint `clinic.api:app` | Hoang |
| services/clinic/routers | HTTP endpoint và dependency xác thực | Hoang |
| services/clinic/schemas | Schema đầu vào | Hoang |
| services/clinic/application | Nghiệp vụ booking/catalog/auth và serialization | Hoang |
| services/clinic | DB/models/security, publisher/worker, reminder và telemetry dùng chung | Hoang |
| ci | Pipeline, gates, release/deploy/rollback, agent/controller/engine/relay và tests | Vuong |
| scripts/dev | Khởi tạo env, kiểm tra app/browser/integration, thu bằng chứng local | Hoang |
| scripts/ci | Bootstrap Jenkins, cài tool CI, verify theo mốc và smoke image SHA | Vuong |
| scripts/infra | Control host, Terraform/Ansible/K8s/monitoring, load, backup/restore | Long, Hoang hỗ trợ quan sát |
| scripts/maintenance | Công cụ bảo trì Docker storage có tham số đường dẫn rõ ràng | Long, Vuong review |
| infra | Terraform, Ansible, budget và tool versions | Long |
| deploy/k8s | Manifest và overlays staging/production | Long |
| observability | Metrics, dashboard, rules, EFK và cấu hình quan sát | Hoang, Long hỗ trợ operator |
| images | Dockerfile middleware, không phải ảnh giao diện | Vuong |
| contracts | Event schema/example versioned | Hoang |
| tests | Kiểm thử ứng dụng; tests của CI nằm ở ci/tests | Cả nhóm theo phần thay đổi |
| docs | Mục lục, ma trận, guides, runbooks và evidence | Cả nhóm |

API/publisher/worker vẫn dùng chung package và image nhưng chạy độc lập. Đường dẫn endpoint, event schema, migration, dữ liệu và transaction không được đổi chỉ vì di chuyển module. State điều phối frontend tiếp tục nằm ở `useClinicApp` để giữ dữ liệu nhập khi chuyển màn hình; mỗi feature có component riêng. Đây chưa phải tách từng feature thành ứng dụng độc lập.

## Chạy từ checkout bất kỳ

Chạy lệnh từ repo root. Python script tìm root theo `Jenkinsfile` và `pyproject.toml`; không yêu cầu repo nằm trên ổ D hoặc trong thư mục người dùng cụ thể.

```powershell
python scripts/dev/init-env.py
docker compose up -d --build --wait
.\.venv\Scripts\python.exe -m pytest -q
npm --prefix frontend run lint
npm --prefix frontend run format:check
npm --prefix frontend run build
```

Pytest mặc định gồm `tests` và `ci/tests`. Unit có thể skip các case phụ thuộc broker/DB thật. Integration container chỉ chạy `tests`; nó gắn source hiện tại, tạo DB/queue test riêng và phải ghi rõ có build image mới hay chỉ dùng bind mount.

```powershell
.\scripts\dev\check-ui.ps1
.\scripts\dev\check-integration.ps1
.\.venv\Scripts\python.exe scripts/ci/bootstrap-ci.py --help
.\.venv\Scripts\python.exe scripts/ci/verify-m3-local.py
```

Trên Windows, kiểm tra control host dùng `wslpath` để đổi đường dẫn checkout hiện tại. Mặc định dùng distro WSL của người dùng. Chỉ đặt `CLINIC_WSL_DISTRO` nếu muốn chọn distro khác; không có yêu cầu distro phải tên Ubuntu-22.04. Có unit test cho đường dẫn chứa khoảng trắng, distro tùy chọn và lỗi chuyển đường dẫn. Unit test này không chứng minh WSL/KVM đủ tài nguyên để triển khai.

`scripts/dev/collect-runtime.py` nhận `--brief` và `--assignment-pdf` tùy chọn để ghi hash tài liệu gốc. Không truyền thì ghi NOT_PROVIDED, không tìm trong Downloads của một tài khoản cụ thể.

## Dữ liệu local và file sinh tự động

`.ci-local`, `.infra-local`, `.venv`, cache, `ci-out`, `tmp`, `outputs`, node_modules và dist đã được loại khỏi Git phù hợp với phạm vi. `outputs/` còn được loại khỏi Docker context. `.vscode/settings.json` chỉ ẩn các thư mục này trong Explorer; file và dữ liệu thật vẫn nằm nguyên chỗ cũ. `.env`/`.env.ci` vẫn dùng tại root và không được commit.

Các công cụ maintenance không chạy khi cài app hoặc chạy test. Công cụ backup nhận `-DockerSource`, `-BackupRoot`, tùy chọn `-SourceSettings`; công cụ inspect nhận `-TargetDisk`, tùy chọn `-SourceDisk`; công cụ chuẩn bị thư mục nhận `-DataRoot`, `-BackupRoot`. Tham số phải được người vận hành kiểm tra và duyệt theo runbook. Không dùng tái cấu trúc source để tự chuyển/xóa VHD hoặc sửa ACL/pagefile trên máy chung. Lần refactor này chỉ sửa mã của chúng, không thực thi các tác vụ bảo trì đó.

Backup PostgreSQL dùng `scripts/infra/backup.sh`, `restore.sh` và helper `backup-common.sh`, tách khỏi backup VHD ở `scripts/maintenance`. Role Ansible cài đủ helper theo đường dẫn mới `scripts/infra/{{ item }}`. CI kiểm source copy/template có thật và parse Bash đệ quy, mỗi file một lần; không dùng glob chỉ quét thư mục root. [Drill dev](../runbooks/restore.md) chạy bằng `python scripts/dev/check-backup-restore.py`, giữ dump tại `.infra-local/db-backups`, chỉ tạo/xóa DB thử thuộc lượt đó. Metadata ghi hash source và phạm vi, không suy thành VM/cluster hoặc timer đã chạy.

## Kiểm chứng

Xem báo cáo `docs/evidence/source-restructure-*/metadata.json` của lần kiểm tra mới nhất. Baseline Jenkins #8/SHA 5bf6734 là kết quả trước refactor. Chỉ ghi một build Jenkins mới đã đạt khi đúng source sau thay đổi đã thực sự chạy qua pipeline. Docker chuyển sang D đã có bằng chứng lịch sử; dung lượng Windows C vẫn phải được đo riêng trước build lớn.

## Repo GitHub và định danh CI

GitHub redirect từ vxxngw/DevOps đến vuongvo2207-gmail-com/DevOps, cùng repository ID 1457478642; repo vẫn private. Cấu hình hiện tại dùng URL canonical. Webhook đọc ci/webhook/repository.json, đối chiếu cả tên và ID của repository/head PR, giữ HMAC và từ chối fork. Namespace image dự kiến là ghcr.io/vuongvo2207-gmail-com; chưa có bằng chứng publish GHCR.

Chuỗi OWNER trong bootstrap Jenkins là marker ownership đã lưu trên controller cũ. Nó cố ý giữ giá trị lịch sử dù file script đã chuyển chỗ, để guard nhận đúng item thuộc dự án. Không đổi marker theo tên file hoặc tài khoản. Hai regression test kiểm tra cập nhật item cũ hợp lệ và từ chối item của dự án khác.

Kết quả sau thay đổi: [final summary](../evidence/source-restructure-20261115T104329Z/final-summary.json), Jenkins11SUCCESS92unit/8skip và33integration/0skip,5image0CRITICAL, browser10checks và SHAstack cleanup0. Không suy thành GHCR publication hoặc K8s runtime.
