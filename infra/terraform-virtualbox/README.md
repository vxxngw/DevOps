# Jenkins VM on a Windows VirtualBox host

This is a separate Terraform root, not a replacement for the libvirt root.
It manages only `anuyen-jenkins` (6 GiB, 2 vCPU). The upstream alpha provider is
still awaiting an actual apply/SSH acceptance test on VirtualBox 7.2.

## Local preparation performed on 2026-11-19

- Terraform 1.17.2 is available at
  `D:\nam4\project_devops\DevOps\.infra-local\bin\windows\terraform.exe`.
- Canonical Ubuntu 24.04 build `20261017` was downloaded from its dated Noble
  build directory, not a mutable `current` URL.
- `SHA256SUMS.gpg` verified successfully with the UEC image signing fingerprint
  `D2EB44626FDDC30B513D5BB71A5D6C4C7DB87C81`; GPG's owner-trust warning is expected
  for this isolated keyring. The fingerprint is documented in Canonical's public
  image verification documentation.
- Original VMDK SHA256:
  `9a1e3959c9f4ad9d4752101fd4ff9a43191fb7d72e61fa20e033f9fd235ce794`.
- VMDK cloned with VBoxManage to dynamic VDI and resized to 32768 MiB. A tar
  archive with top-level `root.vdi` is prepared under
  `E:\DevOpsVMs\images\noble-20261017`. Prepared archive hashes are generated
  locally because disk UUIDs differ across preparations.
- New dedicated SSH key: `E:\DevOpsVMs\keys\jenkins_ed25519`; private key ACL
  is restricted to the current Windows user. It is not password-protected, for
  noninteractive automation. Do not share or commit it.
- NoCloud seed: `E:\DevOpsVMs\jenkins\cidata.iso`, volume label `cidata`, contains
  `user-data` and `meta-data`. User `clinicops` has key-only login and sudo access.
  Bootstrap requests UFW and VirtualBox guest utilities and permits SSH from
  `192.168.1.169/32` only. Update the seed before first boot if the operator IP
  changes; never loosen it to all networks just to bypass connection issues.
- Provider storage junction:
  `C:\Users\USER\.terraform\virtualbox` -> `E:\DevOpsVMs\terraform-virtualbox`.
  The source did not exist before preparation. Existing VM paths were untouched.
- Local active Terraform root/state/variables:
  `E:\DevOpsVMs\jenkins\terraform`. The tracked root is copied there so all large
  runtime files stay on E. The runner refuses source drift; review and sync
  explicitly after changing the tracked HCL. State belongs to this host only.
- `terraform plan` passed: **1 add, 0 change, 0 destroy**.

## Runtime attempt (2026-11-19, 01:18 local time)

An initial attempt was blocked by available RAM. A subsequent capacity check
passed with 8258 MiB available and Terraform apply was executed. It created and
started `anuyen-jenkins`, UUID `19b68220-bb8b-47c9-8d27-d58fc1588cb0`, then failed:

```text
can't convert vbox network to terraform data: No match with get guestproperty output
```

The VM exists and is running; Terraform state contains its UUID but marks the
instance `tainted`. **Do not run apply again, recreate, or blindly untaint it.**
The runner now blocks tainted state before planning. `prevent_destroy` also
protects against replacement. The old `HoangNgocBaoLong` VM remains unchanged.

Read-only diagnosis:

- Guest screenshot shows Ubuntu kernel device initialization, root disk detected
  as 32 GiB, and `cidata.iso` attached. Repeated screenshots did not show further
  progress during the observation period. This does not establish a root cause.
- Guest properties do not yet report network count or IP; `guestproperty get`
  returns `No value set!`. Upstream `go-virtualbox` expects `Value: ...` and raises
  the observed parse error instead of treating the absent value as pending.
- VirtualBox log shows Windows hypervisor present and fallback to NEM. This is
  not evidence that BIOS virtualization is disabled. Hyper-V/WSL were not changed.
- GPT end-of-disk warnings are visible after resizing; filesystem/cloud-init
  growth and SSH readiness have not yet been verified.
- Console images and upstream parser source are saved under the ignored
  `D:\nam4\project_devops\DevOps\.infra-local` directory.

Next: diagnose guest boot and obtain real cloud-init/IP/SSH evidence first,
then reconcile Terraform state only after confirming resource completeness.
No Ansible provisioning or Jenkins service installation has occurred.

### Boot/SSH recovery on the same VM

The guest did not respond to an ACPI power button during diagnosis. Only the new
Jenkins VM was powered off, UART1 file logging was enabled, and it was restarted;
neither its disk nor Terraform resource was recreated. Serial output is at
`E:\DevOpsVMs\jenkins\boot-serial.log`. The previous stall's root cause remains
unproven; enabling serial output is diagnostic, not a proven general fix.

The restarted guest reached login, consumed the NoCloud seed and received DHCP
address **192.168.1.33/24** on `enp0s17`. Host key was collected using ssh-keyscan
and verified against the ED25519 fingerprint printed by cloud-init on the trusted
VirtualBox serial console before adding it to the dedicated known-hosts file:
`SHA256:7pJHCLotXTjE3qMeIp070zjcJlKPdHro1tjyjoS5k/s`.

Initial SSH signing failed because key generation had accidentally set a literal
two-double-quote passphrase through shell argument handling. It was removed using
Python subprocess arguments with a true empty passphrase, preserving the same
public key. The private key's current-user-only read ACL was restored afterward.
Use explicit native Windows OpenSSH paths; Git tools can shadow native tools.

Runtime checks over authenticated SSH now show:

- Hostname `anuyen-jenkins`, noninteractive sudo works.
- Root filesystem about 30 GiB, confirming disk/filesystem growth.
- Bridged host-to-guest SSH works at `192.168.1.33` (DHCP, not reserved).
- UFW active, default deny incoming/allow outgoing; TCP 22 allowed only from
  operator `192.168.1.169/32`. These bootstrap settings were applied over SSH
  while cloud-init was still downloading package indexes.
- Effective SSH: `permitrootlogin no`, `passwordauthentication no`,
  `pubkeyauthentication yes`; sshd config validated before reloading.
- cloud-init final stage is still running `apt-get update` and making download
  progress. Do not kill apt/dpkg or start competing installation processes.
- Guest network properties remain absent until guest utilities are installed.
  Terraform remains tainted; it has not been untainted or re-applied.

Local SSH evidence: ignored
`D:\nam4\project_devops\DevOps\.infra-local\jenkins-runtime-check.log`.
A Jenkins-only private JSON-as-YAML inventory is prepared under
`D:\nam4\project_devops\DevOps\.infra-local\virtualbox-jenkins-inventory`.
It has no Vault or Git revision yet. Its Linux SSH path is an initial WSL path;
before using it, copy the dedicated private key to a protected Linux filesystem
with mode 0600 and update the path if WSL mount permissions are unsuitable.

Next: wait for `cloud-init status --wait`, check guest utilities and provider
refresh, then assess whether state can safely be untainted without replacement.
Do not report the original apply as successful merely because SSH now works.

## Resume

Run from PowerShell (no Docker Desktop or WSL is required for Terraform):

```powershell
# Inspect/re-plan only; does not create a VM.
& 'D:\nam4\project_devops\DevOps\scripts\invoke-jenkins-virtualbox.ps1'

# Re-plan, check source/storage/allowed actions and capacity, then apply saved plan.
& 'D:\nam4\project_devops\DevOps\scripts\invoke-jenkins-virtualbox.ps1' -Apply
```

The runner places native Windows tar ahead of Git tar and provides Git's external
`cp.exe` for the provider ISO copy. The resource prevents destruction and verifies
both prepared image and seed SHA256 before creation. The runner only accepts
no-op or creation of the expected Jenkins VM; replacements/deletions are refused.

If apply fails, inspect both Terraform state and VirtualBox's VM list before
retrying: upstream can leave a partial VM on a create failure. Do not blindly
delete, import, or re-create it. No automatic rollback deletes user resources.

After a successful apply, record guest IP and inspect `cloud-init status --wait`
over SSH using the dedicated key. Verify the SSH host fingerprint against the VM
console/trusted evidence before accepting it; do not disable host key checking.
Check DHCP/bridged reachability and effective UFW before provisioning services.

## Remaining Ansible inputs and acceptance

The existing `infra/ansible/site.yml` remains the provisioning entry point.
Prepare a private inventory with the actual Jenkins IP, key path as seen from
the Linux Ansible control machine, current operator CIDR, and public key. Use
`--limit` to Jenkins; do not run three-node preflight against this one laptop.

The Jenkins role additionally requires an actual 40-character Git revision
available in the remote repository and an encrypted deployment Vault containing:

- `vault_jenkins_admin_password` (at least 24 characters),
- `vault_github_read_token`,
- `vault_registry_write_token`.

No real credentials were requested or read during preparation. Existing synthetic
Vault test artifacts must not be reused for deployment. Do not paste credentials
into chat, HCL, shell command lines or logs. Populate them privately using the
existing encrypted Vault workflow. Uncommitted local changes are not deployable
by the Jenkins role's exact remote-revision checkout until reviewed and pushed.

Ansible is now running from the existing Ubuntu WSL control environment using
the pinned Ansible virtualenv and collections. Docker Desktop was not started.
The private key was copied to `/root/.ssh/clinic-virtualbox-jenkins` with mode
0600, and the private inventory was updated accordingly.

Runtime acceptance is still pending: Terraform apply, clean-host Ansible, second
run `changed=0`, effective SSH/UFW, Jenkins and agent health. Full-fleet acceptance
also requires the other two laptops and scheduled backups on the k3s server.

## Latest continuation: Terraform reconciliation and OS provisioning

- Cloud-init completed without errors. Guest utilities are active and now expose
  real guest network properties.
- After inspecting the existing VM, a backed-up Terraform state was refreshed
  with refresh-only apply. The resource was then untainted and a normal plan
  returned `No changes` (exit 0). The original failed create was not repeated.
- First Ansible run with `--limit anuyen-jenkins --tags os` completed:
  `ok=30 changed=19 unreachable=0 failed=0 skipped=2 rescued=0 ignored=0`.
  This covers common OS, node exporter and host-health roles only, not Jenkins.
- An interrupted/incomplete second-run log is not convergence evidence. Another
  attempt lost connectivity when DHCP changed the guest IP to **192.168.1.27**.
- The new IP was checked against VirtualBox guest properties, guest MAC and the
  previously console-verified SSH host key. Strict host-key checking remains on.
  The private inventory and Terraform output now use 192.168.1.27. No static IP or
  router reservation was configured. Reserve guest MAC `08:00:27:F7:B0:50` on the
  router if the network administrator permits; do not assume DHCP is stable.
- The private `clinic_node_cidr` was updated to `192.168.1.27/32` for this
  Jenkins-only inventory. A fresh pair of OS runs was started with identical
  variables; inspect their complete recaps before claiming convergence:
  `.infra-local/jenkins-os-current-first.log` and
  `.infra-local/jenkins-os-current-second.log`. The recap validator result is
  `.infra-local/jenkins-os-current-recap.txt` when both commands finish.
- That pair has now completed with process exit 0 for both runs. First recap:
  `ok=27 changed=1 unreachable=0 failed=0 skipped=3 rescued=0 ignored=0`.
  Second recap: `ok=27 changed=0 unreachable=0 failed=0 skipped=3 rescued=0 ignored=0`.
  The recap validator accepted the second log for the full Jenkins-only inventory.
  This is OS-tag convergence on one VM only; CI/Vault and k3s plays were excluded.
- Real runtime checks at the current IP: SSH active, cloud-init done, node
  exporter HTTP 200 locally, health timer active, scheduled health journal
  `healthy: true`, and service `Result=success`, `ExecMainStatus=0`.

No deployment Vault exists in the Jenkins-only inventory. Jenkins installation
is still blocked on privately populated real credentials and a reviewed remote
Git revision. Do not use synthetic Vault artifacts or claim fleet-wide acceptance.