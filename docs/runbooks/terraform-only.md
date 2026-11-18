# Terraform + cloud-init/Bash migration

## Decision (2026-11-19)

The operator requested removal of Ansible from the active source and pipeline.
Terraform manages VM lifecycle; cloud-init bootstraps users/SSH/UFW on new guests.
Explicit Bash scripts manage guest services. This does **not** satisfy a mandatory
Ansible requirement in Bài 7. It is not evidence of complete Jenkins/K3s/backup.

The previous Ansible source was moved, not destroyed, to
`E:\DevOpsVMs\jenkins\retired-ansible-20261119-042437`.
Private `.infra-local` files, encrypted Vaults, SSH keys and Terraform states are
preserved. Never copy decrypted secrets into Terraform variables, user-data,
provisioner arguments or Git. The previously pushed deployment branch is a
historical Ansible-based revision and is not the new Terraform-only workflow.

## Existing Jenkins VM

- Use `scripts/invoke-jenkins-virtualbox.ps1` for guarded plans of the existing
  VirtualBox root. Its resource address and prevent-destroy guard are unchanged.
- Runtime state stays at `E:\DevOpsVMs\jenkins\terraform`.
- Do not replace the existing seed ISO or change cloud-init identity to rerun it.
  Review plans and reject replacement/deletion; never reset Terraform state.
- DHCP may change the guest IP. Read VirtualBox guest properties, verify the
  trusted SSH key and update connection metadata before connecting.
- OS, Docker and host-health timer installed earlier remain on the guest.
  Removing controller-side Ansible does not uninstall guest services.
- `scripts/configure-host.sh` installs the health script and timer when run
  explicitly as root from a checkout on Ubuntu. It leaves SSH/UFW untouched.

## Validation and remaining scope

Run Terraform fmt/validate and `bash -n` for shell syntax. A successful plan is
not guest-service acceptance. Jenkins controller/agent installation, k3s join,
node exporter installation on new hosts and scheduled database backup still
need replacement Bash automation and real runtime verification. Existing
backup/restore scripts remain, but a backup schedule is not automatically
installed by this migration. No claim of three-host acceptance is made.

Historical runbooks mentioning Ansible are retained as history, not current
execution instructions. Follow this runbook for the active migration scope.