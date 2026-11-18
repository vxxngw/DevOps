# Nguồn và giấy phép

Mã ứng dụng được viết cho đồ án trong workspace; không lấy nguyên ứng dụng mẫu khác. AI hỗ trợ sinh mã/cấu hình; nhóm vẫn cần review và giải thích theo PDF trang 1. Hướng dẫn kỹ thuật tham chiếu trong docs/guides/versions.md; không xem tham khảo pattern outbox là bằng chứng runtime.

Logo An Uyên Hospital do chủ dự án cung cấp, giữ nguyên trong frontend/public/brand/an-uyen-logo.jpg. Nguồn/checksum và quy tắc nhận diện ở docs/guides/branding.md; đây là tài sản dự án, không phải logo do AI tạo.

| Thành phần | Nguồn gốc | License upstream cần giữ khi phân phối |
|---|---|---|
| FastAPI, SQLAlchemy, Alembic, Pydantic, PyJWT, pwdlib, React, Vite | Package/official repository từ lockfiles | MIT (đối chiếu LICENSE đúng artifact/version) |
| Uvicorn, psycopg, Pika, Prometheus Python client | Package/official repository | BSD-3-Clause / LGPL-3.0 / BSD-3-Clause / Apache-2.0 tương ứng; psycopg binary có phụ thuộc riêng |
| PostgreSQL | Official Docker image + postgres.org | PostgreSQL License và giấy phép package OS |
| RabbitMQ | Official Docker image + rabbitmq.com | MPL-2.0 và phụ thuộc Erlang/OS riêng |
| Mailpit | github.com/axllent/mailpit | MIT |
| Nginx, Node, Python | Official Docker images | BSD-2-Clause / MIT+phụ thuộc / PSF+phụ thuộc |
| Playwright | github.com/microsoft/playwright | Apache-2.0 |
| Jenkins và plugins trực tiếp | jenkins.io, ci/controller/plugins-lock.json | Jenkins MIT; kiểm tra LICENSE từng plugin/artifact khi build, không xóa NOTICE |
| Gitleaks / Trivy / Docker CLI | github.com/gitleaks/gitleaks, aquasecurity/trivy, docker/cli | MIT / Apache-2.0 / Apache-2.0; binary release kiểm SHA256, chưa là SBOM đầy đủ |
| ESLint / typescript-eslint / React Hooks lint plugin | npm lockfile và repository upstream | MIT; giữ license bundled |
| Terraform 1.17.2 | [LICENSE đúng tag](https://github.com/hashicorp/terraform/blob/v1.17.2/LICENSE) | Business Source License 1.1; giữ LICENSE của binary/artifact khi phân phối |
| Ansible-core 2.22.0 | [COPYING đúng tag](https://github.com/ansible/ansible/blob/v2.22.0/COPYING) | GNU GPL v3; collections có license riêng, kiểm artifact tương ứng |
| libvirt provider, K3s/Kubernetes, KEDA, cert-manager, uv và Node Exporter | Nguồn/tag và checksum trong infra/versions.json; provider trong .terraform.lock.hcl | Giữ LICENSE/NOTICE upstream; bảng này chưa kiểm kê toàn bộ phụ thuộc hoặc thay thế license audit |
| Inter (UI font), @fontsource/inter 5.3.0 | The Inter Project Authors; package npm có integrity trong lockfile | SIL Open Font License 1.1; tự phục vụ các weight400/500/600 gồm tiếng Việt; bản license trong frontend/public/brand/Inter-OFL.txt |

Danh sách trên là hướng dẫn kiểm kê, chưa phải SBOM/license audit đầy đủ. Không xóa LICENSE/NOTICE bundled của phụ thuộc/image. Lockfile ghi phiên bản, npm lock ghi integrity; build/scan/SBOM và xác minh license artifact thực phải bổ sung trước phát hành. Chưa chọn license cho mã riêng của nhóm thay người sở hữu.

Mốc4 bổ sung Prometheus/Alertmanager, Grafana, kube-state-metrics, postgres_exporter, Elasticsearch/Kibana và Fluentd/plugins. Nguồn/tag/digest ở observability/versions.json và docs/guides/versions.md; giữ LICENSE/NOTICE từ đúng artifact, gồm phụ thuộc/plugin và điều khoản phân phối Elastic/Grafana. Chưa có SBOM/license audit đầy đủ cho8image này và chưa coi image ghim digest là đã quét CVE.
