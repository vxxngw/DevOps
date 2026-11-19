# Bằng chứng Bài 4 (push GHCR) và Bài 6 (Jenkins, webhook) – 19/11/2026 UTC

Jenkins riêng `localhost:18090` (controller + agent + engine), relay webhook `127.0.0.1:18085` qua Cloudflare Quick Tunnel; GitHub hook `713783232` (events `push`, `pull_request`, kiểm TLS). URL tunnel không ghi ở đây vì repo public.

| Yêu cầu | Kết quả | File |
|---|---|---|
| Bài 4 – image tag theo commit SHA và đẩy lên GHCR | Build #22: 5 image `ghcr.io/vxxngw/devops-{app,frontend,postgres,rabbitmq,mailpit}:269519e…` đã push và pull lại theo digest; manifest ghi tag, image ID và digest từng image | [release-manifest.json](release-manifest.json), [builds.txt](builds.txt) |
| Bài 6 – Jenkinsfile declarative, đủ stage theo thứ tự | `Jenkinsfile` trong repo; #22 chạy thật checkout → lint → unit test → build image → quét bảo mật → push | [builds.txt](builds.txt) |
| Bài 6 – Webhook push | Merge #31 vào `main` → relay `queued` commit `269519e` → build #22 bởi user `clinic-webhook` với `PUBLISH_IMAGES=true`, `DEPLOY=true` (chính sách nhánh main) | [webhook-queued.jsonl](webhook-queued.jsonl) |
| Bài 6 – Webhook Pull Request | Release PR #32 → relay `queued` commit `1753510a`, `is_pr: true` | [webhook-queued.jsonl](webhook-queued.jsonl) |
| Bài 6 – Secret trong Jenkins Credentials | `clinic-github` (folder), `clinic-ghcr` (system) dùng qua `withCredentials`, token được che trong log | [builds.txt](builds.txt) |
| Bài 6 – deploy staging → duyệt thủ công → deploy production | **Chưa chạy**: #22 dừng ở "Deploy staging" vì chưa có credential `clinic-kubeconfig-staging` (cần cụm k3s Bài 9 và 5 credential deploy) | [builds.txt](builds.txt) |

Lịch sử lỗi giữ nguyên: #17/#19/#20 lỗi lint (sửa ở #27), #21 lỗi pull kiểm tra digest do GHCR chậm đồng bộ (sửa ở #31). Package GHCR đang để mặc định (private).
