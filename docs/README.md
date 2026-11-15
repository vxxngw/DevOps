# Tài liệu An Uyên Hospital

Bắt đầu với [bố cục source](guides/source-structure.md), [chạy local](guides/local-setup.md) và [ma trận yêu cầu](compliance-matrix.md). Trạng thái có ngày và phạm vi kiểm chứng riêng; cấu hình chưa chạy không được tính là runtime đã đạt.

| Mục đích | Tài liệu |
|---|---|
| Chia việc cho Vuong, Hoang, Long | [Onboarding](guides/team-onboarding.md), [quy trình nhóm](guides/team-workflow.md), [đóng góp](../CONTRIBUTING.md) |
| Kiến trúc và quyết định | [Kiến trúc](guides/architecture.md), [ADR](guides/decisions.md), [phiên bản](guides/versions.md), [nguồn OSS](../THIRD_PARTY.md) |
| Ứng dụng và giao diện | [Local setup](guides/local-setup.md), [Soft Minimal](guides/soft-minimal.md), [branding](guides/branding.md), [notification runbook](runbooks/notifications.md) |
| CI/CD và bảo mật | [CI/CD](guides/ci-cd.md), [security](guides/security.md), [webhook](runbooks/github-webhook.md), [deploy](runbooks/deploy.md), [rollback](runbooks/rollback.md) |
| Hạ tầng và vận hành | [Lab](runbooks/infra-lab.md), [tài nguyên](guides/resource-budget.md), [restore DB](runbooks/restore.md), [observability](runbooks/observability.md), [cảnh báo](runbooks/alerts.md) |
| Các mốc | [Mốc 1](guides/milestone-1.md), [Mốc 2](guides/milestone-2.md), [Mốc 3](guides/milestone-3.md), [Mốc 4](guides/milestone-4.md) |
| Demo và sản phẩm nộp | [8 bước demo](guides/demo-script.md), [checklist nộp](guides/submission.md), [báo cáo](guides/project-report.md), [vấn đáp](guides/viva-preparation.md), [postmortem](guides/postmortem.md), [chi phí](guides/cloud-cost-estimate.md) |
| Bằng chứng | [Refactor source](evidence/source-restructure-20261115T104329Z/README.md), [mục lục evidence](evidence/README.md), [CI baseline](evidence/ci-runtime-latest.json), [chuẩn bị M3](evidence/m3-latest.json), [chuẩn bị M4](evidence/m4-latest.json) |

`guides/` chứa hướng dẫn và báo cáo, `runbooks/` chứa quy trình vận hành, `evidence/` giữ snapshot có thời điểm. Đường dẫn cũ `docs/<tên>.md` đã chuyển thành `docs/guides/<tên>.md`, ngoại trừ ma trận yêu cầu vẫn ở vị trí được đề bài/brief yêu cầu. Các đường dẫn được ghi trong raw report cũ là thông tin provenance tại thời điểm thu thập.
