> **2026-11-19: Terraform-only migration.** Ansible source/control dependencies retired at operator request; historical evidence below is not current execution guidance. See runbooks/terraform-only.md. VM/key/Vault/state preserved. Jenkins/K3s/backup replacement automation remains incomplete; mandatory Ansible requirement is not satisfied.

# Đối chiếu Bài 3, 7, 8, 12

Ngày rà soát: 18/11/2026. Đây là đối chiếu mã nguồn và bằng chứng hiện có,
không phải biên bản nghiệm thu VM đã chạy.

## Phương án nộp bài

Phạm vi thực hiện: Linux/Bash, host, backup/timer; Ansible, Terraform và chi phí.
Không mở rộng sang monitoring/alert/log tập trung Bài 10 hoặc demo HPA/KEDA.

Chọn lab cục bộ dùng Terraform provider libvirt và module VM tự viết. Theo yêu
cầu người dùng cung cấp, phương án local được nộp kèm bảng ước tính chi phí
chuyển lên một nhà cung cấp cloud; không bắt buộc thuê cloud chỉ để có hóa đơn.
Không gọi namespace `production` trên máy local là production đã triển khai cloud.

Bảng dự toán đã có tại `D:\nam4\project_devops\DevOps\docs\cloud-cost-estimate.md`,
kèm giả định, nguồn giá, cấu hình, khoản ngoài tổng và bằng chứng tra giá.
Đó là dự toán, không phải tài nguyên cloud đã được tạo.

## Ma trận yêu cầu

### Chuẩn đối chiếu theo đề đầy đủ người dùng cung cấp

- **Bài 3 bắt buộc:** Bash backup CSDL theo cron/systemd timer, kiểm tra sức
  khỏe host; user riêng, SSH key, tắt root login, UFW. **Nâng cao:** restore
  đã diễn tập thành công và logrotate cho log ứng dụng. Restore không phải
  điều kiện đạt cột Bắt buộc Bài 3; runbook khôi phục vẫn là sản phẩm nộp chung.
- **Bài 7 bắt buộc:** chia role, cài Docker/k3s/Jenkins agent/node exporter
  từ máy trắng, inventory tách môi trường, lần hai không đổi, Vault mã hóa.
  **Nâng cao:** Molecule và gọi playbook từ Jenkins. Syntax-check không thay
  bằng chứng cài đặt hoặc idempotency.
- **Bài 8 bắt buộc:** Terraform tạo VM/mạng/firewall (DNS nếu có), variables,
  outputs, module tự viết, state không commit; local cho phép libvirt.
  **Nâng cao:** remote state có khóa, plan trên PR, staging/production chung
  module khác biến. Không bắt buộc hai fleet 3 VM độc lập để đạt mức cơ bản.
- **Bài 12 bắt buộc:** production cloud hoặc local kèm dự toán chuyển lên một
  nhà cung cấp cloud. **Nâng cao:** managed services, tự tắt staging ngoài giờ.
- Demo chung bước 1 bắt buộc chạy Terraform apply rồi Ansible trên máy trắng,
  cụm K8s lên được; có thể dùng video quay trước nếu bước chạy lâu. Video phải
  là một lần chạy thật, không thay bằng cấu hình hoặc log tổng hợp.

### Ranh giới trách nhiệm và bàn giao

Người phụ trách phần này bàn giao host/SSH/UFW, Terraform, Ansible, backup và
timer, tài liệu chi phí và phần demo dựng hạ tầng. Phối hợp thành viên Jenkins
để có credential/agent online; thành viên ứng dụng/K8s để có PostgreSQL và
namespace cho backup; thành viên monitoring để scrape node exporter. Không
đưa private key, kubeconfig, token hoặc mật khẩu vào tài liệu bàn giao công khai.

Nhóm vẫn phải đạt cả 12 bài. Bài 10 đã bị gỡ theo yêu cầu trước đó nên cần thành
viên phụ trách khôi phục hoặc triển khai lại trước nghiệm thu nhóm; không được
coi là đã đạt. Demo HPA/dashboard/alert/log và KEDA của đề tài đặt lịch khám
vẫn thuộc phạm vi chung, không phải việc tự động bổ sung trong phần cá nhân này.

| Yêu cầu                                      | Mã/cấu hình hiện có                                                                               | Trạng thái và bằng chứng còn cần                                                                                                                                                         |
| -------------------------------------------- | ------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Bash backup CSDL                             | `scripts/backup.sh`, `scripts/restore.sh`                                                         | Có script dùng PostgreSQL dump custom format, checksum, retention; chưa chứng minh backup/restore thật trên VM                                                                           |
| Chạy backup theo lịch                        | Role `backup`, systemd template service và timer 02:15 với random delay 300 giây, Persistent=true | Chưa có kết quả list-timers, service journal và artifact từ lịch chạy thật                                                                                                               |
| Kiểm tra sức khỏe host                       | `scripts/host-health.sh`, role `host_health`                                                      | Có service/timer mỗi 5 phút trên mọi VM; script đã chạy thật trên WSL, chưa có kết quả trên cả 3 VM                                                                                      |
| User riêng, SSH key, cấm root/password login | Cloud-init module VM và role `common`                                                             | Có cấu hình `clinicops`, public key, sshd; cần xác minh SSH key thật và cấu hình sshd hiệu lực                                                                                           |
| UFW                                          | Terraform cloud-init và role `common`                                                             | First boot cài UFW, chặn inbound và chỉ mở SSH theo operator CIDR; Ansible chờ cloud-init rồi bổ sung rule; chưa có `ufw status` trên VM                                                 |
| Playbook chia role                           | `infra/ansible/site.yml`, các role common/docker/k3s/jenkins/node_exporter/backup                 | Có cấu trúc; chưa chạy từ máy trắng                                                                                                                                                      |
| Docker, k3s, Jenkins agent, node exporter    | Các role tương ứng; Jenkins agent chạy qua Compose                                                | Có cấu hình; cần service/process/node Ready/agent online thật                                                                                                                            |
| Inventory tách môi trường                    | `inventories/lab`, `inventories/staging`, `inventories/production`                                | Có inventory mẫu với host/subnet, group_vars, Vault riêng; hai fleet độc lập chưa provision. Lab vẫn là một fleet dùng hai namespace                                                     |
| Idempotency                                  | Các task declarative, marker bootstrap, `scripts/check-ansible-recap.py`                          | Có validator và unit test cho recap; chưa chứng minh hội tụ VM thật; cần chạy hai lần cùng revision/vars                                                                                 |
| Ansible Vault                                | `tasks/load-vault.yml`, Vault example                                                             | Có chặn plaintext; cần operator tạo Vault mã hóa thật ngoài Git, dùng password riêng và không in secrets                                                                                 |
| Terraform tạo VM/mạng                        | `infra/terraform/main.tf`, provider libvirt                                                       | Có cấu hình; chưa có apply/output/VM thật                                                                                                                                                |
| Module tự viết, variables, outputs           | `infra/terraform/modules/vm`, variables.tf, outputs.tf                                            | Terraform đúng bản ghim đã fmt/init/validate thành công; chưa plan/apply VM thật                                                                                                         |
| Firewall/security group trong hạ tầng        | Terraform truyền policy UFW qua cloud-init; Ansible bổ sung rule dịch vụ                          | Có firewall guest trong module; không phải tài nguyên security group cloud/provider firewall riêng. Nếu rubric yêu cầu resource firewall độc lập thì cần xác nhận phạm vi với người chấm |
| DNS nếu có                                   | `libvirt_network.lab` DNS local                                                                   | Có cấu hình tên miền lab; chưa kiểm resolve thật                                                                                                                                         |
| Không commit state                           | `.gitignore` loại `.terraform`, `*.tfstate*`, `*.tfplan`, `*.tfvars`                              | Phải kiểm cả tracked files và staged diff trước push; ignore không bỏ file đã từng track                                                                                                 |
| Local kèm chi phí cloud                      | `docs/cloud-cost-estimate.md` và receipt nguồn giá                                                | Có bảng; cập nhật khi thay cấu hình hoặc trước nộp nếu cần giá mới                                                                                                                       |

Các đường dẫn tương đối trong bảng tính từ `D:\nam4\project_devops\DevOps`.

## Việc tiếp theo theo thứ tự

1. Chuẩn bị host đúng ngân sách trong `infra/lab-budget.json`; không apply trên
   máy hiện tại khi preflight chưa đạt. Không xóa active Docker VHDX hoặc backup.
2. Chọn profile lab hoặc fleet độc lập theo `docs/runbooks/infra-acceptance.md`.
   Inventory mẫu không chứng minh môi trường đã chạy; không chạy đồng thời hai
   fleet khi chưa có ngân sách. Workspace không phải ranh giới phân quyền.
3. Xác minh firewall first boot từ cloud-init và rule Ansible trên guest thật.
   Không gọi mạng NAT/UFW là security group cloud.
4. Chạy preflight, Terraform fmt/init/validate/plan, review trước apply; thu output
   đã che thông tin nhạy cảm và kiểm đúng 3 VM.
5. Tạo Vault mã hóa thật và chạy Ansible hai lần, cùng commit/vars. Không dùng
   check mode hay `changed_when: false` để giả bằng chứng idempotency.
6. Kiểm SSH, UFW, dịch vụ, timers và backup thật để chốt bắt buộc. Nếu làm nâng
   cao Bài 3, restore sang DB thử và kiểm dữ liệu trước/sau; chỉ dump/checksum
   thành công chưa chứng minh khôi phục được. Logrotate chưa có bằng chứng đạt.
7. Đóng gói report và receipt đã che secret; không commit state, tfvars, kubeconfig,
   token, Vault password hoặc dump chứa dữ liệu nhạy cảm.

## Bằng chứng tối thiểu để chốt

- Plan/apply đã che nhạy cảm; 3 VM/IP thật và kết nối SSH bằng key.
- `sshd -T` hiệu lực (kể cả Match rules nếu có), UFW status; không thử root sai
  cách gây mất kết nối operator.
- Service Docker/k3s/exporter, 2 node Ready, Jenkins build agent online.
- Hai Ansible recap; lần hai không có thay đổi/failed/unreachable.
- Timer enabled/active, lịch next/last, journal thành công, dump/checksum ngoài pod.
- Bảng chi phí và giải thích các giả định; không tuyên bố cloud deployment.

Nâng cao Bài 3: bổ sung restore thử thành công, kiểm dữ liệu ứng dụng và
logrotate cho log ứng dụng. Backup ngoài VM là biện pháp bảo vệ được khuyến
nghị, không ghi thành tiêu chí bắt buộc nguyên văn của đề.

Bài 10 monitoring/EFK/Telegram đã được gỡ theo yêu cầu ngày 18/11/2026;
bằng chứng lịch sử của phần đó không thay thế những bằng chứng hạ tầng trên.

## Kết quả kiểm tra ngày 18/11/2026

- Unit suite `tests` và `ci/tests`: **82 passed, 11 skipped**, 1 cảnh báo
  deprecation TestClient/httpx. Test bị skip không được tính là runtime đã đạt.
- Ruff check và format check: đạt.
- Bash syntax tất cả script shell: đạt.
- Ansible core 2.22.0/Python 3.13.18 trong WSL: syntax-check playbook đạt với
  inventory mẫu lab, staging và production.
- Vault local bằng giá trị tổng hợp: encrypted input exit 0, plaintext input
  exit 2; không dùng secret thật, không phải bằng chứng credential trên VM.
- Terraform bản ghim: fmt/init (backend=false)/validate đạt; không plan/apply.
- Host-health chạy thật trên WSL trả healthy; không thay sức khỏe VM.
- Preflight 15:17 UTC: **BLOCKED**. RAM khả dụng 2710 MiB so với 18432 MiB VM
  cộng 1024 MiB reserve; ổ repo còn 21825085440 byte so với yêu cầu 160 GiB;
  chưa có libvirt socket/virsh/QEMU. Không cấp quyền hoặc tạo VM để vượt chặn.

Log cục bộ bị ignore: `.infra-local/final-unit.log`,
`.infra-local/final-infra.log`, `.infra-local/preflight.json`,
`.infra-local/vault-test/result.json`; Terraform log ở `ci-out/infra`.
Chưa có bằng chứng timer/backup/restore và recap lần hai trên VM thật.

## Cập nhật VirtualBox ngày 19/11/2026 — chỉ một VM Jenkins

### Docker runtime continuation

- Docker role was applied separately without bypassing the CI play's Vault gate.
  DHCP changed again to `192.168.1.39`; SSH was verified against the previously
  trusted host key before updating the private inventory. The operator stays
  `192.168.1.169/32`. Earlier `.27` addresses below are historical evidence.
- The initial controller connection was interrupted during apt installation.
  Package installation was allowed to finish; no second apt job was started.
  The disconnected control processes were terminated only after apt/dpkg exited.
- A reconciled run at `.39` completed with exit 0:
  `ok=7 changed=0 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0`.
  Docker server is `29.9.3`; Compose is `v5.7.1`; Docker is enabled and active.
- Private evidence: `.infra-local/jenkins-docker-reconciled.log` and `.exit`.
  Jenkins controller/agent are not installed yet. Operator needs to create real
  read-only SCM and GHCR write tokens and enter them into encrypted Vault privately.

- Terraform đã tạo VM `anuyen-jenkins` trên laptop Windows, dữ liệu ở ổ E.
  Lần create đầu lỗi đọc guest properties; sau cloud-init hoàn tất, đã kiểm VM,
  refresh-only state và gỡ taint có căn cứ. Plan sau đối soát không đổi tài nguyên.
- Guest Ubuntu đã SSH bằng key, tắt root/password login, UFW hoạt động. DHCP đã
  đổi IP từ `192.168.1.33` sang `192.168.1.27`; inventory private cập nhật và SSH
  vẫn kiểm đúng host key. Chưa cấu hình reservation router hoặc static IP.
- Ansible `--limit anuyen-jenkins --tags os` chạy qua WSL. Cặp chạy cùng vars ở IP
  mới: lần một `ok=27 changed=1`, lần hai `ok=27 changed=0`; cả hai exit 0,
  `unreachable=failed=rescued=ignored=0`. Recap validator chấp nhận inventory 1 host.
- Node exporter HTTP 200 trong guest; host-health timer hoạt động, journal có
  lần chạy theo lịch `healthy: true`, service result success/exit 0.
- Đây không phải bằng chứng CI/Jenkins hoàn tất hoặc fleet 3 VM đạt. Chưa có
  deployment Vault thật/revision remote được chốt, chưa cài Jenkins + agent,
  chưa chạy k3s và scheduled backup trên hai laptop còn lại.
- Log riêng nằm dưới `.infra-local/jenkins-os-current-*`; không commit private
  inventory, SSH key, state hoặc Vault password. Chi tiết xem
  `infra/terraform-virtualbox/README.md`.
