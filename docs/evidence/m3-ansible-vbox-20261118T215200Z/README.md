# M3 – Ansible cài 2 VM VirtualBox từ máy trắng (2026-11-18 UTC)

Code: [infra/ansible-lab](../../../infra/ansible-lab/README.md) (`site.yml`, 6 role). Trạng thái: **PASS cho dev**, staging chưa có máy.

| Yêu cầu mục 7 | Bằng chứng |
|---|---|
| Playbook chia role | `site.yml`: play base (common, node_exporter) → k3s_server → agent (docker, k3s_agent, jenkins_agent) |
| Cài từ máy trắng | VM `anuyen-agent` ban đầu không có docker/java/k3s; [run1-full.log](run1-full.log) |
| 2 node k3s Ready, Docker, node exporter | [check-cluster.txt](check-cluster.txt) |
| Idempotent | [run2-full.log](run2-full.log): `anuyen-agent changed=0`, `anuyen-server changed=0`, `failed=0` |
| Inventory theo môi trường | `inventories/dev` (chạy thật), `inventories/staging` (placeholder, chưa có VM) |
| Ansible Vault | `inventories/*/group_vars/all/vault.yml` mã hoá `$ANSIBLE_VAULT;1.1;AES256`; mật khẩu `~/.vault_pass` ngoài git |
| Jenkins agent | Node `anuyen-agent` online trên controller dự án (`clinic-ci-controller`, 127.0.0.1:18090) qua SSH launcher (plugin `ssh-slaves`); chạy với user `jenkins` thuộc nhóm `docker`, Java 21, Docker 29.1.3 |

## Diễn biến trung thực
- Lần 1 bị ngắt 2 lần do máy host hết RAM (15,7 GB): [run1-full-interrupted.log](run1-full-interrupted.log) (VM agent tắt khi cài k3s), [run1-full-agent-only.log](run1-full-agent-only.log) (server mất SSH sau khi đổi card 1 sang bridged). Sau khi tắt container dự án khác và giảm VM agent xuống 2 GB, [run1-full.log](run1-full.log) chạy trọn.
- Server được cài k3s ở lượt trước ([m3-k3s-server-vbox](../m3-k3s-server-vbox-20261118T200352Z/README.md)); ở run1-full server chỉ còn `changed=1` (apt cache).

## Môi trường
- Control node: WSL Ubuntu, ansible-core 2.20.1.
- `anuyen-server`: 2 vCPU/4 GB, card 1 NAT (SSH 127.0.0.1:2222; lần 1–2 card 1 là bridged Wi-Fi 192.168.1.77), card 2 host-only 192.168.56.11.
- `anuyen-agent`: 2 vCPU/2 GB, card 1 NAT (SSH 127.0.0.1:2223), card 2 host-only 192.168.56.12.
- k3s v1.37.2+k3s1 (kênh stable, chưa pin theo `infra/versions.json`).

## Chưa chứng minh
- Staging trên máy thật; Terraform; restore etcd snapshot.
- Bộ `infra/ansible` (thiết kế libvirt/Terraform) chưa áp lên VM; bộ chạy thật là `infra/ansible-lab`.

## Lần chạy 3 – Ansible vào server qua NAT 127.0.0.1:2222 (22:10 UTC)
Card 1 của server đổi từ bridged Wi-Fi về NAT (port forward 2222→22) để Ansible không phụ thuộc mạng Wi-Fi/hotspot; mạng k3s vẫn là host-only 192.168.56.0/24.
- Ping 2 VM, `--syntax-check` cho `dev` và `staging`, `ansible-vault view` đều OK.
- [run3-nat2222.log](run3-nat2222.log) (`--diff`): `anuyen-agent changed=0`, `anuyen-server changed=0`, `failed=0`.
- [check-cluster-nat2222.txt](check-cluster-nat2222.txt): 2 node Ready; docker, k3s, k3s-agent, node exporter, k3s-backup.timer active. Jenkins node `anuyen-agent` online.
