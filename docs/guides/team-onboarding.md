# Checklist onboarding cho nhóm 4 thành viên

Phân công cho An Uyên Hospital – Đặt lịch khám có thông báo, đồng bộ 16/11/2026 với [bảng task của nhóm](https://docs.google.com/spreadsheets/d/1py3DJf2rO_x2zK0-LcE8tERMtrn2S5lINx7nbnM8-48/edit). Nhóm gồm **Vuong, Hoang, Long, Thien**; **TV1 = Hoang, TV2 = Vuong, TV3 = Long, TV4 = Thien**. GitHub từng người còn cần điền trong [quy trình nhóm](team-workflow.md). Đây là trách nhiệm bàn giao tiếp theo, không phải bằng chứng ai đã thực hiện các kết quả cũ. Mọi checkbox bên dưới là công việc cần làm, chưa được đánh dấu hoàn thành thay thành viên.

Bảng có **50 task**: 24 task chung (6 task × 4 người), 16 task riêng (4 task × 4 người) và 10 task backlog. Vuong nhận 14, Hoang 11, Long 13, Thien 12; số task không phải ước lượng số giờ. Giữ 40 ID cũ; bổ sung `TV4-OB-01` đến `TV4-OB-06` và `TV4-O1` đến `TV4-O4`.

## 1. Phân vai và review chéo

| Thành viên | Phụ trách chính | Phạm vi file chính | PR được review bởi |
|---|---|---|---|
| TV1 / Hoang | Ứng dụng, sự kiện, QA, monitoring/logging/alert | services/, frontend/, tests/, observability/, scripts/infra/load-http.py, scripts/infra/load-queue.py, docs/guides/metrics-map.md | TV3 / Long |
| TV2 / Vuong | Điều phối, Git, Docker/Compose/Jenkins, registry, CI security và release | ci/, Jenkinsfile, compose.ci*.yaml, .github/, docs/guides/ci-cd.md | TV1 / Hoang |
| TV3 / Long | Host Linux/Bash, Terraform, Ansible, backup/timer và chi phí | infra/, scripts/infra/backup.sh, scripts/infra/restore.sh, docs/guides/resource-budget.md | TV4 / Thien |
| TV4 / Thien | Kubernetes, HPA/KEDA, TLS/RBAC, rollout/rollback | deploy/k8s/, ci/deploy.py, ci/rollback.py, docs/runbooks/infra-lab.md | TV2 / Vuong |

Vòng review: **Vuong → Hoang → Long → Thien → Vuong**. Hoang chịu trách nhiệm nội dung metric/dashboard/alert; Thien hỗ trợ operator, EFK và cluster; Long cấp host/node Ready; Vuong bàn giao image/CI và hỗ trợ credential riêng. Thay đổi contract, migration, Jenkinsfile hoặc tài nguyên dùng chung cần phối hợp với ba người còn lại.

## 2. Checklist chung – mỗi người tự hoàn thành

- [ ] **OB-01 – Danh tính và quyền:** điền tên/GitHub, cấu hình Git name/email thật; chủ repo cấp quyền repo private. Thống nhất kênh trao đổi và xác nhận đăng ký đề tài/backend theo yêu cầu lớp.
- [ ] **OB-02 – Đọc bối cảnh:** đọc README.md, CONTRIBUTING.md, [kiến trúc](architecture.md), [ma trận](../compliance-matrix.md), [CI evidence](../evidence/ci-runtime-latest.json). Phân biệt yêu cầu PDF, lựa chọn thiết kế và kết quả đã chạy. Một số đoạn README là snapshot cũ; dùng ma trận/evidence có thời điểm để đối chiếu.
- [ ] **OB-03 – Môi trường cá nhân:** clone bằng tài khoản riêng; kiểm phiên bản Git/Python/Node/Docker theo README và docs/guides/versions.md. Tạo env synthetic riêng theo hướng dẫn, không sao chép token, .env, state, kubeconfig hoặc password admin giữa các thành viên.
- [ ] **OB-04 – Cách làm việc:** tạo nhánh `codex/tv1/<task>`, `codex/tv2/<task>`, `codex/tv3/<task>` hoặc `codex/tv4/<task>`; dùng Conventional Commits; mỗi PR có một người review thật. Không dùng chung tài khoản Git hoặc tự approve PR của mình.
- [ ] **OB-05 – Đọc một bộ bằng chứng:** chỉ ra commit, môi trường, lệnh, exit code, report và giới hạn. Giải thích vì sao unit skip khác integration skip; vì sao manifest hợp lệ chưa chứng minh cluster chạy.
- [ ] **OB-06 – Walkthrough chung:** mỗi người giải thích được booking → PostgreSQL/outbox → RabbitMQ → worker → SMTP/Mailpit, và push → Jenkins → scan → registry → staging → duyệt → production. Mỗi người đọc phần của ba bạn, không chỉ phần mình phụ trách.

ID trong Sheet thêm tiền tố của người nhận, ví dụ `TV1-OB-01` và `TV4-OB-01`. Mỗi người tự hoàn thành cả 6 bước; chưa có ngày hạn được thống nhất nên giữ ô hạn trống.

Nếu cần xem Jenkins ở máy chung, chủ host cấp đường truy cập có kiểm soát và user riêng với quyền cần thiết. Các URL localhost trong repo chỉ truy cập trực tiếp từ máy đang chạy dịch vụ; không chia sẻ tài khoản clinic-admin hoặc mở Jenkins ra Internet để onboarding.

## 3. Công việc onboarding riêng và PR đầu tiên

### TV1 – Ứng dụng, QA, monitoring

- [ ] **TV1-O1:** đọc API/UI/event contract và notification runbook; vẽ lại luồng đặt, hủy, nhắc lịch, retry/DLQ bằng lời của mình. Chỉ ra nơi tạo outbox và nơi ghi SENT.
- [ ] **TV1-O2:** đối chiếu các tình huống đã có trong tests/ với booking, trùng slot, idempotency, ownership, hủy lịch và SMTP lỗi. Ghi rõ case nào là unit/fake, case nào dùng PostgreSQL/RabbitMQ/SMTP thật.
- [ ] **TV1-O3:** sau khi P0-01 cho phép chạy test, chạy một smoke trên môi trường được giao; lưu appointment/request ID synthetic, kết quả email và cleanup. Không chạy fault injection trên stack dùng chung khi chưa thống nhất cửa sổ demo.
- [ ] **TV1-O4 – PR đầu tiên:** tạo tài liệu dự kiến `docs/guides/app-handoff.md`: cách lần theo một booking qua outbox/queue/email, cách chạy lại case và cách dọn dữ liệu synthetic. Kèm evidence hoặc ghi rõ phần chưa chạy. **Long review.**

Hoàn thành onboarding khi TV1 giải thích được luồng sự kiện, phân biệt các loại test và có một PR đã được review.

### TV2 – CI/CD, registry, security

- [ ] **TV2-O1:** đọc Jenkinsfile, ci/pipeline.py, ci/security.py và ci/release.py; liệt kê thứ tự gate, credential ID và điều kiện publish/deploy/PR.
- [ ] **TV2-O2:** đọc artifacts của một build xanh và một build âm. Đối chiếu JUnit, image ID/SHA, scan report, FAILURE và SKIPPED_FOR_FAILURE; kiểm việc che fingerprint công khai trong audit copy không thay raw report dùng cho gate.
- [ ] **TV2-O3:** kiểm đường truy cập Jenkins/agent/engine và relay theo runbook. Xác nhận controller 0 executor, agent non-root, Docker mutual TLS/rootless, relay chỉ READ/BUILD; mọi kiểm tra phải lưu kết quả thực.
- [ ] **TV2-O4 – PR đầu tiên:** cập nhật các đoạn trạng thái cũ trong README.md từ evidence đã có, bổ sung cách tìm build/artifact mới nhất. Không đổi trạng thái VM/cluster thành đã chạy. **TV1 review.**

Hoàn thành onboarding khi TV2 giải thích được vì sao một build bị chặn và cách đối chiếu image đã scan với image chuẩn bị phát hành.

### TV3 / Long – Hạ tầng, Linux, phục hồi

- [ ] **TV3-O1:** đọc infra/terraform, infra/ansible và [ngân sách tài nguyên](resource-budget.md); xác định state, inventory và Vault. Phối hợp bàn giao node Ready cho Thien; Thien nhận Kubernetes/kubeconfig.
- [ ] **TV3-O2:** khảo sát host được giao: RAM, disk C/D, WSL/Linux/KVM, quyền SSH và dung lượng dự phòng. Đối chiếu preflight trước khi đề xuất chạy VM hoặc build lớn.
- [ ] **TV3-O3:** giải thích topology CI + k3s server/agent, tách dữ liệu staging/production và backup/restore. Biết điểm bàn giao HPA/KEDA cho Thien; chỉ rõ schema/syntax khác runtime.
- [ ] **TV3-O4 – PR đầu tiên:** cập nhật docs/guides/resource-budget.md bằng số đo mới, host dự kiến và blocker. **PDF trang 1 yêu cầu 3 VM nếu chọn local**; host 32GiB/160GiB trống là ước lượng thiết kế, cần đo và review. **Thien review.**

Hoàn thành onboarding khi TV3 xác định được môi trường nào có thể triển khai và môi trường nào phải dừng ở chuẩn bị, có số đo thay cho phỏng đoán.

### TV4 / Thien – Kubernetes, autoscale, TLS/RBAC

- [ ] **TV4-O1:** đọc deploy/k8s/bootstrap/overlays và runbook infra-lab; giải thích Deployment/Service/Ingress/ConfigMap/Secret, hai namespace, probes, requests/limits và quyền. Liệt kê phần chỉ validate, điều kiện Secret/cluster và cách kiểm runtime.
- [ ] **TV4-O2:** phối hợp Hoang đọc metrics-map và event contract; phân biệt HPA API theo CPU và KEDA worker theo queue/vhost. Xác định ready/unacked/backlog, TriggerAuthentication và bằng chứng scale-up → drain → scale-down. Ngưỡng CPU/replica/queue là thiết kế; RabbitMQ/giám sát queue/KEDA là bắt buộc của đề tài.
- [ ] **TV4-O3:** đọc cert-manager, trusted HTTPS, namespace Role/ServiceAccount và `auth can-i`; app không tự gắn API token. Lập cách kiểm rollout, pod recovery, bản lỗi và rollback ≤120s. Vuong hỗ trợ CI/security; Long bàn giao host.
- [ ] **TV4-O4 – PR đầu tiên:** tạo tài liệu dự kiến `docs/guides/k8s-handoff.md`: cấu hình, điều kiện host/Secret/image/receiver, lệnh kiểm TLS/RBAC/HPA/KEDA/rollback, bằng chứng đã có và phần chưa chạy. **Vuong review bằng tài khoản riêng.**

Hoàn thành onboarding khi Thien giải thích được cấu hình đang có, điểm bàn giao từ Long/Vuong/Hoang và có PR được review thật. Không lấy schema hợp lệ hoặc kết quả cũ của dự án làm bằng chứng Thien đã triển khai cluster.

## 4. Backlog ưu tiên sau onboarding

| ID / ưu tiên | Owner chính | Việc cần hoàn thành | Điều kiện / bàn giao | Bằng chứng để đóng task |
|---|---|---|---|---|
| P0-01 | TV3 | Gỡ chặn host/dung lượng; thống nhất máy CI và host lab | Làm trước build/apply lớn. Lần kiểm gần nhất C còn rất ít chỗ và Docker đã từng dừng vì lỗi ghi log; phải đo lại. Không tự xóa backup hoặc đổi pagefile trên máy chung | Snapshot tài nguyên, host được chấp nhận, preflight và giới hạn tải được ghi rõ |
| P0-02 | TV2 + chủ repo | Chuẩn bị quyền GHCR và credential Jenkins đúng phạm vi | Chủ credential tự lưu/cấp quyền theo docs/guides/ci-cd.md; không gửi token lên chat/PR | Credential được dùng thành công; không lưu giá trị secret trong evidence |
| P0-03 | TV2 / Vuong | Main protection, webhook PR, commit/review và semver thật | PR không draft, base=main; Hoang review. API protection vẫn 403 ở snapshot 16/11; không tự đổi visibility/gói | Rule main enforce; delivery → Jenkins đúng SHA/IS_PR; ≥1 review; Conventional Commits của đủ 4 người và tag semver |
| P1-01 | TV2 | Chốt candidate Mốc2: build/test/scan → push 5 image SHA → pull bằng digest | P0-01/02, tất cả gate đạt; giữ deploy tắt ở bước nghiệm thu registry | Jenkins URL, JUnit, raw security reports, release manifest và log pull từng digest |
| P1-02 | TV3 / Long | Terraform provision và Ansible cấu hình host thật | P0-01, host/quyền/plan đã chấp nhận; Thien review và nhận node Ready, Vuong hỗ trợ CI | Apply/state đúng phạm vi, SSH/user/UFW, recap lần2 changed=0, node Ready |
| P1-03 | TV4 / Thien | Kubernetes staging/production, TLS, probes/resources/RBAC | P1-01/02; Long bàn giao node, Vuong image/CI; Hoang smoke | Hai namespace, image đúng release, TLS trusted, probes/permissions và smoke thật; Vuong review |
| P1-04 | TV1 / Hoang | Prometheus/Grafana/EFK và receiver cảnh báo | Thien hỗ trợ operator/cluster, Long host, Vuong credential riêng; chuẩn bị mapping song song | Targets/panel có dữ liệu, Kibana tìm đúng request, FIRING/RESOLVED nhận thật; Long review |
| P1-05 | TV4 / Thien | HPA API và RabbitMQ + queue monitoring + KEDA worker | P1-03/04; Hoang tạo tải/kiểm email, Long host; đúng queue/vhost | CPU/replica timeline; ready/unacked/backlog tăng → worker tăng → drain → giảm, có thông báo; Vuong review |
| P1-06 | TV3 / Long | Hoàn tất timer/host health Linux và kiểm SSH/UFW trên lab | [Dev drill đã qua](../evidence/backup-restore-20261115T134405Z/README.md): pg_dump/checksum/retention, 9 bảng/46 định nghĩa schema, API/outbox/cleanup; Thien review | Timer journal/health host/SSH key-only/root deny/UFW thật. Restore dev không thay production; restore drill là nâng cao Bài 3, không chặn hoàn tất phần bắt buộc |
| P1-07 | TV2 / Vuong điều phối | Staging → duyệt thật → production, rollback và hồ sơ nộp | Thien rollout/rollback, Hoang nghiệp vụ/alert/video, Long host/restore/chi phí; Hoang review | Approver/timestamp, rollout/request loop, rollback ≤120s đo thật, báo cáo/chi phí/postmortem/video |

Hoang chuẩn bị metric/test/dashboard, Vuong registry/Git, Long host/IaC và Thien Kubernetes/TLS/KEDA song song. Chỉ bắt đầu runtime sau khi phụ thuộc có bằng chứng đạt. HPA/KEDA, monitoring và các mục bắt buộc được ưu tiên trước tracing, cosign hoặc phần nâng cao khác. P0-01 do Thien review; P0-02/P1-01 do Hoang review.

## 5. Phân công 12 bài và 8 bước demo

| Bài | Owner chính | Phối hợp |
|---|---|---|
| 1–2: tổ chức nhóm/Git | Vuong điều phối | Cả 4 cung cấp danh tính, commit và review thật; kênh/đăng ký lớp còn cần xác nhận |
| 3: Linux/Bash | Long | Thien review; Hoang kiểm nghiệp vụ khi có restore |
| 4–6: Docker/Compose/Jenkins | Vuong | Hoang smoke/review; Long host; Thien deployment |
| 7–8: Ansible/Terraform | Long | Thien review/nhận node Ready; Vuong CI |
| 9: Kubernetes | Thien | Long host; Vuong image/CI; Hoang smoke/tải |
| 10: monitoring/logging/alert | Hoang | Thien operator/cluster; Long host; Vuong scan/credential |
| 11: security | Vuong (CI), Thien (TLS/RBAC) | Hoang API; Long SSH/UFW |
| 12: chi phí theo phương án local | Long | Thien cấu hình K8s; Vuong release; Hoang workload; production thực còn ở Bài 6/9 |

| Demo PDF | Owner dẫn | Người hỗ trợ |
|---|---|---|
| 1. Terraform → Ansible → K8s | Long | Thien cluster; Vuong CI |
| 2. Push → CI → staging → duyệt → production | Vuong | Thien deploy; Hoang smoke; Long host; approver thực được chỉ định |
| 3. Commit secret giả/thư viện lỗi → pipeline chặn | Vuong | Hoang review kịch bản, Thien kiểm deployment; không credential thật |
| 4. Xóa pod, dịch vụ liên tục | Thien | Hoang đo request/error/p95; Long host |
| 5. Load → HPA → Grafana → cảnh báo | Hoang | Thien HPA; Long host; Vuong receiver/credential |
| 6. Lỗi → monitoring phát hiện → rollback ≤2 phút | Thien | Hoang phát hiện/đo; Vuong CI; Long host |
| 7. Request lỗi → log tập trung | Hoang | Thien EFK/operator; Long host |
| 8. Backlog RabbitMQ → KEDA → thông báo | Thien | Hoang burst/queue/email; Vuong release; Long host |

Các job SECURITY_DEMO đã có không thay việc commit nhánh thử và đối chiếu deployment theo đúng demo PDF. Dọn ref thử qua quy trình đã thống nhất để không chặn pipeline chính. Không lấy worker recovery cũ thay cho rollback app ≤120s. Xem [kịch bản demo](demo-script.md) và [sản phẩm nộp](submission.md).

## 6. Owner của sản phẩm phải nộp

| Sản phẩm | Owner tập hợp | Người kiểm tra / phần bàn giao |
|---|---|---|
| Repo và README dựng từ máy trắng | Vuong | Long hạ tầng, Thien Kubernetes, Hoang ứng dụng; cần tái dựng thật |
| Báo cáo kiến trúc, công nghệ, pipeline, phân công | Vuong | Hoang app/monitoring, Long IaC, Thien K8s/security; cả 4 xác nhận đóng góp thật |
| Kết quả load test | Hoang | Thien replica timeline, Long tài nguyên, Vuong SHA/digest |
| Postmortem ít nhất một sự cố thật | Vuong | Người xử lý xác nhận timeline/evidence; cả 4 nhận action cụ thể |
| Runbook deploy và rollback | Thien | Vuong CI, Hoang nghiệp vụ/đo thời gian, Long host |
| Runbook khôi phục DB | Long | Hoang dữ liệu/nghiệp vụ; Vuong review; Thien lab |
| Runbook cảnh báo, dashboard export, alert rules | Hoang | Thien operator, Vuong credential, Long host; cần UI/nhận tin thật |
| Video dự phòng tối đa 10 phút | Hoang điều phối | Cả Vuong, Hoang, Long, Thien trình bày và xem lại footage/thời lượng |
| Bảng ước tính chi phí cloud | Long | Thien K8s, Vuong release, Hoang workload; nguồn giá/ngày/region/giả định |

Bảng chi phí cloud do TV3 cập nhật vào báo cáo, có nguồn giá và ngày tra cứu. Checklist chi tiết giữ tại [sản phẩm nộp](submission.md); bảng này giao trách nhiệm, không xác nhận sản phẩm đã được nghiệm thu.

## 7. Definition of Done cho từng task

- [ ] Có owner thật, người review và dependency/blocker được ghi rõ.
- [ ] PR nhỏ, đúng nhánh; ≥1 review thật và checks phù hợp với thay đổi.
- [ ] Có evidence: môi trường, thời gian, commit/source hash, lệnh, exit code, log/report và giới hạn; không chứa credential hoặc dữ liệu người bệnh thật.
- [ ] Có kết quả reset/cleanup khi chạy test/demo; không sửa report hoặc bỏ gate để làm kết quả đạt.
- [ ] Cập nhật đúng dòng trong compliance-matrix.md. Chưa chạy ghi IMPLEMENTED_NOT_RUN; thiếu điều kiện ghi BLOCKED. Có file cấu hình không đồng nghĩa VERIFIED.
- [ ] Ba thành viên còn lại giải thích được phần vừa bàn giao ở mức đủ vấn đáp.

## 8. Trạng thái tại thời điểm bàn giao

[Kiểm tra chỉ đọc 03:14–03:16 ngày 16/11/2026 Việt Nam](../evidence/team-four-handoff-20261115T201450Z/README.md): Docker và các container clinic dev/CI healthy; 11 endpoint HTTP trả 200. Jenkins gần nhất #14 SUCCESS trên `adb5dbd`, publish/deploy=false; đây là build cũ được đọc lại, không phải build của tài liệu vừa sửa.

C còn khoảng 0,20GiB, D 9,09GiB; `.registry-token` chưa có. Main vẫn protected=false, API protection/rulesets trả 403; chưa có tag, PR đang mở là draft #2 với base khác main. VM/Ansible/cluster/HPA/KEDA/TLS/monitoring vẫn chưa có runtime được nghiệm thu. Không thay các trạng thái cá nhân trong Sheet từ kết quả chung này.
