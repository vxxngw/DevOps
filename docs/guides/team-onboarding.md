# Checklist onboarding cho nhóm 3 thành viên

Phân công đề xuất cho An Uyên Hospital – Đặt lịch khám có thông báo, cập nhật 15/11/2026. Nhóm gồm Vuong, Hoang và Long theo thông tin người dùng. Ánh xạ vai trò đề xuất: **TV1 = Hoang, TV2 = Vuong, TV3 = Long**; GitHub từng người còn cần điền trong [quy trình nhóm](team-workflow.md). Đây là trách nhiệm bàn giao tiếp theo, không phải bằng chứng ai đã thực hiện các kết quả cũ. Mọi checkbox bên dưới là công việc cần làm, chưa được đánh dấu hoàn thành thay thành viên.

## 1. Phân vai và review chéo

| Thành viên | Phụ trách chính | Phạm vi file chính | PR được review bởi |
|---|---|---|---|
| TV1 | Ứng dụng, sự kiện, QA và giám sát | services/, frontend/, tests/, observability/, scripts/infra/load-http.py, scripts/infra/load-queue.py, docs/guides/metrics-map.md | TV3 |
| TV2 | Git workflow, Docker/Jenkins, registry, security và release | ci/, Jenkinsfile, compose.ci*.yaml, .github/, docs/guides/ci-cd.md | TV1 |
| TV3 | Host Linux, Terraform, Ansible, Kubernetes, backup/restore | infra/, deploy/, scripts/infra/backup.sh, scripts/infra/restore.sh, docs/runbooks/infra-lab.md | TV2 |

TV1 có phần giám sát vì ứng dụng đã có nền tảng và bằng chứng chạy; TV3 không phải làm một mình toàn bộ monitoring. Thay đổi contract, migration, Jenkinsfile hoặc tài nguyên dùng chung phải thông báo cho hai người còn lại trước khi sửa.

## 2. Checklist chung – mỗi người tự hoàn thành

- [ ] **OB-01 – Danh tính và quyền:** điền tên/GitHub, cấu hình Git name/email thật; chủ repo cấp quyền repo private. Thống nhất kênh trao đổi và xác nhận đăng ký đề tài/backend theo yêu cầu lớp.
- [ ] **OB-02 – Đọc bối cảnh:** đọc README.md, CONTRIBUTING.md, [kiến trúc](architecture.md), [ma trận](../compliance-matrix.md), [CI evidence](../evidence/ci-runtime-latest.json). Phân biệt yêu cầu PDF, lựa chọn thiết kế và kết quả đã chạy. Một số đoạn README là snapshot cũ; dùng ma trận/evidence có thời điểm để đối chiếu.
- [ ] **OB-03 – Môi trường cá nhân:** clone bằng tài khoản riêng; kiểm phiên bản Git/Python/Node/Docker theo README và docs/guides/versions.md. Tạo env synthetic riêng theo hướng dẫn, không sao chép token, .env, state, kubeconfig hoặc password admin giữa các thành viên.
- [ ] **OB-04 – Cách làm việc:** tạo nhánh `codex/tv1/<task>`, `codex/tv2/<task>` hoặc `codex/tv3/<task>`; dùng Conventional Commits; mỗi PR có một người review thật. Không dùng chung tài khoản Git hoặc tự approve PR của mình.
- [ ] **OB-05 – Đọc một bộ bằng chứng:** chỉ ra commit, môi trường, lệnh, exit code, report và giới hạn. Giải thích vì sao unit skip khác integration skip; vì sao manifest hợp lệ chưa chứng minh cluster chạy.
- [ ] **OB-06 – Walkthrough chung:** mỗi người giải thích được booking → PostgreSQL/outbox → RabbitMQ → worker → SMTP/Mailpit, và push → Jenkins → scan → registry → staging → duyệt → production. Mỗi người đọc phần của hai bạn, không chỉ phần mình phụ trách.

Nếu cần xem Jenkins ở máy chung, chủ host cấp đường truy cập có kiểm soát và user riêng với quyền cần thiết. Các URL localhost trong repo chỉ truy cập trực tiếp từ máy đang chạy dịch vụ; không chia sẻ tài khoản clinic-admin hoặc mở Jenkins ra Internet để onboarding.

## 3. Công việc onboarding riêng và PR đầu tiên

### TV1 – Ứng dụng, QA, monitoring

- [ ] **TV1-O1:** đọc API/UI/event contract và notification runbook; vẽ lại luồng đặt, hủy, nhắc lịch, retry/DLQ bằng lời của mình. Chỉ ra nơi tạo outbox và nơi ghi SENT.
- [ ] **TV1-O2:** đối chiếu các tình huống đã có trong tests/ với booking, trùng slot, idempotency, ownership, hủy lịch và SMTP lỗi. Ghi rõ case nào là unit/fake, case nào dùng PostgreSQL/RabbitMQ/SMTP thật.
- [ ] **TV1-O3:** sau khi P0-01 cho phép chạy test, chạy một smoke trên môi trường được giao; lưu appointment/request ID synthetic, kết quả email và cleanup. Không chạy fault injection trên stack dùng chung khi chưa thống nhất cửa sổ demo.
- [ ] **TV1-O4 – PR đầu tiên:** bổ sung `docs/app-handoff.md`: cách lần theo một booking qua outbox/queue/email, cách chạy lại case và cách dọn dữ liệu synthetic. Kèm evidence hoặc ghi rõ phần chưa chạy. **TV3 review.**

Hoàn thành onboarding khi TV1 giải thích được luồng sự kiện, phân biệt các loại test và có một PR đã được review.

### TV2 – CI/CD, registry, security

- [ ] **TV2-O1:** đọc Jenkinsfile, ci/pipeline.py, ci/security.py và ci/release.py; liệt kê thứ tự gate, credential ID và điều kiện publish/deploy/PR.
- [ ] **TV2-O2:** đọc artifacts của một build xanh và một build âm. Đối chiếu JUnit, image ID/SHA, scan report, FAILURE và SKIPPED_FOR_FAILURE; kiểm việc che fingerprint công khai trong audit copy không thay raw report dùng cho gate.
- [ ] **TV2-O3:** kiểm đường truy cập Jenkins/agent/engine và relay theo runbook. Xác nhận controller 0 executor, agent non-root, Docker mutual TLS/rootless, relay chỉ READ/BUILD; mọi kiểm tra phải lưu kết quả thực.
- [ ] **TV2-O4 – PR đầu tiên:** cập nhật các đoạn trạng thái cũ trong README.md từ evidence đã có, bổ sung cách tìm build/artifact mới nhất. Không đổi trạng thái VM/cluster thành đã chạy. **TV1 review.**

Hoàn thành onboarding khi TV2 giải thích được vì sao một build bị chặn và cách đối chiếu image đã scan với image chuẩn bị phát hành.

### TV3 – Hạ tầng, Kubernetes, phục hồi

- [ ] **TV3-O1:** đọc infra/terraform, infra/ansible, deploy/k8s và [ngân sách tài nguyên](resource-budget.md); xác định state, inventory, secret và kubeconfig nằm ở đâu.
- [ ] **TV3-O2:** khảo sát host được giao: RAM, disk C/D, WSL/Linux/KVM, quyền SSH và dung lượng dự phòng. Đối chiếu preflight trước khi đề xuất chạy VM hoặc build lớn.
- [ ] **TV3-O3:** giải thích topology CI + k3s server/agent, staging/production tách dữ liệu, HPA API khác KEDA worker và cách backup/restore. Chỉ ra những phần mới có schema/syntax validation.
- [ ] **TV3-O4 – PR đầu tiên:** cập nhật docs/guides/resource-budget.md bằng số đo mới, host dự kiến và blocker. Profile 3 VM/32GiB host/160GiB trống là thiết kế hiện tại, không phải cấu hình phần cứng bắt buộc của PDF; thay đổi topology cần quyết định thiết kế và tiêu chí kiểm chứng rõ ràng. **TV2 review.**

Hoàn thành onboarding khi TV3 xác định được môi trường nào có thể triển khai và môi trường nào phải dừng ở chuẩn bị, có số đo thay cho phỏng đoán.

## 4. Backlog ưu tiên sau onboarding

| ID / ưu tiên | Owner chính | Việc cần hoàn thành | Điều kiện / bàn giao | Bằng chứng để đóng task |
|---|---|---|---|---|
| P0-01 | TV3 | Gỡ chặn host/dung lượng; thống nhất máy CI và host lab | Làm trước build/apply lớn. Lần kiểm gần nhất C còn rất ít chỗ và Docker đã từng dừng vì lỗi ghi log; phải đo lại. Không tự xóa backup hoặc đổi pagefile trên máy chung | Snapshot tài nguyên, host được chấp nhận, preflight và giới hạn tải được ghi rõ |
| P0-02 | TV2 + chủ repo | Chuẩn bị quyền GHCR và credential Jenkins đúng phạm vi | Chủ credential tự lưu/cấp quyền theo docs/guides/ci-cd.md; không gửi token lên chat/PR | Credential được dùng thành công; không lưu giá trị secret trong evidence |
| P0-03 | TV2 | Kiểm webhook cho PR phù hợp và quy trình review thật | PR cùng repo, không draft, base=main theo policy hiện tại; TV1 review | GitHub delivery → Jenkins đúng SHA/IS_PR, không publish/deploy trong PR; review thật |
| P1-01 | TV2 | Chốt candidate Mốc2: build/test/scan → push 5 image SHA → pull bằng digest | P0-01/02, tất cả gate đạt; giữ deploy tắt ở bước nghiệm thu registry | Jenkins URL, JUnit, raw security reports, release manifest và log pull từng digest |
| P1-02 | TV3 | Terraform provision và Ansible cấu hình host thật | Host/quyền/plan đã được chấp nhận; TV2 review thay đổi hạ tầng | Apply/state đúng phạm vi, SSH/user/UFW, recap lần2 changed=0, node Ready |
| P1-03 | TV3 | Kubernetes staging/production, TLS, probes/resources/RBAC | P1-01/02; TV1 kiểm smoke nghiệp vụ | Hai namespace, image digest đúng, TLS trusted, probes/permissions và smoke thật |
| P1-04 | TV1, TV3 hỗ trợ operator | Prometheus/Grafana/EFK và receiver cảnh báo | Chuẩn bị mapping/config song song; cài/chạy khi cluster đủ tài nguyên. TV2 kiểm scan/gate image | Targets có dữ liệu, panel từng service, Kibana tìm đúng request, FIRING/RESOLVED nhận thật |
| P1-05 | TV3, TV1 đo tải | HPA API và RabbitMQ + queue monitoring + KEDA worker | P1-03/04; nguồn metrics và queue/vhost đúng môi trường | CPU/replica timeline; ready/unacked/backlog tăng → worker tăng → drain → scale-down, có thông báo |
| P1-06 | TV3 | Bash backup/timer, restore DB thử và health host | Môi trường lab riêng, runbook rõ phạm vi | pg_dump/checksum, timer journal, restore DB mới và kiểm dữ liệu/nghiệp vụ; VHD backup không thay DB restore |
| P1-07 | TV2 điều phối, cả nhóm thực hiện | Staging → người duyệt thật → production, rollback và hồ sơ nộp | Staging đạt, cùng digest khi promote; role/credential đã cấp đúng | Approver/timestamp, rollout/request loop, rollback ≤120s đo thật, báo cáo/chi phí/postmortem/video |

TV1 có thể rà metric/test và chuẩn bị dashboard trong lúc TV2 làm registry, TV3 chuẩn bị host. Chỉ bắt đầu các phần runtime phụ thuộc sau khi điều kiện của dòng tương ứng có bằng chứng đạt. HPA/KEDA, monitoring và các mục bắt buộc được ưu tiên trước tracing, cosign hoặc các phần nâng cao khác.

## 5. Phân công 12 bài và 8 bước demo

| Bài | Owner chính | Phối hợp |
|---|---|---|
| 1–2: tổ chức nhóm/Git | TV2 điều phối | Cả ba cung cấp danh tính, commit và review thật |
| 3: Linux/Bash | TV3 | TV2 review vận hành/security |
| 4–6: Docker/Compose/Jenkins | TV2 | TV1 smoke/UI/event; TV3 host/tài nguyên |
| 7–9: Ansible/Terraform/Kubernetes | TV3 | TV2 CI/deploy; TV1 kiểm nghiệp vụ và tải |
| 10: monitoring/logging/alert | TV1 | TV3 operator/cluster; TV2 scan/secret |
| 11: security | TV2 | TV1 bảo mật API; TV3 SSH/TLS/RBAC |
| 12: production và chi phí | TV3 | TV2 release; TV1 số liệu workload |

| Demo PDF | Owner dẫn | Người hỗ trợ |
|---|---|---|
| 1. Terraform → Ansible → K8s | TV3 | TV2 |
| 2. Push → CI → staging → duyệt → production | TV2 | TV1 smoke/người duyệt được chỉ định, TV3 cluster |
| 3. Commit secret giả/thư viện lỗi → pipeline chặn | TV2 | TV1 review kịch bản; dùng nhánh thử có kiểm soát, không credential thật |
| 4. Xóa pod, dịch vụ liên tục | TV3 | TV1 đo request/error/p95 |
| 5. Load → HPA → Grafana → cảnh báo | TV1 | TV3 HPA, TV2 receiver/credential |
| 6. Lỗi → monitoring phát hiện → rollback ≤2 phút | TV2 | TV1 phát hiện/đo, TV3 khôi phục |
| 7. Request lỗi → log tập trung | TV1 | TV3 EFK |
| 8. Backlog RabbitMQ → KEDA → thông báo | TV3 | TV1 burst/queue/email, TV2 đối chiếu release |

Các job SECURITY_DEMO đã có không thay việc commit nhánh thử và đối chiếu deployment theo đúng demo PDF. Dọn ref thử qua quy trình đã thống nhất để không chặn pipeline chính. Không lấy worker recovery cũ thay cho rollback app ≤120s. Xem [kịch bản demo](demo-script.md) và [sản phẩm nộp](submission.md).

## 6. Owner của sản phẩm phải nộp

| Sản phẩm | Owner tập hợp | Người kiểm tra / phần bàn giao |
|---|---|---|
| Repo và README dựng từ máy trắng | TV2 | TV3 chạy phần hạ tầng, TV1 kiểm ứng dụng; chỉ ghi tái dựng thành công khi đã chạy thật |
| Báo cáo kiến trúc, công nghệ, pipeline, bảng phân công | TV2 | TV1 viết ứng dụng/sự kiện, TV3 viết hạ tầng; cả ba xác nhận đóng góp thật |
| Kết quả load test | TV1 | TV3 cung cấp resource/replica timeline, TV2 đối chiếu SHA/digest |
| Postmortem ít nhất một sự cố thật | TV2 | Người trực tiếp xử lý xác nhận timeline/evidence; cả ba nhận action cụ thể |
| Runbook deploy và rollback | TV2 | TV3 thực hiện drill, TV1 xác nhận nghiệp vụ và thời gian phục hồi |
| Runbook khôi phục DB | TV3 | TV1 kiểm dữ liệu/nghiệp vụ sau restore, TV2 review quyền và secret |
| Runbook từng loại cảnh báo, dashboard export, alert rules | TV1 | TV3 kiểm collector/operator, TV2 kiểm delivery/credential; cần bằng chứng UI và nhận tin thật |
| Video dự phòng tối đa 10 phút | TV1 điều phối ghi hình | TV2/TV3 trình bày phần mình; cả ba xem lại nội dung, thời lượng và dữ liệu nhạy cảm |

Bảng chi phí cloud do TV3 cập nhật vào báo cáo, có nguồn giá và ngày tra cứu. Checklist chi tiết giữ tại [sản phẩm nộp](submission.md); bảng này giao trách nhiệm, không xác nhận sản phẩm đã được nghiệm thu.

## 7. Definition of Done cho từng task

- [ ] Có owner thật, người review và dependency/blocker được ghi rõ.
- [ ] PR nhỏ, đúng nhánh; ≥1 review thật và checks phù hợp với thay đổi.
- [ ] Có evidence: môi trường, thời gian, commit/source hash, lệnh, exit code, log/report và giới hạn; không chứa credential hoặc dữ liệu người bệnh thật.
- [ ] Có kết quả reset/cleanup khi chạy test/demo; không sửa report hoặc bỏ gate để làm kết quả đạt.
- [ ] Cập nhật đúng dòng trong compliance-matrix.md. Chưa chạy ghi IMPLEMENTED_NOT_RUN; thiếu điều kiện ghi BLOCKED. Có file cấu hình không đồng nghĩa VERIFIED.
- [ ] Hai thành viên còn lại giải thích được phần vừa bàn giao ở mức đủ vấn đáp.
