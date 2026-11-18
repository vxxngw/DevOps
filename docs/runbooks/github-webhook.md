# GitHub webhook cho Jenkins local

[THIẾT KẾ] Dùng Cloudflare Quick Tunnel làm HTTPS ingress tạm cho relay `127.0.0.1:18085`. Đây là lựa chọn phục vụ demo, không phải yêu cầu chọn nhà cung cấp trong PDF. Controller18090, Jenkins cũ8080 và Docker engine không được dùng làm origin. [Pin binary/hash](../../ci/cloudflared.json); [evidence hiện có](../evidence/ci-runtime-latest.json).

## Điều kiện và nguồn credential

Dedicated controller đã bật security, agent online; Docker dùng D và đủ dung lượng. Mật khẩu controller ở `.env.ci`; GitHub repo credential lấy từ GCM đã đăng nhập. `configure-webhook` tạo HMAC và token của `clinic-webhook` trong `.ci-local/webhook`, ngoài Git/Docker context. Không in nội dung file private.

```powershell
.\.venv\Scripts\python.exe scripts/ci/bootstrap-ci.py configure-webhook
docker compose --env-file .env.ci -f compose.ci.yaml --profile webhook build webhook
docker compose --env-file .env.ci -f compose.ci.yaml --profile webhook up -d --no-deps --no-build --wait webhook
```

Token relay chỉ có Overall/Read, Job/Read/Build. Trong kiểm chứng thật, GET API/job200; script/config403; credential endpoint404 với relay trong khi admin200. ACL thực xác nhận không admin/script/configure/view/create/update/delete credential. Không đổi quyền để làm HTTP test qua. Giữ cả lần collector đoán403 rồi nhận404 trong evidence.

HTTP local: GET `/health`200; POST `/github` thiếu/sai HMAC401; ping ký đúng200; repo sai400. Body tối đa1MiB, HMAC-SHA256 trên nguyên byte, repo chỉ `vxxngw/DevOps`, SHA40hex. `/login`, `/api/json` trên relay phải404.

## Binary và tunnel tạm

Tải đúng `url` trong ci/cloudflared.json vào `.ci-local/bin/cloudflared-VERSION.exe`, đối chiếu Get-FileHash SHA256 trước khi chạy `--version`. Không tự chuyển sang latest. Lượt thực tế dùng2026.11.0, kiểm hash asset từ release chính thức.

```powershell
$taskPin = Get-Content ci/cloudflared.json -Raw | ConvertFrom-Json
$taskExe = Join-Path (Resolve-Path .ci-local/bin) ('cloudflared-' + $taskPin.version + '.exe')
if ((Get-FileHash -LiteralPath $taskExe -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskPin.sha256) { throw 'Hash mismatch' }
Start-Process -FilePath $taskExe -ArgumentList @('tunnel','--no-autoupdate','--protocol','http2','--url','http://127.0.0.1:18085','--metrics','127.0.0.1:18086') -WindowStyle Hidden -RedirectStandardOutput .ci-local/webhook/tunnel-stdout.log -RedirectStandardError .ci-local/webhook/tunnel-stderr.log -PassThru
```

Đọc URL `https://....trycloudflare.com` từ log local; xác nhận health200 và service=clinic-webhook, unsignedPOST401, `/login` và `/api/json`404 qua chính URL đó. Chỉ sau khi đúng routing/auth mới cấu hình repo:

```powershell
.\.venv\Scripts\python.exe scripts/ci/bootstrap-ci.py github-webhook --public-url https://URL_TUNNEL_THUC_TE
```

Bootstrap chỉ tạo/cập nhật hook trùng endpoint, events push/pull_request, `insecure_ssl=0`, HMAC lấy từ file local. Giữ nguyên các hook khác. Thu ping200 thật từ GitHub, deliveryID/event/status/SHA/queue/build và user `clinic-webhook`; bỏ toàn bộ header/body/HMAC/token khỏi evidence công khai.

## Push, PR và bản ghi thực

Push nhánh tính năng phải tạo build đúng SOURCE_REF=SHA, SOURCE_BRANCH; PUBLISH_IMAGES=false/DEPLOY=false. Main push yêu cầu PUBLISH_IMAGES=true/DEPLOY=true: sau gate sẽ push GHCR, deploy staging và chờ duyệt thủ công trước production. Thiếu credential `clinic-ghcr`/kubeconfig thì build FAILURE tại stage push/deploy, không bỏ qua gate. PR phải cùng repo, không draft và base=main mới chạy IS_PR=true, publish/deploy=false. Draft hoặc base khác main được nhận200 rồi bỏ qua theo policy; delivery200 loại này không chứng minh PR build đã chạy.

CI hiện đã có ping200, push202 và build5SUCCESS đúng SHA. Source/header payload không được lưu công khai. Bản ghi gốc và các lượt lỗi ở [CI evidence](../evidence/ci-agent-20261115T064424Z/README.md). Các PRmain phù hợp hoặc release registry chỉ được đánh dấu khi có receipt thật.

Relay dùng SQLite payload-key để chống cùng body lặp; PENDING do crash giữa claim và queue phải được operator kiểm queue trước xử lý. Không hứa exactly-once. Muốn kiểm redelivery phải dùng delivery GitHub thật, đối chiếu HTTP200 Already accepted và số queue/build không tăng; chưa có bằng chứng thì giữ NOT_RUN.

## Vòng đời và dừng

Tunnel chỉ hoạt động khi process/máy local đang chạy; URL thay đổi sau restart. Không cài Windows service/autostart trong phiên này. Khi khởi động lại, kiểm port/origin/HMAC/ACL trước rồi cập nhật hook tới URL mới, tắt hook cũ đã xác nhận thuộc task. Không in private token khi điều tra502; xem relay JSON error_type và quyền/token/đường mạng nội bộ.

Phiên đang chạy ghi PID/executable/origin trong `.ci-local/webhook/tunnel-state.json`. Dừng đúng PID sau khi đối chiếu process executable khớp file ghim, không dừng mọi process cloudflared. Nếu kết thúc demo, tắt đúng hook của endpoint trước để các push sau không gửi đến URL hết hạn; đây là thao tác riêng, chưa tự thực hiện.

Nguồn: [Cloudflare Quick Tunnel](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/), [GitHub webhook delivery](https://docs.github.com/en/rest/repos/webhooks#list-deliveries-for-a-repository-webhook), [Jenkins Remote API](https://www.jenkins.io/doc/book/using/remote-access-api/). Các nguồn này mô tả cơ chế; receipt local/GitHub mới là bằng chứng đã chạy của dự án.
