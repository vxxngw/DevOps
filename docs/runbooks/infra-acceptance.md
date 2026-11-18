# Nghiệm thu Bài 3, 7, 8, 12

Cập nhật 18/11/2026. Repo Windows: `D:\nam4\project_devops\DevOps`;
trong WSL: `/mnt/d/nam4/project_devops/DevOps`. Các lệnh Linux bên dưới bắt
đầu từ thư mục repo này. Không phải bằng chứng đã apply hoặc hội tụ VM.

Phạm vi bắt buộc cá nhân: Linux/Bash/host/backup-timer, Ansible, Terraform và
chi phí (Bài 3/7/8/12). Restore diễn tập và logrotate là nâng cao Bài 3;
runbook restore vẫn là tài liệu nộp chung. Không đòi Molecule, remote state hay
hai fleet độc lập để gọi mức bắt buộc đã đạt. Demo Terraform apply → Ansible
trên máy trắng vẫn bắt buộc cho nhóm; chỉ cấu hình/syntax-check là chưa đủ.

## 1. Chọn đúng mô hình

| Profile | Inventory | Prefix / subnet dự kiến | Backup namespace |
|---|---|---|---|
| lab | `infra/ansible/inventories/lab` | anuyen / 192.168.150.0/24 | staging, production |
| staging | `infra/ansible/inventories/staging` | anuyen-staging / 192.168.151.0/24 | staging |
| production | `infra/ansible/inventories/production` | anuyen-production / 192.168.152.0/24 | production |

Lab là 3 VM dùng chung cluster cho 2 namespace. Staging/production là các
inventory mẫu cho **fleet độc lập**, không tự tạo máy. Mỗi fleet dùng ngân sách
18 GiB RAM/8 vCPU/128 GiB disk; chạy cả hai cần 36 GiB RAM VM cộng host reserve
và storage thực tương ứng. Preflight hiện chỉ kiểm ngân sách một fleet, không
phải bộ lập lịch nhiều fleet. Không tự chạy cả hai trên host hiện tại.

Không dùng chung state/prefix/subnet/storage/MAC giữa fleet trên cùng hypervisor.
Terraform workspace tách state, không phải ranh giới phân quyền bảo mật.
Nếu state cũ nằm workspace `default`, sao lưu state riêng tư và kiểm mapping
trước khi di chuyển; **không tạo workspace mới rồi apply cùng tên tài nguyên cũ**.

## 2. Kiểm tra control node không tạo VM

```powershell
Set-Location 'D:\nam4\project_devops\DevOps'
.\.venv\Scripts\python.exe -m pip install -r infra/requirements-static.txt
.\.venv\Scripts\python.exe scripts/install-infra-tools.py
wsl -d Ubuntu -e bash /mnt/d/nam4/project_devops/DevOps/scripts/setup-infra-control.sh
wsl -d Ubuntu -e bash /mnt/d/nam4/project_devops/DevOps/scripts/check-infra-control.sh
.\.venv\Scripts\python.exe -m pytest -q tests ci/tests
.\.venv\Scripts\python.exe -m ci.infrastructure
```

Installer chỉ cài tool/cache bị ignore. Nếu tải Python timeout, có thể đặt
`UV_HTTP_TIMEOUT=600 UV_NO_PROGRESS=1` khi chạy setup trong Linux rồi thử lại.
Preflight `BLOCKED` là kết quả chặn triển khai, không phải thất bại cần bỏ qua.
Dung lượng ext4 ảo WSL không thay thế dung lượng trống thật của ổ Windows.

## 3. Terraform và firewall lúc first boot

Chuẩn bị Linux/KVM/libvirt theo runbook infra-lab; image Ubuntu 24.04 và SHA256
thật, SSH public key thật, operator CIDR có thể kết nối tới VM. Không đưa private
key/token vào tfvars/state. Terraform truyền UFW default-deny inbound,
allow-outbound và chỉ cho SSH từ operator CIDR qua cloud-init; Ansible chờ
cloud-init xong rồi bổ sung rule dịch vụ. Đây là firewall **trong guest**, không
phải security group cloud hay bộ firewall độc lập của libvirt provider.

Ví dụ profile lab, CHỈ sau khi preflight READY và đã duyệt ngân sách:

```bash
cd /mnt/d/nam4/project_devops/DevOps
umask 077
cp infra/terraform/lab.example.tfvars infra/terraform/lab.tfvars
# Sửa lab.tfvars: image/hash/key/operator CIDRs và storage Linux thực trước lệnh sau.
TF="$PWD/.infra-local/bin/linux/terraform"
"$TF" -chdir=infra/terraform init -input=false -lockfile=readonly
"$TF" -chdir=infra/terraform workspace list
# Chỉ tạo khi chưa tồn tại và không có tài nguyên trùng trong state khác:
"$TF" -chdir=infra/terraform workspace new lab
"$TF" -chdir=infra/terraform workspace select lab
python3 scripts/lab.py plan --environment lab --var-file infra/terraform/lab.tfvars
# Review đúng VM/pool/network/cloud-init, không có destroy ngoài dự kiến.
python3 scripts/lab.py apply --environment lab --var-file infra/terraform/lab.tfvars
"$TF" -chdir=infra/terraform output -raw ansible_inventory > infra/ansible/inventories/lab/hosts.yml
```

Apply yêu cầu nhập tên môi trường sau khi review plan. File inventory output nằm
cạnh group_vars đúng môi trường. Với fleet độc lập, tạo tfvars bị ignore riêng,
đổi prefix/subnet/storage và từng MAC trong map `nodes`; giữ đúng ba key
jenkins/server/agent. Dùng workspace và output inventory cùng môi trường.
Không ghép các inventory này trong một lệnh Ansible.

## 4. Vault và chạy playbook hai lần

Đọc schema `vault.example.yml`, nhưng tạo trực tiếp file mã hóa bằng
`ansible-vault create`, không lưu plaintext secrets vào repo. Staging/production
phải có giá trị và mật khẩu Vault riêng. Để SSH key trong filesystem Linux, mode
0600; xác minh fingerprint host qua console tin cậy trước khi chấp nhận known_hosts.

```bash
export ANSIBLE_CONFIG="$PWD/infra/ansible/ansible.cfg"
export ANSIBLE_HOME="$PWD/.infra-local/ansible-home"
export ANSIBLE_COLLECTIONS_PATH="$PWD/.infra-local/collections"
export ANSIBLE_NOCOLOR=1
ENVIRONMENT=lab
INVENTORY="infra/ansible/inventories/$ENVIRONMENT/hosts.yml"
ANSIBLE="$PWD/.infra-local/ansible-venv/bin/ansible-playbook"
VAULT="$PWD/.infra-local/ansible-venv/bin/ansible-vault"
"$VAULT" create "infra/ansible/inventories/$ENVIRONMENT/vault.yml"
read -r -p 'Exact pushed repository commit (40 hex): ' REVISION
[[ "$REVISION" =~ ^[a-f0-9]{40}$ ]] || exit 2
mkdir -p .infra-local/acceptance
set -o pipefail
"$ANSIBLE" -i "$INVENTORY" infra/ansible/site.yml --ask-vault-pass \
  -e "clinic_repo_revision=$REVISION" 2>&1 | tee .infra-local/acceptance/ansible-first.log
# Dừng tại đây nếu exit != 0; không gộp log của các lần chạy.
"$ANSIBLE" -i "$INVENTORY" infra/ansible/site.yml --ask-vault-pass \
  -e "clinic_repo_revision=$REVISION" 2>&1 | tee .infra-local/acceptance/ansible-second.log
python3 scripts/check-ansible-recap.py .infra-local/acceptance/ansible-second.log \
  --hosts anuyen-jenkins anuyen-server anuyen-agent
```

Mỗi lệnh phải exit 0 trước khi tiếp tục. Không truyền `--check`, `--limit` hay
`--tags` để giả bằng chứng full-fleet. Đổi danh sách `--hosts` theo inventory
thật nếu không dùng prefix anuyen. Validator chỉ đọc recap: không chứng minh
log là thật, cùng commit/vars hay đúng lệnh; lưu metadata/exit code và hash nguồn.
Không dùng `changed_when: false` cho task thay đổi hệ thống để đạt changed=0.

## 5. Kiểm tra trên VM thật

Trên từng VM, qua SSH operator key:

```bash
sudo cloud-init status --wait
sudo sshd -T | grep -E 'permitrootlogin|passwordauthentication|kbdinteractiveauthentication|pubkeyauthentication'
sudo ufw status verbose
sudo systemctl is-active node-exporter clinic-host-health.timer
sudo systemctl start clinic-host-health.service
sudo journalctl -u clinic-host-health.service -n 10 --no-pager
sudo systemctl list-timers 'clinic-*' --no-pager
```

Với sshd Match rules, kiểm thêm `sshd -T -C` theo user/IP nguồn thực. Giữ session
operator đang mở khi thử SSH mới; không tắt root/password trước khi key login
thật hoạt động. SSH drop-in cần được kiểm thứ tự và effective config, không chỉ
đọc file. Timer health chạy sau boot 2 phút, lặp 5 phút; exit khác 0 khi không khỏe.

Trên server: `sudo k3s kubectl get nodes -o wide`, cả 2 node Ready. Trên Jenkins:
kiểm Docker/Compose controller + engine + agent và xác nhận agent online từ UI;
process tồn tại chưa đủ. Đọc runbook restore để chạy backup và khôi phục DB thử.
Backup timer 02:15 theo timezone VM, delay tối đa 300 giây, chạy bù khi bật lại.

## 6. Bằng chứng và trạng thái

Chỉ nghiệm thu sau có: Terraform plan/apply và 3 VM thật; SSH/UFW hiệu lực;
service/node/agent; hai recap; journal timer; dump/checksum và restore DB mới
kiểm schema/dữ liệu nếu nghiệm thu nâng cao Bài 3; backup ngoài fleet được
khuyến nghị để tránh mất dữ liệu. Với mức bắt buộc chỉ cần backup theo lịch
thật và các kiểm tra host/Ansible/Terraform nêu trên, không lấy restore nâng
cao làm điều kiện bắt buộc. Chưa có bằng chứng bắt buộc thì ghi
**cấu hình hoàn tất, runtime chưa xác minh**, không ghi tất cả bài đã đạt.

State, tfvars, tfplan, inventory thật, Vault và credential không commit. Trước
push chạy `git diff --check`, kiểm tracked/staged files và secret scanner.
Không xóa `D:\DockerDesktopData\DockerDesktopWSL` hoặc
`D:\nam4\docker-maintenance-backup`. Không destroy trước khi xuất backup ra ngoài VM.