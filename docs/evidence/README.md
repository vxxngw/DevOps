[Refactor đã kiểm chứng](source-restructure-20261115T104329Z/README.md): source32f4343, Jenkins11SUCCESS,92unit/8skip,33integration/0skip,10browserchecks,5image0CRITICAL và SHAstack/email/cleanup0.

[Backup/restore dev thật](backup-restore-20261115T134405Z/README.md): dump/checksum/retention, 9 bảng và46schema definitions khớp, API/outbox qua, nguồn không đổi, DB thử đã dọn. [CI native mới](backup-ci-checks-20261115T134558Z/README.md) có lint/110unit+8skip và kiểm hạ tầng tĩnh; chưa phải Jenkins build mới hay timer/VM/cluster runtime. Các snapshot lịch sử bên dưới không bị viết lại.

[Linux source0bd3fb3](linux-paths-20261115T141048Z/README.md): 18 test liên quan qua trên agent UID1000, checkout riêng có khoảng trắng; source7file Ansible/Bash6file qua. Không build image hoặc khởi động pipeline.

[Full unit Linux source 0bd3fb3](linux-unit-20261115T141826Z/README.md): 110 đạt/8 bỏ qua, agent non-root và checkout riêng có khoảng trắng. Không thay integration hoặc full Jenkins build mới.

## Hiện trạng và bằng chứng mới

[CI runtime](ci-runtime-latest.json) và [CI/SHA bundle](ci-agent-20261115T064424Z/README.md) ghi nhận baseline CI thật. Các phần dưới là snapshot lịch sử. Sau tái cấu trúc, xem [bố cục source](../guides/source-structure.md) và báo cáo kiểm chứng riêng, không coi baseline là build của source mới.

# Evidence index

## Mốc3 – chuẩn bị local

[Bằng chứng mới nhất](m3-latest.json), [báo cáo](../guides/milestone-3.md). Có Terraform/provider/schema/unit/scanner/controlchecks theo metadata; giữ lỗi WSL và phạm vi từng lượt. Chưa VMapply, máy trắng/idempotency, clusterdeploy, TLStrust, autoscale, backup/restore/rollbackruntime.

## Mốc 2 – phạm vi local, chưa runtime CI

- [Remote base image scans](m2-base-images-20261114T085952Z/metadata.json): giữ cả nền lỗi và nền thay thế; Python/Nginx/Mailpit mới0CRITICAL, RabbitMQ0; PostgreSQL1ởgosu. Dockerfile đã sửa, custom build/scan/runtime vẫn chưa chạy.

- [Local checks](m2-local-20261114T084619Z/metadata.json): Ruff/format/ESLint/typecheck/build,56passed/8integration skipped; Gitleaks history baseline, scan lock Python/Node gồm dev dependencies và hai demo scanner exit1 có finding thật. HEAD/working tree/source hash ghi riêng; chưa phải Jenkins build hoặc scan image release.
- [Main protection403](m2-git-policy-20261114T081335Z/metadata.json): GitHub Free/private không cho bật bảo vệ main; giữ repo private, không tạo enforcement/review giả.
- [Backup Docker](docker-storage-20261114T073814Z/backup-manifest.json): nguồn dừng ghi và bản backup khớp SHA256. [Copy/config thử](docker-migration-20261114T074728Z/copy-and-settings.json) không chứng minh đĩa D active; live check sau đó vẫn dùng C. Xem [runbook](../runbooks/docker-storage-migration.md).

## Mốc 1 – lịch sử trước commit baseline

Tất cả bằng chứng dưới là chạy thật trên workspace hiện tại, dùng dữ liệu synthetic. Commit: **UNCOMMITTED**; metadata ghi hash source hoặc bundle. Thời gian thư mục dùng UTC, báo cáo theo Asia/Ho_Chi_Minh (UTC+7). Không suy fake channel/SQLite thành broker/PostgreSQL thật. Không coi tất cả bài DevOps đã đạt từ Mốc 1.

Suite mới30test: 8API/DB,1schema,6unit reliability có fake channel/sender,10test nhắc lịch/timer/ownership/khóa,5test adapter RabbitMQ/SMTP thật. DB của suite Linux là PostgreSQL; không gọi cả30là test SMTP. Các snapshot19test bên dưới là lịch sử trước bổ sung nhắc lịch. Fault smoke và UI Compose kiểm tra riêng các tiến trình live end-to-end.

| Bằng chứng | Lệnh / môi trường | Kết quả và giới hạn |
|---|---|---|
| [Rà soát DevOps và phục hồi local](devops-review-20261114T063937Z/metadata.json) | PDF/brief, repo/Git/tool inventory, runtime read-only; phục hồi engine và2container cổng host của clinic-dev | Chưa đủ12bài/8demo/sản phẩm nộp; [báo cáo](../guides/devops-review.md). Snapshot cuối7healthy/11HTTP200, [browser11checks](ui-devops-recovery-20261114T063956Z/metadata.json). Git0tracked/0remote/0tag; thiếu Jenkinsfile/IaC/K8s/observability. Không suy thành CI/IaC/security pass |
| [Double check UI](ui-requirements-final-20261114T054356Z/metadata.json) | API bootstrap thật; lỗi mạng/HTTP và reminder status giả lập trong browser, không ghi appointment | 15/15checks pass, có responsive history/admin ở320/390/768/1440. [Báo cáo từng yêu cầu](../guides/ui-requirements-review.md); [trước sửa8pass/5fail](ui-requirements-before-20261114T053603Z/metadata.json), [sau sửa13pass](ui-requirements-after-20261114T053824Z/metadata.json) giữ riêng |
| [Smoke sau double check](ui-double-check-20261114T054401Z/metadata.json) | Browser → Compose/PostgreSQL/RabbitMQ/Mailpit thật | 11/11checks pass sau sửa, không gọi15test UI giả lập là15test gửi SMTP thật |
| [Inspection sau double check](soft-minimal-inspection-20261114T054357Z/metadata.json) | CSS/font/asset và12layout probes | Màu/font/radius đúng, không tràn ngang, served JS/CSS khớp dist. Kèm log Vite/Docker, live status và source hashes |
| [Soft Minimal UI mới](ui-soft-minimal-20261113T193104Z/metadata.json) | Edge → Nginx/API/PostgreSQL/RabbitMQ/Mailpit, `frontend/tests/smoke.cjs` | 11checks pass:3bước, giờ bận, pending, lỗi503 giữ dữ liệu/key, email SENT, công tắc lưu thực, hủy, quyền patient/admin. [Ảnh desktop](soft-minimal-inspection-20261113T193126Z/slots-desktop.png), [mobile](ui-soft-minimal-20261113T193104Z/review-mobile.png) |
| [Soft Minimal inspection](soft-minimal-inspection-20261113T193126Z/metadata.json) | Đo CSS/font/served assets,12layout probes | Đúng toàn bộ palette/Inter/bo góc; không tràn ngang320/390/768/1440 ở login/chọn giờ/xem lại; hash JS/CSS khớp build, logo khớp asset. Kèm build logs, Compose status và Alembic head |
| [Suite mới30/JUnit](integration-20261113T192650Z/metadata.json) | Linux/PostgreSQL/RabbitMQ/Mailpit, `check-integration.ps1` | 30pass trong12.35s; nhắc lịch kiểm thử bằng đồng hồ truyền vào scheduler, gửi SMTP thật và dedupe; không tuyên bố chờ1giờ thực.1warning TestClient/httpx |
| [Native mới22pass/8skip](20261113T193126Z/metadata.json) | Windows,SQLite, `scripts/verify.py` | Lint/format/pip check exit0; pytest22pass/8skip; skip được chạy bằng Linux suite riêng;1warning TestClient/httpx |
| [Logo xanh #103783](logo-blue-20261113T185004Z/metadata.json) | Vite/Docker frontend build, logo/favicon SVG, render desktop/mobile | HTTP200/hash khớp, ảnh nguồn nhúng nguyên byte;3pixel đặc đo đượcff103783; không tràn ngang. Không suy thành test DB/broker mới |
| [An Uyên Hospital branding](branding-20261113T183956Z/metadata.json) | Logo gốc nguyên byte, primary#103783, ảnh desktop/mobile, tên OpenAPI/email thực | Build Docker/dev healthy; [UI6checks](ui-an-uyen-20261113T183851Z/metadata.json), [suiteLinux19/19](integration-20261113T183741Z/metadata.json), [native13pass/6skip](20261113T183544Z/metadata.json). Scope/chi tiết ở[branding](../guides/branding.md); không thay evidence các mốc DevOps còn thiếu |
| [Inspection cuối](inspection-20261113T175719Z/metadata.json) + [audit bàn giao](final-audit.json) | Sửa template đọc field User upstream vắng mặt; kiểm tra link/ma trận/metric parser/local env secret copy | Tất cả command exit0/HTTP200; JSON stdout145/145dòng, metrics parse được; ma trận70dòng đủ12nhóm/8demo/16AC. Đây không thay gitleaks/Trivy |
| [Integration cuối19/JUnit/JSON stdout](integration-20261113T174626Z/metadata.json) | scripts/check-integration.ps1, broker plugin đã sửa, Linux/PostgreSQL/RabbitMQ/Mailpit | 19/19 pass trong10.51s,1warning httpx deprecation; [raw JSON/test log](integration-20261113T174626Z/pytest.log), [JUnit](integration-20261113T174626Z/junit.xml). Cache dùng/tmp, không che test lỗi |
| [Integration19/JUnit/log](integration-20261113T171959Z/metadata.json) | scripts/check-integration.ps1, Linux app image, DB clinic_test_UUID + queue prefix riêng, RabbitMQ/SMTP Mailpit thật | 19/19 pass; [raw](integration-20261113T171959Z/pytest.log), [JUnit](integration-20261113T171959Z/junit.xml). Có cảnh báo httpx deprecation/cache permission ở lượt đầu, không che cảnh báo |
| [Unit/lint/format/deps cuối](20261113T174426Z/metadata.json) | .venv Python3.12 trên Windows; scripts/verify.py | Các command exit0; [pytest](20261113T174426Z/pytest.log) 13 pass/6 skip. Sáu skip là tests cần PostgreSQL/broker, được chứng minh riêng bằng integration |
| [Fault/business smoke pass](runtime-20261113T173308Z/metadata.json) | scripts/smoke-runtime.py --faults; stack Compose/PostgreSQL/RabbitMQ/Mailpit | Exit0; 5 checks: email body/SENT, proxy sau API recreate, broker outage/outbox/recovery, kill worker before ack/recovery114.781s, cancel/email3lịch. Lệnh stop/kill/start có target clinic-dev cụ thể và exit code |
| [UI Compose thật](ui-compose-20261113T173824Z/metadata.json) | Edge157.0.4341.46 headless → Nginx18080 → API/PostgreSQL/RabbitMQ/Mailpit | 6 checks pass, served JS/CSS hashes bằng build; [patient desktop](ui-compose-20261113T173824Z/patient-desktop.png), [mobile](ui-compose-20261113T173824Z/patient-mobile.png), [admin](ui-compose-20261113T173824Z/admin-desktop.png), [login](ui-compose-20261113T173824Z/login.png) |
| [Inspection runtime](inspection-20261113T174328Z/metadata.json) | scripts/collect-runtime.py; docker inspect/exec/logs, HTTP health/ready/metrics, hash brief/PDF/source | App endpoints9/9 HTTP200; Rabbit metrics/per-object200; JSON stdout139/139 dòng ở snapshot; non-root actual + cap_drop/security. Một image-inspect Mailpit template lỗi, không tính là thuộc tính upstream đã được xác nhận. Build logs gốc được copy vào cùng folder |
| [Cleanup lượt smoke cũ](reconcile-20261113T174425Z/metadata.json) | API cancel đúng3lịch synthetic có correlation runtime- trong window UTC của lượt lỗi | Giữ lịch sử, CANCELLED và email SENT; không reset/xóa DB |
| [UI SQLite cũ](ui-20261113T170532Z/metadata.json) | scripts/check-ui.ps1; native API + SQLite riêng | 5 checks pass; không dùng làm chứng cứ email/PostgreSQL |

## Những lượt không đạt được giữ nguyên

- [UI Soft Minimal lượt đầu](ui-soft-minimal-20261113T192729Z/metadata.json): exit1 do Playwright `.check()` yêu cầu checkbox đổi ngay trong khi UI đợi PATCH lưu xong. Test được sửa thành click, đợi response200 rồi assert state. [Lượt10checks](ui-soft-minimal-20261113T192811Z/metadata.json) đã pass; lượt cuối11checks còn thêm kiểm tra pending. Không ghi đè evidence lỗi.
- [Native Windows integration treo/đã dừng](20261113T171149Z/metadata.json): pytest exit4294967295, không pass. DB clinic_test_b7199c5de4234cada99a17e9cfaae553 đã dọn sau khi dừng đúng test process. Linux runner là bằng chứng integration được dùng.
- [Smoke đầu](runtime-20261113T172254Z/metadata.json): exit1 do RemoteProtocolError ở HTTP management chưa có listener; hai check email/broker recovery đã qua nhưng cả lượt không đạt.
- [Smoke trước sửa proxy](runtime-20261113T173052Z/metadata.json): HTTPStatusError, exit1, chưa tạo lịch; không ghi thành pass. Lượt mới có regression recreate API.
- [Lint lỗi ban đầu](20261113T165259Z/metadata.json): Ruff exit1, pytest exit0; không coi toàn bộ verification pass. Đã sửa fixture import và có lượt cuối exit0 riêng.
- [UI trước sửa nhãn](ui-20261113T170008Z/metadata.json): timeout chọn combobox; giữ failure và ảnh đã chụp. Đã sửa htmlFor/id và chạy lại riêng.

Log lỗi user PostgreSQL và các log build/up sau được lưu trong inspection; không suy mọi log đều thành công. Lỗi EOF/HTTP500 ban đầu được quan sát trong tool transcript; [preflight](preflight-20261113T165422Z.json) ghi engine pipe không có ở lần sau, không dựng lại raw log EOF. Chưa có bằng chứng Git remote/PR/review, Jenkins/webhook/registry push/security gate, Terraform/Ansible/K8s/HPA/KEDA, Prometheus/Grafana/Alertmanager/EFK, load test/rollback/video hoặc mailbox bên ngoài.

## Lỗi môi trường trong lượt rà soát DevOps14/11

[Engine pipe mất kết nối](devops-review-20261114T062627Z/metadata.json), [HTTP lỗi sau engine khởi động](devops-outage-20261114T063406Z/metadata.json), [snapshot chỉ5/11HTTP200 dù7container healthy](devops-review-20261114T063627Z/metadata.json) và [probe cổng host](devops-recovery-probe-20261114T063816Z/metadata.json) được giữ nguyên. Không coi container healthy là đủ truy cập từ host. Engine đã phục hồi, recreate riêng API/publisher sửa cổng host; snapshot cuối và smoke ở đầu bảng. Một collector từng gặp WinError1455; WSL bootstrap sau đó có0xc00000fd; chưa xác định nguyên nhân gốc, không khẳng định do RAM. Phục hồi môi trường không phải demo rollback app≤120giây.


## Chuẩn bị Mốc 4

[m4-latest.json](m4-latest.json) trỏ lần chạy có source hashes, JUnit, parser Prometheus/Alertmanager, 14 ca rule fixture, 37 query dashboard, schema/policy51đối tượng và Ansible/Bash/Vault local. VMpreflight vẫn BLOCKED, Jenkins parser BLOCKED. Không có stack monitoring/EFK, external alert receipt, tải/scale/rollback/video. [cloud-cost-latest.json](cloud-cost-latest.json) là nguồn giá công khai và phép tính, không phải hóa đơn hay cloud deployment. Các lượt bằng chứng cũ giữ nguyên.

Bằng chứng M4 tổng hợp ghi rõ lượt native cuối và lượt Ansible/Bash/Vault cùng source trước đó; các lượt WSL lỗi WSAENOTCONN và exit1 không có chẩn đoán được giữ lại. local_checks_passed chỉ tổng hợp các kiểm tra nguồn có bằng chứng, không có nghĩa WSL hiện tại hoặc VM/cluster đang chạy.


[ci-runtime-latest.json](ci-runtime-latest.json) ghi lần khôi phục15/11: controller/engine thật, anonymous403, job/SCM credential đã cấu hình, agent offline và parser fail→pass. Có fresh backup manifest và WSL Ansible/Bash/Vault checks. Không có pipeline build hoặc D migration proof.

[ops-security-latest.json](ops-security-latest.json): 8remote image scan0CRITICAL sau retryJavaDBtimeout, raw gate validated. Bản public chỉ che packageSHA1 false positives; source hashes/CVE giữ nguyên, gate dùng report gốc ci-out. Chưa có image runtime hoặc deploy stack.
