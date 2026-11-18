# Chuẩn bị và dựng lab3 VM

> Cập nhật 18/11/2026: quy trình nghiệm thu và inventory/workspace mới ở
> `D:\nam4\project_devops\DevOps\docs\runbooks\infra-acceptance.md`.
> Có inventory mẫu lab/staging/production; fleet độc lập chưa triển khai.

Runbook chưa phải evidence đã provision. Người dùng chọn chuẩn bị trên máy hiện tại. Windows16,87GBRAM/WSL8GiB chưa đủ [profile](../../infra/lab-budget.json):3 VM tổng18GiB RAM/128GiB disk, dự trù host32GiB và160GiB disktrống. Đây là lựa chọn thiết kế, không phải cấu hình phần cứng PDF bắt buộc. /dev/kvm có thật nhưng user chưa có quyền; chưa libvirt/QEMU. Không cấp sudo/nhóm, sửa WSL hoặc tạo VM trong phiên này.

## Kiểm chứng local

```powershell
.\.venv\Scripts\python.exe scripts/install-infra-tools.py
wsl -d Ubuntu -e bash /mnt/d/nam4/project_devops/DevOps/scripts/setup-infra-control.sh
.\.venv\Scripts\python.exe scripts/verify-m3-local.py
```

Cần requirements.lock và infra/requirements-static.txt trong Pythonvenv. Installer ghim/checkSHA256 TerraformWindows/Linux, uv, addonmanifests, collections và schema. Pythoncontrol3.13.18/Ansible 2.22 vì core2.22 yêu cầuPython≥3.13; không chạy Ansible bằng Python 3.10 có sẵn. Cache ở .infra-local trênD, bị loại khỏi Git/Dockercontext. Collection cài offline từ artifactđã kiểm. DrvFS có thể báo Galaxycache world-writable; privateSSHkey nên ở filesystemLinux/mode0600, không coi chmod trênNTFS là đã bảo vệkey.

Verifier chỉ Terraform fmt/init/validate, schema/policy render, unit, Ansible/Bashsyntax, dependency/secret scan và preflightread-only. PreflightBLOCKED không biến thànhVMpass.

## Trước apply thật

Host Linux/KVM cần libvirtdaemon, QEMU, quyền /dev/kvm và qemu:///system; operator/admin phải chuẩn bị quyền phù hợp, không chmod777. Chọn host đủ ngân sách kể cả Windows/WSL/Docker. WSLcần RAM vật lý/hạn mức/diskbacking thật; df của ext4ảo không thay dung lượng ổWindows. Có thể dùng module trên hostLinux khác đủ tài nguyên.

Lấy Ubuntu24.04 từ [nguồn chính thức](https://cloud-images.ubuntu.com/releases/noble/), lưu ngoàiGit, xác minh SHA256SUMS đúng bản tải và ghi URL/ngày/hash. Copy lab.example.tfvars sang lab.tfvars bịignore, điền storage_pathriêng, imagepath/checksum thật và SSHpublickey thật; không privatekey/token trongTerraform. DrvFS/QEMUstorage chưa đo quyền/hiệu năng. Kiểm subnet192.168.150.0/24/prefix/MAC không đụng tài nguyên khác.

Trong Linux/WSL đã chuẩn bị:

```bash
.infra-local/ansible-venv/bin/python scripts/preflight-infra.py
.infra-local/bin/linux/terraform -chdir=infra/terraform init -input=false -lockfile=readonly
# Chọn workspace lab đã được review; xem runbook infra-acceptance trước khi tạo mới.
.infra-local/bin/linux/terraform -chdir=infra/terraform workspace select lab
.infra-local/ansible-venv/bin/python scripts/lab.py plan --var-file infra/terraform/lab.tfvars
# Review exactly3 VM, dedicated pool/volumes/cloud-init and labnetwork.
.infra-local/ansible-venv/bin/python scripts/lab.py apply --var-file infra/terraform/lab.tfvars
.infra-local/bin/linux/terraform -chdir=infra/terraform output -raw ansible_inventory > infra/ansible/inventories/lab/hosts.yml
```

lab.py từ chối tạo khi preflight chưaREADY. Terraform dùng provider thật, không shell/Vagrant thayVM. Lưu plan/outputđã che nhạy cảm, virshlist/3IP/SSH thật. Terraform quản lý NAT/DHCP/DNS và bootstrap UFW qua cloud-init; Ansible chờ cloud-init rồi bổ sung UFW trong VM.

## Ansible

Profile lab dùng một bộ 3 VM cho hai namespace. Có thêm inventory mẫu staging/production cho hai fleet độc lập với subnet và Vault riêng; chưa provision và cần ngân sách riêng. Sample inventory là IP dự kiến, không phải máy đã phát hiện. Chọn một mô hình theo runbook infra-acceptance, không gộp inventory các fleet.

Tạo inventorylab/vault.yml từ schema, nhập secret local rồi ansible-vault encrypt; file/password không commit. Có k3stoken≥32ký tự; CIrole cần Jenkinsadminpassword≥24, GitHubreadtoken và registrywritecredential. clinic_repo_revision phải commit40hex đã push.

```bash
export ANSIBLE_CONFIG="$PWD/infra/ansible/ansible.cfg"
export ANSIBLE_HOME="$PWD/.infra-local/ansible-home"
export ANSIBLE_COLLECTIONS_PATH="$PWD/.infra-local/collections"
.infra-local/ansible-venv/bin/ansible-playbook -i infra/ansible/inventories/lab/hosts.yml infra/ansible/site.yml --tags os,cluster --ask-vault-pass
# CI can wait independently for its credentials:
.infra-local/ansible-venv/bin/ansible-playbook -i infra/ansible/inventories/lab/hosts.yml infra/ansible/site.yml --tags ci --ask-vault-pass -e clinic_repo_revision=ACTUAL_COMMIT40HEX
```

Serverplay hoàn tất trước agent; role đợi NodeReady. Giữ SSHsession khi xác minh firewall:22từ operatorCIDR;6443/10250/UDP8472 chỉ mạngnode;80/443 cho lab/CI;9100nội bộ. Không mở8472/DB/broker raInternet. Jenkinsloopback18090/18085, giữ Jenkinscũ8080; CI VM6GiB dùng compose.ci.vm.yaml, hardlimit5GiB cộngOSreserve.

Chạy lần2cùngrevision/vars và lưu recapchanged=0. changed_when:false chỉ cho truy vấn read-only. Kiểm SSHrootdeny/UFW/2 nodesReady/k3sversion/exportermetrics/timers. Syntaxcheck không thay idempotencythật.

## Bootstrap bằng operator, tách CIdeployer

Dùng admin kubeconfiglab qua SSH, giữ ngoàiGit; đúng server/CA, không insecure-skip-tls-verify:

```bash
python scripts/bootstrap-cluster.py --expected-server https://192.168.150.11:6443
python scripts/prepare-cluster-secrets.py staging --registry-token-file .registry-token
python scripts/prepare-cluster-secrets.py production --registry-token-file .registry-token
kubectl create -f .infra-local/secrets/staging.json
kubectl create -f .infra-local/secrets/production.json
python scripts/issue-cluster-access.py --expected-server https://192.168.150.11:6443
```

Chưa chạy trêncluster trong phiên này. Secretgenerator từ chối ghi đè; không thay passwordDBđang có. Addon/RBAC/ClusterIssuer cần quyềnoperator; Jenkins chỉ namespaceRole. KubeconfigSA yêu cầu token8giờ: kiểm thời hạn APIserver cấp thực và rotateCredential sauhạn, không dùngadminkubeconfig cho deploy.

Jenkins cần clinic-kubeconfig-staging/production, clinic-lab-ca(publiccertificate) và clinic-smoke-staging/production. CertificateReady khác clienttrust: cài publicCA, DNS/hosts và kiểm HTTPSkhông-k. TerraformDNSalias trỏ hai domain.test vào server cho VM. Windows không tự thấy mạnglibvirtWSL: dùng forward/tunnel được kiểm tra, có thể HTTPS8443+hosts127.0.0.1, ghi port đúngURL. Có thể SSHforward18090từ VMJenkins quaWSL. Không tự sửa hosts/truststore trong phiên chuẩn bị.

## Quan sát HPA và KEDA

Hai tải độc lập, chỉ stagingsynthetic/Mailpit:

```bash
python scripts/load-http.py --url https://staging.anuyen.test --password-file PASSWORD_FILE --ca-file LAB_CA
kubectl -n staging get hpa api -w
kubectl -n staging set env deployment/worker WORKER_DELAY_SECONDS=2
python scripts/load-queue.py burst --url https://staging.anuyen.test --password-file PASSWORD_FILE --ca-file LAB_CA
kubectl -n staging get scaledobject worker
kubectl -n staging get deployment api worker -w
python scripts/load-queue.py cleanup --receipt RECEIPT --url https://staging.anuyen.test --password-file PASSWORD_FILE --ca-file LAB_CA
kubectl -n staging set env deployment/worker WORKER_DELAY_SECONDS-
```

Ghi CPUAPI, HPAcurrent/desired, queue ready/unacked/backlog và worker/timestamp. Cleanupcancellation sinh eventthêm; đợi rút tiếp và gỡ delay cả khi demo lỗi. HPAstabilization có thể dài hơn cooldown60; không hứa giảm trong60giây. Chưa có load/scaletimeline để công bố.

## Teardown

Xuất backup khỏi cả3 VM, kiểm checksum/state/plan; backup trênserver cũng mất khi xóaVMserver:

```bash
python scripts/lab.py destroy --var-file infra/terraform/lab.tfvars --confirm-prefix anuyen
```

Terraform vẫn hiển thị xác nhận, wrapper kiểm đúngprefix. Không reset/unregisterWSL, xóaDockerdata, đụng defaultpool/network hoặc VMkhác. Chưa có apply/destroy/restoreevidence để nghiệm thu demo1.
