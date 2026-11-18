# Bài 3 – Linux trên một VM VirtualBox

[vbox-lab.py](../../scripts/infra/vbox-lab.py) tạo một VM Ubuntu 24.04 từ cloud image chính thức; playbook [linux-lab.yml](../../infra/ansible/linux-lab.yml) cấu hình nó làm máy chủ Bài 3:

| Yêu cầu Bài 3 | Thực hiện bằng |
|---|---|
| Script Bash sao lưu CSDL theo lịch | `scripts/infra/backup.sh dev` (pg_dump + SHA-256 + xoá bản cũ hơn 7 ngày) chạy bởi `clinic-backup@dev.timer` (hằng giờ trên VM lab) |
| Kiểm tra sức khỏe máy chủ | `scripts/infra/host-health.sh` (RAM, đĩa `/`, load) chạy bởi `clinic-host-health.timer` mỗi 15 phút |
| User riêng | `clinicops` (cloud-init tạo, role `common` đảm bảo); dịch vụ health chạy `DynamicUser` |
| SSH bằng key | `PasswordAuthentication no`, `KbdInteractiveAuthentication no`, `PubkeyAuthentication yes` |
| Tắt đăng nhập root | `PermitRootLogin no` |
| Bật UFW | Mặc định chặn vào; chỉ mở 22 từ máy vận hành, 9100 từ mạng host-only |

PostgreSQL chạy bằng Docker Compose (service `postgres`) với dữ liệu synthetic (migrate + seed). Backup staging/production trong k3s vẫn do `site.yml` cài trên `k3s_server`.

## 1. Chuẩn bị (một lần)

1. Cài VirtualBox 7 (`winget install -e --id Oracle.VirtualBox` hoặc bộ cài từ virtualbox.org). Ổ C ít chỗ thì chọn thư mục cài trên ổ D. Bộ cài tạo sẵn *VirtualBox Host-Only Ethernet Adapter* `192.168.56.1`.
2. Tạo SSH key riêng cho lab (PowerShell):
   ```bash
   ssh-keygen -t ed25519 -f $HOME/.ssh/anuyen_lab -C anuyen-lab
   ```

## 2. Tạo VM

```bash
.venv/Scripts/python.exe scripts/infra/vbox-lab.py --public-key ~/.ssh/anuyen_lab.pub
```

Script tải `ubuntu-24.04-server-cloudimg-amd64.vmdk` (~563 MB, kiểm SHA-256) vào `.infra-local/downloads`, tạo VM `anuyen-lab` (2 vCPU, 4 GB RAM, đĩa 20 GB) trong `.infra-local/vbox` (ổ D), NIC1 NAT ra Internet, NIC2 host-only `192.168.56.10`. cloud-init nhận user `clinicops` + key qua SMBIOS/HTTP, không cần ISO. Log khởi động: `.infra-local/vbox/anuyen-lab/console.log`. Xoá VM: `VBoxManage unregistervm anuyen-lab --delete`.

## 3. Chạy playbook (từ WSL, venv Ansible trong `.infra-local`)

1. Chép key vào WSL với quyền 600 (ssh từ chối key trên `/mnt/c`):
   ```bash
   install -D -m 600 /mnt/c/Users/$WINUSER/.ssh/anuyen_lab ~/.ssh/anuyen_lab
   ```
2. Đăng nhập lần đầu và xem VM thấy SSH đến từ IP nào; IP đó phải nằm trong `clinic_operator_cidrs` (mặc định `192.168.56.1/32`), nếu không UFW sẽ khoá Ansible ngay khi bật:
   ```bash
   ssh -i ~/.ssh/anuyen_lab clinicops@192.168.56.10 'echo $SSH_CLIENT'
   ```
3. Chạy hai lần; lần hai phải `changed=0`:
   ```bash
   export ANSIBLE_CONFIG=$PWD/infra/ansible/ansible.cfg ANSIBLE_HOME=$PWD/.infra-local/ansible-home ANSIBLE_COLLECTIONS_PATH=$PWD/.infra-local/collections
   .infra-local/ansible-venv/bin/ansible-playbook -i infra/ansible/inventories/vbox/hosts.example.yml infra/ansible/linux-lab.yml \
     --private-key ~/.ssh/anuyen_lab -e "clinic_operator_public_key='$(cat ~/.ssh/anuyen_lab.pub 2>/dev/null || cat /mnt/c/Users/$WINUSER/.ssh/anuyen_lab.pub)'" \
     -e clinic_repo_revision=$(git rev-parse HEAD)
   ```

## 4. Kiểm chứng

Trên VM (`ssh -i ~/.ssh/anuyen_lab clinicops@192.168.56.10`):

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
ssh -i ~/.ssh/anuyen_lab root@192.168.56.10
ssh -o PubkeyAuthentication=no -o PreferredAuthentications=password clinicops@192.168.56.10
```

Lưu output vào `docs/evidence/linux-lab-<UTC>/`.
