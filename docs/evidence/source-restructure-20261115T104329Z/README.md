# Kiểm chứng tái cấu trúc source 15/11/2026

Các kiểm tra dưới đây chạy trên working tree sau refactor, trước commit phát hành; source hashes ghi tại [metadata](metadata.json). Không lấy Jenkins #8 trước refactor làm bằng chứng source mới đã chạy CI.

| Kiểm tra | Kết quả và phạm vi |
|---|---|
| CI lint | Ruff/format, ESLint, Prettier check, TypeScript/Vite build exit0 |
| Unit | 85 passed, 8 skipped. Bao gồm tests ứng dụng và ci/tests, có 4 test helper đường dẫn WSL mới |
| Integration | Lần đầu 33 setup errors vì postgres/rabbitmq/mailpit đã dừng sau Docker restart. Đã khởi động đúng 4 container dev giữ nguyên volume. Retry 33 passed, 0 skipped |
| Source integration | services/contracts/tests hiện tại bind read-only vào image dev có sẵn. DB PostgreSQL và queue test riêng, SMTP Mailpit thật. Không phải build/scan image SHA mới |
| Browser | [Soft Minimal](../ui-20261115T105819Z/metadata.json): 10 checks trên Edge thật, Vite và API source mới, SQLite riêng; không chứng minh SMTP từ browser |
| Jenkinsfile | Controller thật trả `Jenkinsfile successfully validated`. Parser không thay một pipeline mới |
| Compose | Dev, CI và CI VM override đều config --quiet exit0 |
| Dependency security | Trivy lock Python/Node gồm dev dependency và Prettier3.6.2: exit0, không CRITICAL. Không thay scan image |
| Secret precommit | Snapshot 1305 file không chứa env/private/output: Gitleaks exit0, 0 finding |
| Portability | Checkout có khoảng trắng, cwd khác, init-env không ghi đè và env thật giữ nguyên; 5 Bash script parse được; PowerShell parser không lỗi |
| Bảo toàn hành vi | [Audit](structure-audit.json): 18 route và 18 body nghiệp vụ giữ nguyên, chỉ truyền request_id tường minh qua lớp router |
| Bảo toàn evidence | Raw snapshot/report/log cũ giữ nguyên byte. Hai chỉ mục điều hướng docs/evidence/README.md và ci-runtime-latest.json được cập nhật; audit ban đầu trước đổi pointer ghi1002 file, kiểm cuối còn1001 file giữ nguyên và hai pointer đổi có chủ đích |

Giữ cả [log integration lần đầu](integration-bind-source.log), [JUnit lần đầu](junit-integration-attempt1.xml), [log retry](integration-bind-source-retry-2.log), [JUnit retry](junit.xml) và [recovery](dev-runtime-recovery.json). Không đổi lỗi môi trường đầu tiên thành kết quả đạt. Có một warning deprecation TestClient từ dependency hiện tại; không có test failure trong lần retry.

Windows từng chỉ còn khoảng0,25GiB trên C và một lần PowerShell lỗi lúc startup. Snapshot sau đã có khoảng3,48GiB C và1,38GiB RAM khả dụng; browser được chạy sau khi đo lại đủ tài nguyên. Một pipeline Jenkins mới chỉ được công bố khi đúng commit sau refactor chạy thật. GHCR publication và K8s runtime vẫn có phạm vi/blocker riêng trong [ma trận](../../compliance-matrix.md).

## Kết quả cuối trên image và pipeline thật

[Final summary](final-summary.json) đối chiếu source `32f4343f8bb800053faf81bfce1d171b3fcbf697` với [Jenkins #11](http://localhost:18090/job/an-uyen/job/clinic-pipeline/11/), [JUnit/security receipts](jenkins-11/summary.json) và [SHA runtime](sha-runtime/metadata.json). Unit92passed/8skipped, integration33passed/0skipped, đủ5image0CRITICAL. Chạy full stack9service/job trong project thử riêng,7healthy/non-root và2jobsexit0; đặt/hủy/email body khớp,9backend HTTPchecks và frontend200, JSON logs3backend; cleanup0.

[Webhook](repository-webhook-verification.json) ghi GitHub push202 cùng repo ID1457478642 → user clinic-webhook → Jenkins11 đúng SHA, publish/deploy=false. Health200, login404, unsigned401, signed wrong-repo400. Push đầu502 được giữ nguyên trong receipt. Repo vẫn private sau redirect; quyền/HMAC và marker ownership được giữ, kiểm ID/name được bổ sung.

Các kết quả85unit native ở phần chuẩn bị là snapshot trước bổ sung7regression CI; kết quả92unit của Jenkins11 là source mới hơn. Parser không thay pipeline, bind-source integration không thay image-SHA runtime; cả hai phạm vi hiện có bằng chứng riêng. Không có GHCR publish hoặc triển khai K8s trong lượt này.
