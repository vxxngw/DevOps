# CI/CD local và bằng chứng cần thu

Đối chiếu yêu cầu tại [ma trận](../compliance-matrix.md). Jenkins riêng ở `http://localhost:18090`, controller cũ `http://localhost:8080` giữ nguyên. [Source d2ba14c/Jenkins13](../evidence/backup-ci-runtime-20261115T142446Z/README.md) đã build/test/scan qua webhook thực:110unit/8skip,33integration/0skip,5image/dependency0CRITICAL và SHA stack/email/cleanup qua. Các lượt native/Linux trước đó giữ phạm vi riêng; không lấy chúng thay full pipeline. Publish/deploy của build13 đều tắt, GHCR còn thiếu credential.

## Kiểm tra độc lập Docker

Chạy ở thư mục repo, Python 3.12, Node 24; dùng môi trường Python đã cài requirements.lock:

```powershell
.\.venv\Scripts\python.exe scripts/ci/install-ci-tools.py
.\.venv\Scripts\python.exe scripts/ci/verify-m2-local.py
```

Installer ghim Gitleaks 8.30.1/Trivy 0.76.2, đối chiếu checksum release chính thức, chỉ giải nén executable. Dữ liệu tạm/cache ở `.ci-local` trong checkout hiện tại. Verifier ghi log/JUnit/báo cáo scanner, working tree và hash source vào thư mục evidence mới. Hai demo âm trả exit1 do finding thật; chúng không thay bằng chứng build Jenkins thất bại. Suite native cho phép skip integration, còn stage integration trong CI từ chối mọi skip.

Trivy không tự nhận tên requirements.lock: script sao chép nguyên byte thành requirements.txt ở thư mục scan riêng, kèm package-lock.json, ghi hash file gốc và bắt buộc có kết quả cả pip/npm. Không resolve lại dependency khi scan. Gitleaks có ngoại lệ hẹp cho 5 trường source_sha256 đã kiểm tra trong evidence lịch sử; 3 test chạy executable thật chứng minh secret khác vẫn bị phát hiện, kể cả trong metadata.json.

## Khởi tạo controller riêng

Điều kiện: Docker hoạt động, đủ dung lượng/RAM và cổng 18090/18085 còn trống cho stack mới. Trên máy Windows đã khảo sát, data disk Docker đã chuyển sang D nhưng Windows vẫn cần dung lượng ổ hệ thống cho log/pagefile. Trước full build nên có ít nhất 3 GiB trống trên ổ hệ thống và đo lại dung lượng checkout/data disk; đây là mức dự phòng vận hành của nhóm, không phải yêu cầu PDF hoặc bảo đảm build luôn đủ chỗ. Giới hạn RAM các container CI tổng khoảng 5–6 GiB, chưa phải số đo peak. Nếu stack đang chạy, không khởi tạo lại chỉ để xem trạng thái.

```powershell
.\.venv\Scripts\python.exe scripts/ci/bootstrap-ci.py init
docker compose --env-file .env.ci -f compose.ci.yaml up -d --build --wait controller engine
.\.venv\Scripts\python.exe scripts/ci/bootstrap-ci.py configure
.\.venv\Scripts\python.exe scripts/ci/bootstrap-ci.py validate
docker compose --env-file .env.ci -f compose.ci.yaml --profile agent up -d --build --wait agent
```

Tài khoản `clinic-admin`, mật khẩu ngẫu nhiên chỉ trong `.env.ci`. Bootstrap từ chối controller cho anonymous đọc hoặc chưa bật security. Controller không có executor. Agent `clinic-ci-linux` nối WebSocket, có JDK21/Python3.12/Node24/Docker CLI/scanner ghim phiên bản. Engine rootless riêng không được publish port ra host; agent chỉ nhận TLS client certificate. Workspace cùng đường dẫn trên agent/engine để bind mount integration test hoạt động.

Credential nằm trong folder `an-uyen`, không trong Git:

| ID | Nguồn | Dùng khi |
|---|---|---|
| clinic-github | Git Credential Manager đã đăng nhập | Checkout private repo; credential hiện tại có quyền repo rộng, nên thay bằng token repo chỉ đọc khi có |
| clinic-ghcr | `.registry-token`, PAT classic write:packages | Stage publish sau mọi cổng đạt; không cấp cho PR/fork |
| clinic-kubeconfig-staging/production | Jenkins secret file, deployer namespace | Mốc 3, chưa có |
| clinic-lab-ca | Jenkins secret file, CA tin cậy của lab | HTTPS smoke staging/production, chưa có runtime |
| clinic-smoke-staging/production | Synthetic username/password | Mốc 3, chưa có |

`.env.ci`, `.registry-token`, `.ci-local`, ci-out đều bị loại khỏi Git và Docker context. Không copy credential của Jenkins mới sang controller cũ chưa bật security. Bootstrap giữ credential đã có; thay/rotate credential phải thực hiện rõ ràng trong controller riêng.

## Webhook thật

```powershell
.\.venv\Scripts\python.exe scripts/ci/bootstrap-ci.py configure-webhook
docker compose --env-file .env.ci -f compose.ci.yaml --profile webhook up -d --build --wait webhook
```

Relay chỉ bind 127.0.0.1:18085, HMAC SHA256 cho payload nguyên byte, tối đa 1 MiB. Đối chiếu tên `vxxngw/DevOps` và repository ID `1457478642` từ `ci/webhook/repository.json`, cùng commit40hex. PR phải cùng repo, không draft và base `main`; fork bị từ chối. Push lên main gửi PUBLISH_IMAGES=true và DEPLOY=true: publish digest đã scan, deploy staging rồi dừng ở stage `Approve production` (input, chỉ PRODUCTION_APPROVERS, timeout 15 phút) trước production. Nhánh tính năng/PR không publish, không deploy. API token relay thuộc clinic-webhook với quyền Overall/Read, Job/Read, Job/Build, không có quyền admin/configure/credentials. Không dùng token clinic-admin cho relay.

Cần URL HTTPS công khai chỉ chuyển tiếp đến relay, giữ controller/agent/engine nội bộ. Có thể dùng [Cloudflare Quick Tunnel](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/) cho demo local sau khi cài cloudflared ghim phiên bản và ghi version/checksum. Đây là lựa chọn thiết kế, không phải yêu cầu PDF; Quick Tunnel không bảo đảm uptime và URL thay đổi sau restart. Không trỏ tunnel vào Jenkins8080/18090. Khi relay healthy và có URL:

```powershell
.\.venv\Scripts\python.exe scripts/ci/bootstrap-ci.py github-webhook --public-url https://TEN-RELAY-CUA-BAN
```

Lệnh tạo/cập nhật đúng endpoint của repo, không in HMAC/token. GitHub kiểm tra TLS; không insecure_ssl=1. Kiểm tra ping200, push/PR delivery202 và build có cùng SOURCE_REF. Lưu delivery ID/event/status/SHA/queue/build URL đã che header/body; không lưu X-Hub-Signature hoặc credential. Relay dùng SQLite để chống payload lặp qua restart. Nếu chết giữa claim và enqueue, PENDING cần được người vận hành kiểm tra queue rồi xử lý; không hứa exactly-once cho webhook/build.

## Nghiệm thu pipeline

Job `an-uyen/clinic-pipeline`, mặc định SOURCE_REF/SOURCE_BRANCH=main, CLUSTER_SERVER_URL=https://192.168.56.11:6443 (k3s lab VirtualBox), IS_PR=false, PUBLISH_IMAGES=false, DEPLOY=false. Chỉ người tin cậy có thể sửa mã trong repo private/khởi chạy pipeline có credential. Các kiểm tra PR của thiết kế local này không phải hệ thống chạy code từ fork không tin cậy.

1. Push nhánh/PR thật, xác nhận webhook tạo build, checkout đúng SHA. Parser validate thành công chưa đủ bước này.
2. Build bình thường: secret scan → lint/typecheck → unit → hạ tầng tĩnh → observability tĩnh → build5images → integration PostgreSQL/RabbitMQ/Mailpit riêng → Trivy image + lockfiles. Kiểm tra JUnit không có integration skip và log từng gate. Hai bước cấu hình tĩnh không triển khai VM/cluster/monitoring.
3. Chạy SECURITY_DEMO=secret rồi critical. Cả hai build phải FAILURE tại demo, stage push/deploy phải SKIPPED. Fake token được sinh trong bộ nhớ và report redact; image Alpine cũ chỉ scan từ xa, không dùng chạy ứng dụng hay làm release.
4. Chạy candidate PUBLISH_IMAGES=true, IS_PR=false sau review phù hợp. `ci.release` đối chiếu commit/image ID/hash báo cáo/JUnit rồi login bằng stdin, push5tag SHA, lấy RepoDigest và pull từng digest. Lưu ci-out/release-manifest.json từ build thật; không tự điền digest.
5. Archive JUnit/security/build/push logs và manifest, ghi Jenkins build URL, commit, scanner versions, thời gian. Quét secret trên evidence trước commit. Production chưa deploy ở Mốc 2.

Mỗi build dùng checkout sạch; private file không trong build context. Integration có project clinic-ci-SHA12-UUID8 và volume riêng, cleanup chỉ project này; không down-v clinic-dev. Jenkins disableConcurrentBuilds và timeout60phút. Test hoặc scanner lỗi dừng trước push. [Jenkins Remote API](https://www.jenkins.io/doc/book/using/remote-access-api/) mô tả buildWithParameters/API token; [agent guidance](https://www.jenkins.io/doc/book/using/using-agents/) khuyến nghị controller0executor; [Matrix authorization](https://plugins.jenkins.io/matrix-auth/) cung cấp quyền relay.

## Git và giới hạn hiện tại

Remote public [vxxngw/DevOps](https://github.com/vxxngw/DevOps), chuyển từ Organization `vuongvo2207-gmail-com` ngày 18/11/2026; URL cũ redirect về cùng repository. Repo được chuyển sang public để GitHub Free áp dụng ruleset bảo vệ main (bản private từng trả 403). Trước khi public đã quét Gitleaks toàn bộ lịch sử: không có phát hiện. Nhánh, Conventional Commits, PR ≥1 review, squash merge và release-please (CHANGELOG + tag semver) theo [quy trình nhóm](team-workflow.md) và CONTRIBUTING. Không tự approve/merge để tạo bằng chứng.

Mốc 3 bổ sung overlay/migration Job/kubeconfig namespace, trusted HTTPS smoke, staging → approval có người/thời hạn → production dùng đúng digest, rollback đo thật. Các stage hiện dự kiến, sẽ báo lỗi nếu thiếu sản phẩm Mốc 3; không được dùng DEPLOY=true để công bố đã có Kubernetes.


Controller bật security, anonymous403/0executor; agent online/non-root và dùng Docker rootless qua mutual TLS. [Docker data đã chuyểnD và kiểm chứng](../evidence/docker-storage-latest.json). Tùy chọn timestamps() đã bỏ vì plugin set không có Timestamper; timeout và artifact timestamps vẫn giữ. [CI recovery](ci-recovery.md) giữ diễn biến lịch sử, gồm thời điểm agent còn offline; không dùng trạng thái cũ đó thay trạng thái hiện tại.


[Jenkins13](../evidence/backup-ci-runtime-20261115T142446Z/README.md) có đầy đủ JUnit, gate summary và kiểm hash7raw security report; runtime dùng image ID trùng report scan. [Jenkins11](../evidence/source-restructure-20261115T104329Z/README.md) là mốc refactor trước đó. GHCR, PRmain phù hợp/review thật và staging/production/VM/cluster chưa nghiệm thu. Git credential hiện tại không có write:packages; quyền push Git không thay quyền publish registry.

Engine phải có `DOCKER_TLS_SAN: DNS:engine` để chứng chỉ khớp `DOCKER_HOST=tcp://engine:2376`; kiểm thực sau recreate riêng engine đã qua, không tắt verify. [Webhook HTTPS local](../runbooks/github-webhook.md) có phiên bản tunnel/SHA256 ghim trong ci/cloudflared.json.


Kiểm chứng gate bổ sung15/11: [Jenkins6/7](../evidence/ci-agent-20261115T064424Z/publish-requested-negative-checks.json) yêu cầu PUBLISH_IMAGES=true, DEPLOY=false nhưng scanner thật phát hiện1secret/4CRITICAL, buildFAILURE và push SKIPPED_FOR_FAILURE; không chỉ chứng minh stage bị tắt bởi tham số. Không đăng nhập/push registry hoặc deploy.
