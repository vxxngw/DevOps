# Ansible lab (k3s + Docker + Jenkins agent + node exporter)

## Cấu trúc
- `site.yml` – playbook chính, gán role theo nhóm máy
- `inventories/dev`, `inventories/staging` – inventory tách theo môi trường
- `inventories/*/group_vars/all/vault.yml` – secret, **phải mã hoá bằng Ansible Vault**
- `roles/` – common, node_exporter, k3s_server, k3s_agent, docker, jenkins_agent

## Chạy lần đầu
```bash
echo 'mat-khau-vault-cua-ban' > ~/.vault_pass && chmod 600 ~/.vault_pass
sed -i "s/DOI-THANH-CHUOI-NGAU-NHIEN-dev/$(openssl rand -hex 24)/" inventories/dev/group_vars/all/vault.yml
sed -i "s/DOI-THANH-CHUOI-NGAU-NHIEN-staging/$(openssl rand -hex 24)/" inventories/staging/group_vars/all/vault.yml
ansible-vault encrypt inventories/dev/group_vars/all/vault.yml inventories/staging/group_vars/all/vault.yml

ansible all -m ping
ansible-playbook site.yml | tee run1.log
ansible-playbook site.yml | tee run2.log     # PLAY RECAP phải changed=0 (idempotent)
```
Chỉ cài k3s server: `ansible-playbook site.yml --limit k3s_server`
Môi trường staging: `ansible-playbook -i inventories/staging/hosts.yml site.yml`
