# CI và runtime SHA – 15/11/2026 giờ Việt Nam

**Đã kiểm chứng local; chưa nghiệm thu toàn Mốc2–4.** [Tổng hợp có phạm vi](summary.json), [CI gần nhất](../ci-runtime-latest.json).

| Phần | Bằng chứng thật | Giới hạn |
|---|---|---|
| Agent và Docker build engine | agent-build-attempt-2.log exit0; agent-state.json offline=false; agent-tool-verification.json có13lệnh qua, UID1000, mutualTLS và engine rootless, không có Docker socket host | Engine lồng vẫn cần privileged để khởi tạo rootlesskit; không phải VMCI độc lập |
| Sửa TLS | engine-tls-fix.json: thêm DOCKER_TLS_SAN=DNS:engine; engine volume giữ nguyên, chứng chỉ có DNS:engine; log/probe lỗi trước sửa được giữ | Không tắt TLS hoặc hostname verification |
| Jenkins4/5 | build4 queue-7 và build5: SUCCESS; lint, unit, Terraform/K8s schema, monitoring parser, build5imageSHA, integration và scan qua | PUBLISH_IMAGES=false, DEPLOY=false; không phải staging/production |
| JUnit build5 | [Unit81passed/8skipped](build-5/summary-junit-unit.xml.json); [integration33passed/0skipped](build-5/summary-junit-integration.xml.json) | Unit được skip adapter; integration riêng không có skip |
| Trivy release | build-5/artifact-ci-out_security-summary.json: cả5imageID/tagSHA không CRITICAL; dependency gate qua; ignorefile rỗng, ignore-unfixed=false | Tag ghcr.io chỉ là tag trong CI engine; chưa push registry hoặc có release digest |
| Gate âm | Jenkins1:1secret giả, exit1/FAILURE; Jenkins3:4CRITICAL từ Alpinecũ quétremote, exit1/FAILURE; flow-stages.json có SKIPPED_FOR_FAILURE cho push/deploy | Hai lượt này đặt publish/deploy=false. Không commit credential thật hoặc chạy image Alpinecũ; chưa so digest deployment K8s trước/sau |
| Runtime image mới | [Lệnh có thể chạy lại](sha-runtime-reproducible/metadata.json):7service healthy/non-root, migrate/seed0,9HTTP200, frontend200, BOOKED/CANCELLED email body khớp ID,3backend stdout JSON, cleanup0 | Base Compose của commitaadcc9892b64e59e0523513968dfaefa4dd53f1a; thay5tagSHA và bỏ port publish, project/volume riêng; giữ nguyên dev stack và mọi dữ liệu cũ |
| Webhook | github-webhook-configured.json ping200; github-correlation-*.json có push202 → userclinic-webhook → Jenkins5SUCCESS đúng SHA | PRcũ draft/basekhácmain được nhận200 rồi bỏ qua đúng policy; chưa có PRmain phù hợp chạy thật ở snapshot này |
| HMAC/quyền | public-relay-verification.json: health200, unsignedPOST401, /login và /api/json404; webhook-permissions-verified.json: READ/BUILD, không admin/script/configure/credential | Collector đầu đoán credential endpoint403; thực tế Jenkins ẩn bằng404, admin200 và ACLfalse đã kiểm tra, không hạ quyền để sửa test |
| Dung lượng | duplicate-copy-cleanup-plan*.json và cleanup-executed.json: haiVHD tạm trùng SHA256 backup, Docker dùngDactive; userduyệt rồi chỉ xóa bản tạm, lấy lại10,31GiB | D:\DockerBackup và cả2recovery backup giữ nguyên; không prune images/volume toàn hệ thống |

Giữ nguyên lần build agent đầu bị DNS lỗi và Jenkins2 bị DNS của mirror.gcr.io chặn trước khi có report. Không tính scanner lỗi là chứng minh phát hiệnCRITICAL. Probe DNS/HTTPS rồi retry thực đã qua; chưa kết luận nguyên nhân gốc của lỗi DNS tạm thời. docker-space.log còn ghi một cache record cũ thiếu snapshot; không prune hoặc suy thành mất volume. Build engine riêng và builds thật vẫn qua.

Bản công bố Trivy/Gitleaks/JUnit ở `build-1/reports`, `build-3/reports`, `build-5/reports`; [chỉ mục bản công bố](raw-report-publication.json) ghi hash và đường dẫn raw private tại `.ci-local/submission`. Bản gốc cũng còn trong Jenkins artifacts. Nếu quét secret yêu cầu che checksum package bị nhận nhầm, chỉ công bố bản đã che kèm provenance; không dùng bản đã sửa thay input của release gate. [Kiểm gate gốc](release-gates-verified.json) chạy trực tiếp trên workspace của build4, đối chiếu commit/hash/JUnit/imageID; không đăng nhập hay push registry.

Chạy lại full-stack SHA sau khi agent online, tải `ci-out/security-summary.json` từ build đã xanh rồi chạy tại repo:

```powershell
.\.venv\Scripts\python.exe scripts/run-sha-stack.py DUONG_DAN_SECURITY_SUMMARY_JSON
```

Launcher lấy Compose bằng git show đúng commit của report, truyền nguyên byte checker vào agent. Checker giữ service command/env/probe/dependency của Compose, dùng secret synthetic mới, không có port publish và volume/network ngoài project ngẫu nhiên. Evidence mới ghi verifier SHA256, imageID/UID/health,9HTTP, email body booleans và cleanup. Không dump .env/resolved Compose hoặc token vào artifact công khai.

[Runbook webhook](../../runbooks/github-webhook.md), [Mốc2](../../milestone-2.md), [ma trận](../../compliance-matrix.md). GHCR credential, review/semver, main protection trả403 gói private hiện tại, VM/cluster, scale/tải/alert/EFK/restore/video vẫn cần bằng chứng đúng phạm vi.


Bổ sung [negative6/7 với publish=true](publish-requested-negative-checks.json): cả1secret/4CRITICAL có report thật, scannerexit1, buildFAILURE, push/deploy SKIPPED_FOR_FAILURE. DEPLOY vẫnfalse; không có registrylogin/push. Hai dòng probe raw public reportGPGfingerprint của Python base được xác minh với source Docker Python chính thức rồi che riêng ở auditcopy; giữ raw/gatehash, không đổiCVE/imageID/allowlist. Xem raw-report-publication.json.


Sau các build đã xác minh, Docker có lượt dừng với log ENOSPC khi ghi init.log trên C. Đã dùng Desktopstop → terminate riêng docker-desktop → Desktopstart để khôi phục, engine29.9.3/Jenkins/agentonline, queue trống; VHDactiveD giữmở và backend đúngD. Snapshot Cpagefile allocated20994MiB; chưa kết luận đầy đủ tác nhân làm đầy C tại thời điểm lỗi, không sửa pagefile hay xóa file người dùng. Xem runtime-recovery-after-log-enospc.json trong bundleCI; các SUCCESS trước sự cố vẫn là bằng chứng lịch sử, không suy thành uptime liên tục.
