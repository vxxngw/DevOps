# Bàn giao cụm k3s lab cho máy Jenkins của thành viên khác

Đề cho phép gộp máy thành viên: **3 VM = 1 Jenkins + 2 k3s**. Phân công:

| Máy | Người giữ | Vai trò |
|---|---|---|
| `anuyen-server` (VirtualBox) | Hoàng | k3s control-plane, ingress Traefik 443 |
| `anuyen-agent` (VirtualBox) | Hoàng | k3s worker |
| Jenkins (controller + agent Docker, `compose.ci.yaml`) | thành viên phụ trách CI | chạy `Jenkinsfile`, deploy qua kubeconfig theo namespace |

## Mạng

- `anuyen-server` có 3 card: NAT (SSH `127.0.0.1:2222`), host-only `192.168.56.11` (chỉ máy chủ VM thấy), **bridged `192.168.1.102`** (cả Wi-Fi thấy).
- Máy Jenkins phải **cùng mạng Wi-Fi/LAN** với máy chủ VM. Khác mạng thì cần VPN (Tailscale/ZeroTier) — chưa cấu hình.
- IP bridged do DHCP cấp; nếu đổi IP phải sửa `k3s_tls_san_extra` trong `infra/ansible-lab/inventories/dev/group_vars/all/vars.yml`, chạy lại Ansible và cấp lại kubeconfig. Nên đặt DHCP reservation trên router.
- Chứng chỉ API k3s có SAN `192.168.56.11`, `192.168.1.102`, `k3s.anuyen.test`, nên kubectl xác thực TLS đầy đủ, không dùng `insecure-skip-tls-verify`.
- VM không bật UFW: 6443/443 mở cho cả LAN. Chỉ dùng trong mạng tin cậy.

## Người giữ VM làm (một lần, rồi mỗi 8 giờ)

Chạy trên máy chủ VM, admin kubeconfig lưu trong `.infra-local/` (bị Git bỏ qua):

```bash
# Ansible lab chạy trong WSL Ubuntu (khóa ~/.ssh/m3, ~/.vault_pass)
cd infra/ansible-lab && ANSIBLE_CONFIG=$PWD/ansible.cfg ansible-playbook site.yml --limit k3s_server

# admin kubeconfig trỏ IP LAN (kubeconfig gốc: /etc/rancher/k3s/k3s.yaml, sửa server)
export KUBECONFIG=.infra-local/access/admin-lan.kubeconfig
python scripts/infra/bootstrap-cluster.py --expected-server https://192.168.1.102:6443
python scripts/infra/prepare-cluster-secrets.py staging --registry-token-file .registry-token
python scripts/infra/prepare-cluster-secrets.py production --registry-token-file .registry-token
kubectl create -f .infra-local/secrets/staging.json      # AlreadyExists = giữ secret cũ, đúng
kubectl create -f .infra-local/secrets/production.json
rm -f .infra-local/access/staging.json .infra-local/access/production.json
python scripts/infra/issue-cluster-access.py --expected-server https://192.168.1.102:6443
```

Gửi **riêng** (tin nhắn riêng/USB, không commit, không đăng nhóm) cho người giữ Jenkins 3 file:
`.infra-local/access/staging.json`, `.infra-local/access/production.json`, `.infra-local/access/lab-root-ca.crt`.
Token trong kubeconfig hết hạn sau **8 giờ**: hết hạn thì chạy lại 2 lệnh cuối và gửi lại.

## Người giữ Jenkins làm

1. Pull nhánh có thay đổi này. Thêm vào `.env.ci` (file local, không commit):

   ```
   CLINIC_CLUSTER_SERVER_URL=https://192.168.1.102:6443
   CLINIC_LAB_INGRESS_IP=192.168.1.102
   ```

2. Đặt GHCR token (`write:packages`, xin chủ repo) vào `.registry-token`, rồi:

   ```bash
   python scripts/ci/bootstrap-ci.py init        # lần đầu
   docker compose -f compose.ci.yaml --env-file .env.ci up -d --wait
   python scripts/ci/bootstrap-ci.py configure   # clinic-github, clinic-ghcr, job, agent node
   docker compose -f compose.ci.yaml --env-file .env.ci --profile agent --profile webhook up -d --build --wait
   python scripts/ci/bootstrap-ci.py configure-webhook
   ```

3. Jenkins → folder `an-uyen` → Credentials → thêm 3 credential loại **Secret file**:
   `clinic-kubeconfig-staging` (staging.json), `clinic-kubeconfig-production` (production.json), `clinic-lab-ca` (lab-root-ca.crt).
4. Sau lần deploy đầu, tạo tài khoản smoke theo [deploy.md](deploy.md) rồi thêm `clinic-smoke-staging` / `clinic-smoke-production` (Username with password).
5. Kiểm tra từ agent:

   ```bash
   docker exec clinic-ci-agent-1 getent hosts staging.anuyen.test   # phải ra 192.168.1.102
   ```

## Luồng pipeline

Push `main` → webhook (`PUBLISH_IMAGES=true`, `DEPLOY=true`) → checkout → secret scan → lint → unit test → build image → integration → Trivy → push GHCR digest → deploy staging → **Approve production** (`PRODUCTION_APPROVERS`, 15 phút) → deploy production. PR/nhánh khác chỉ chạy tới quét bảo mật.
