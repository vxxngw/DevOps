# Phiên bản, nguồn kỹ thuật và phạm vi xác nhận

Cập nhật 14/11/2026 (Asia/Ho_Chi_Minh). Không dùng tag latest. Pin không thay security scan. `requirements.in` là phạm vi đầu vào, **requirements.lock** ghim toàn bộ Python đã resolve; frontend package-lock.json có phiên bản và integrity. Terraform/libvirt đã có lock Windows/Linux ở Mốc 3; chưa cài cluster. Monitoring dùng manifest/Kustomize riêng, không dùng chart chưa ghim.

| Thành phần | Phiên bản chọn / môi trường quan sát | Lý do / giới hạn |
|---|---|---|
| Python | Host 3.12.6; image mới3.12.16-slim-trixie ghim digest trong Dockerfile | Nền M1 cũ3.12.12-bookworm có9CRITICAL; nền mới remote scan0CRITICAL, custom image chưa build/run/scan |
| FastAPI / SQLAlchemy / Alembic | 0.162.6 / 2.0.57 / 1.20.1 | Resolve trong phạm vi requirements.in và kiểm tra thực; API SQLAlchemy 2.0 được giữ riêng |
| psycopg / Pika | 3.3.9 / 1.4.4 | Driver PostgreSQL và AMQP blocking confirms/manual ack |
| Prometheus client / PyJWT / pwdlib | 0.26.0 / 2.15.1 / 0.3.1 | Metrics, JWT có expiry và Argon2; tất cả trong lock |
| Pydantic settings / pytest / Ruff | 2.16.3 / 9.2.0 / 0.17.5 | Env config, checks; Starlette 1.10.0 hiện cảnh báo TestClient/httpx deprecation, chưa bỏ cảnh báo để che lỗi |
| PostgreSQL | 17.12-alpine3.24, digest `sha256:34261f594522cf41dfcb76aefd42b9d201098b0e6b23c9c68733f169e4218b6f` | Variant chính thức đã đọc passwd/user/version. Bookworm local có passwd rỗng; không kết luận lỗi upstream. Dùng volume mới `postgres-data-alpine`, không xóa volume cũ |
| RabbitMQ | 4.2.9-management | Quorum retry + at-least-once DLX; bật management/Prometheus plugins; broker dev một node không HA |
| Mailpit | v1.33.1 ghim digest, binary sang Alpine3.24 | Nguồn cũ1.27.10 có3CRITICAL; nguồn mới remote scan0CRITICAL. Custom image/SMTP test sau upgrade chưa chạy |
| Node / React / TypeScript / Vite | Host/build Node24.22.1; React19.2.0; TS5.9.3; Vite7.2.2 | Node build dùng Alpine3.24; agent dùng trixie-slim; native build đã chạy, build image mới chưa chạy |
| Nginx / Playwright | 1.30.6-alpine3.24 ghim digest / 1.65.0 | Nền cũ1.28.0 có3CRITICAL/EOL Alpine; nền mới remote scan0CRITICAL. Frontend image mới chưa chạy |
| Inter / Fontsource | @fontsource/inter 5.3.0, lockfile npm | Font Inter tự phục vụ, gồm tiếng Việt và weight400/500/600; SIL OFL1.1 |
| Docker | Đầu phiên CLI 29.4.0/Desktop 4.69.0; sau phục hồi CLI/engine 29.9.3, Desktop 4.99.0, Compose v5.7.0 | Ghi đúng môi trường thay đổi trong phiên; không ghim phiên bản Docker của máy thay người dùng |
| ESLint / TypeScript ESLint / React Hooks | 10.15.0 / 8.72.2 / 7.1.1; @eslint/js10.0.1, globals17.14.0 | Exact versions/lockfile; nguồn npm registry chính thức; lint native đạt. ESLint9 đã EOL nên không giữ bộ cài thử9.39.1 |
| Gitleaks / Trivy | 8.30.1 / 0.76.2 | Native binary đối chiếu SHA256 release chính thức; image CI cùng phiên bản; chưa có scan release image |
| Jenkins / inbound agent | 2.580.1-jdk21 / 3391.va_37fa_a_305d6d-5-jdk21 | ci/tools.json và Dockerfile; parser Jenkins cũ đã validate, controller mới chưa build/run |
| Jenkins plugins | ci/controller/plugins.txt, plugins-lock.json | 8 direct plugins, chọn bản compatible core từ update center chính thức; transitive resolver --latest=false chưa chạy, cần lưu kết quả khi build |

Nguồn Mốc2 kiểm tra14/11/2026: [Jenkins update center](https://updates.jenkins.io/update-center.actual.json), [Gitleaks releases](https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1), [Trivy releases](https://github.com/aquasecurity/trivy/releases/tag/v0.76.2), npm registry của eslint/typescript-eslint/react-hooks. Dockerfile CI ghi tag cụ thể; chưa coi pin tag là bằng chứng image đã build hoặc không CVE.

Tài liệu chính thức đã đọc để chọn cách triển khai:

- [RabbitMQ publisher confirms và consumer acknowledgements](https://www.rabbitmq.com/docs/confirms): hai cơ chế xác nhận độc lập; dùng mandatory để phát hiện thiếu route và manual ack sau khi xử lý.
- [RabbitMQ 4.2 quorum queues](https://www.rabbitmq.com/docs/4.2/quorum-queues): kiểm tra tính năng retry TTL/dead lettering theo dòng 4.2. Quorum một node vẫn là điểm lỗi chung.
- [Pika documentation](https://pika.github.io/pika/latest/): BlockingConnection, confirms, exceptions và thread ownership; mỗi role giữ connection trong thread xử lý của nó.
- [SQLAlchemy 2.0 transactions](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html) và [PostgreSQL dialect](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html): transaction/session, row locks và partial index. Migration đã tạo là snapshot explicit, không gọi metadata.create_all thay migration.
- [FastAPI security](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/): hashing và token có hạn; quyền sở hữu/admin bổ sung theo nghiệp vụ đồ án.
- [Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/): health dependency và tác vụ completed; app vẫn phải reconnect khi dependency lỗi sau startup.
- [PostgreSQL official image](https://hub.docker.com/_/postgres), [RabbitMQ official image](https://hub.docker.com/_/rabbitmq): tag/variant và upstream source. Digest thực cùng inspect output phải lưu trong evidence.

Nguồn trong brief cần kiểm tra lại khi đến Mốc 3–4, chưa xem là cấu hình đã chạy: [KEDA RabbitMQ 2.21](https://keda.sh/docs/2.21/scalers/rabbitmq-queue/), [Kubernetes HPA](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/), [Promtail lifecycle](https://grafana.com/docs/loki/latest/send-data/promtail/), [libvirt provider](https://registry.terraform.io/providers/dmacvicar/libvirt/latest/docs/resources/domain). Không ghim KEDA/libvirt chỉ từ liên kết khi chưa chọn nền tảng và kiểm tra tương thích thực.

## Toolchain Mốc3 – ghim14/11/2026

| Thành phần | Phiên bản | Phạm vi |
|---|---|---|
| Terraform / libvirt | 1.17.2 /0.9.9 | BinarySHA256, providerlockWindows/Linux; fmt/init/validate đã chạy, chưa VM |
| Pythoncontrol / Ansible-core | 3.13.18 /2.22.0 | WSLvenv, fulltransitivelock; syntax/Vaultlocal theo evidence, không máy trắng |
| Collections | community.general14.0.1, community.docker5.4.0, ansible.posix2.2.2, community.library_inventory_filtering_v1 1.1.5 | GalaxyartifactSHA256, offlineinstall; inventoryVM chưa chạy |
| k3s / Kubernetes | v1.36.6+k3s1 /1.36.6 | Cố ý không lấy stablechannel1.37 để phù hợp KEDA2.21tested1.34–1.36; chưa cài node |
| KEDA / cert-manager | 2.21.0 /1.21.3 | Releaseassets/SHA256/CRDschema thật, chưaoperator |
| Nodeexporter | 1.12.1 | Rolepin/checksumupstream, chưa tải/chạy trênVM |
| kubectl local / Kustomize | 1.36.1 /5.8.1 | Đã render; agentDockerfile chuẩn bị kubectl1.36.6 có checksum, chưabuild |
| Docker VM packages | infra/versions.json | DockerCE29.9.3/Compose5.7.1 và packages đã chọn từ officialUbuntuAPTindex, chưa càiVM |

Sources: [libvirt0.9.9 schema](https://github.com/dmacvicar/terraform-provider-libvirt/tree/v0.9.9/docs), [HashiCorpreleases](https://releases.hashicorp.com/terraform/1.17.2/), [K3srequirements](https://docs.k3s.io/installation/requirements), [Ansibleinstall](https://docs.ansible.com/projects/ansible/latest/installation_guide/intro_installation.html), [KEDAcompatibility](https://keda.sh/docs/2.21/deploy/), [KubernetesOpenAPI1.36.6](https://raw.githubusercontent.com/kubernetes/kubernetes/v1.36.6/api/openapi-spec/swagger.json). ManifestURL/SHA đầy đủ ở infra/versions.json. Pin/version/schema không thay runtime hoặc scan image.

## Mốc 4 – nguồn kiểm tra14/11/2026

observability/versions.json lưu SHA256 archive và OCI manifest digest đã lấy từ registry: Prometheus3.16.0, Alertmanager0.35.0, Grafana13.3.1, kube-state-metrics2.20.0 (client-go1.36), postgres_exporter0.20.1, Elasticsearch/Kibana9.5.6 và Fluentd1.20.1-debian-elasticsearch9-1.0. Release Fluentd có fluent-plugin-elasticsearch6.0.0/client9.5.0 và prometheus2.2.2 trong Gemfile.lock. Catalog Elastic có9.5.7 nhưng registry trả404, nên chỉ chọn9.5.6 đã xác minh tồn tại; không suy image đã phát hành từ catalog. Kubernetes registry redirect lỗi DNS trên máy, manifest KSM được đối chiếu qua mirror chính thức us-central1-docker.pkg.dev/k8s-artifacts-prod/images.

Promtool/amtool native thực sự đã chạy parser/rule fixture. Cập nhật15/11: 8 image này đã remote scan0CRITICAL, chưa chạy; digest không thay CVE gate và phải scan mới theo freshness khi bootstrap. Nginx mới có JSON access log cần build/nginx -t trên image ghim trước nghiệm thu; Fluentd parser/runtime cũng chưa chạy.

Nguồn: [Prometheus3.16.0](https://github.com/prometheus/prometheus/releases/tag/v3.16.0), [Alertmanager0.35.0](https://github.com/prometheus/alertmanager/releases/tag/v0.35.0), [Grafana provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/), [KSM2.20](https://github.com/kubernetes/kube-state-metrics/tree/v2.20.0), [RabbitMQ4.2 collector](https://github.com/rabbitmq/rabbitmq-server/blob/v4.2.9/deps/rabbitmq_prometheus/src/collectors/prometheus_rabbitmq_core_metrics_collector.erl), [Fluentd Gemfile.lock](https://github.com/fluent/fluentd-kubernetes-daemonset/blob/v1.20.1-1.0/docker-image/v1.20/debian-elasticsearch9/Gemfile.lock), [Elastic Docker](https://www.elastic.co/docs/deploy-manage/deploy/self-managed/install-elasticsearch-docker-configure). Giá cloud có nguồn/ngày riêng trong cloud-cost-estimate.md; không có tài nguyên cloud đã mua.
