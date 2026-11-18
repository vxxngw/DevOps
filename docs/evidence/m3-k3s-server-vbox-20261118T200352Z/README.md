# M3 – k3s server prototype trên VirtualBox (2026-11-18 UTC)

Phạm vi: **một VM `anuyen-server`** trên VirtualBox, cấu hình bằng bộ Ansible riêng (`ansible-lab`), **không phải** role trong `infra/ansible` và **không có** Terraform plan/apply. Trạng thái: **PARTIAL**.

## Đã chứng minh
- Cài từ cloud image trắng: role common, node_exporter, k3s_server.
- Lần 1: `ok=23 changed=8 failed=0` ([run1-server.log](run1-server.log)).
- Lần 2: `ok=21 changed=0 failed=0`, idempotent ([run2-server.log](run2-server.log)).
- Secret (k3s token) mã hoá Ansible Vault; inventory tách dev/staging.
- Node `anuyen-server Ready control-plane,etcd`, k3s v1.37.2+k3s1, IP 192.168.56.11.
- Timer `k3s-backup.timer` mỗi 6 giờ; chạy tay tạo snapshot etcd 3,3 MB ([check-server.txt](check-server.txt)).

## Lệch thiết kế / chưa chứng minh
Xem `deviations_from_design` và `not_proven` trong [metadata.json](metadata.json). Không dùng evidence này thay cho chạy `infra/ansible/site.yml` trên VM sạch, Terraform apply, agent join hay restore.
