# Bài 3 – Linux trên một VM cloud

Playbook [cloud-lab.yml](../../infra/ansible/cloud-lab.yml) dựng một VM Ubuntu cloud làm máy chủ Bài 3:

| Yêu cầu Bài 3 | Thực hiện bằng |
|---|---|
| Script Bash sao lưu CSDL theo lịch | `scripts/infra/backup.sh dev` (pg_dump + SHA-256 + xoá bản cũ hơn 7 ngày) chạy bởi `clinic-backup@dev.timer` (hằng giờ trên VM lab) |
| Kiểm tra sức khỏe máy chủ | `scripts/infra/host-health.sh` (RAM, đĩa `/`, load) chạy bởi `clinic-host-health.timer` mỗi 15 phút |
| User riêng | `clinicops` (cloud-init tạo, role `common` đảm bảo); dịch vụ health chạy `DynamicUser` |
| SSH bằng key | `PasswordAuthentication no`, `KbdInteractiveAuthentication no`, `PubkeyAuthentication yes` |
| Tắt đăng nhập root | `PermitRootLogin no` |
| Bật UFW | Mặc định chặn vào; chỉ mở 22 từ IP người vận hành, 9100 từ mạng nội bộ |

PostgreSQL chạy bằng Docker Compose (`compose.yaml`, service `postgres`) với dữ liệu synthetic (migrate + seed). Backup staging/production trong k3s vẫn do `site.yml` cài trên `k3s_server`.

## 1. Tạo VM (người có tài khoản cloud làm)

1. Tạo SSH key riêng cho lab trên máy vận hành (PowerShell):
   ```bash
   ssh-keygen -t ed25519 -f $HOME/.ssh/anuyen_lab -C anuyen-lab
   ```
2. Tạo VM: **Ubuntu Server 24.04 LTS x86_64**, ≥ 2 vCPU / 4 GB RAM, ≥ 30 GB đĩa, có IP công khai.
3. Firewall của nhà cung cấp (Security group / NSG / Cloud firewall): chỉ mở **TCP 22 từ IP công khai của bạn**.
4. Dán vào ô *User data / Custom data* (thay dòng key bằng nội dung `anuyen_lab.pub`):
   ```yaml
   #cloud-config
   ssh_pwauth: false
   users:
     - name: clinicops
       groups: sudo
       shell: /bin/bash
       lock_passwd: true
       sudo: "ALL=(ALL) NOPASSWD:ALL"
       ssh_authorized_keys:
         - ssh-ed25519 AAAA... anuyen-lab
   ```
   Nếu nhà cung cấp bắt chọn key cho user mặc định (root/azureuser), chọn cùng key này.

## 2. Chạy playbook (từ WSL, venv Ansible trong `.infra-local`)

1. Chép `infra/ansible/inventories/cloud/hosts.example.yml` thành `hosts.yml` (git-ignored), điền IP VM, IP của bạn dạng `/32`, public key và commit 40-hex cần triển khai.
2. Kiểm vân tay host key với console nhà cung cấp rồi đăng nhập lần đầu: `ssh -i ~/.ssh/anuyen_lab clinicops@IP_VM`.
3. Chạy hai lần; lần hai phải `changed=0`:
   ```bash
   export ANSIBLE_CONFIG=$PWD/infra/ansible/ansible.cfg ANSIBLE_HOME=$PWD/.infra-local/ansible-home ANSIBLE_COLLECTIONS_PATH=$PWD/.infra-local/collections
   .infra-local/ansible-venv/bin/ansible-playbook -i infra/ansible/inventories/cloud/hosts.yml infra/ansible/cloud-lab.yml --private-key ~/.ssh/anuyen_lab
   ```

**Cẩn thận:** UFW chỉ cho SSH từ `clinic_operator_cidrs`. Nếu IP nhà bạn đổi, cập nhật `hosts.yml` qua console của nhà cung cấp trước khi bị khoá ngoài.

## 3. Kiểm chứng

Trên VM (`ssh -i ~/.ssh/anuyen_lab clinicops@IP_VM`):

```bash
id clinicops
sudo sshd -T | grep -E '^(permitrootlogin|passwordauthentication|kbdinteractiveauthentication|pubkeyauthentication) '
sudo ufw status verbose
systemctl list-timers 'clinic-*'
journalctl -u clinic-backup@dev.service --no-pager -n 20   # phải có lần chạy do timer kích hoạt
sudo ls -l /opt/anuyen-src/.infra-local/db-backups/dev/
cd /opt/anuyen-src/.infra-local/db-backups/dev && sudo sha256sum -c "$(sudo ls -t *.sha256 | head -1)"
journalctl -u clinic-host-health.service --no-pager -n 5
```

Từ máy vận hành, hai lệnh sau phải bị từ chối (`Permission denied`):

```bash
ssh -i ~/.ssh/anuyen_lab root@IP_VM
ssh -o PubkeyAuthentication=no -o PreferredAuthentications=password clinicops@IP_VM
```

Lưu output vào `docs/evidence/linux-cloud-<UTC>/`, thay IP thật bằng `<VM_IP>`/`<OPERATOR_IP>` trước khi commit (repo public).
