# Windows VirtualBox feasibility check

Initial probe on 2026-11-19. Scope: provider installation/schema and source review only.
No VM was created, started, imported, modified or deleted. No Ubuntu disk image
was downloaded. This is not Terraform apply or clean-host Ansible evidence.

Continuation: image/seed/storage preparation and a real one-VM Terraform plan
were subsequently completed. See `infra/terraform-virtualbox/README.md` for the
updated execution record. A later apply created the VM but failed during guest
IP discovery; the existing resource is tainted and boot/SSH diagnosis is pending.

## Executed checks

- Windows Terraform executable: `D:\nam4\terraform_1.16.5_windows_amd64\terraform.exe`.
- Installed VirtualBox: `E:\VirtualBox\VBoxManage.exe`, version `7.2.22r175245`.
- Isolated scratch configuration:
  `D:\nam4\project_devops\DevOps\.infra-local\virtualbox-provider-check\main.tf`.
- Pinned provider: `terra-farm/virtualbox = 0.2.2-alpha.1`.
- `terraform init -backend=false -input=false -no-color`: passed; Terraform
  reported a self-signed community provider, key ID `51EC33490F8CDBE5`.
- `terraform validate -no-color`: passed for a provider-only configuration.
- `terraform providers schema -json`: passed. This launches the plugin but does
  not exercise VM creation or prove VirtualBox 7.2 compatibility.
- VirtualBox VM listing still shows the existing `HoangNgocBaoLong`; running VM
  listing is empty.
- Scratch schema, source snapshots, registry download metadata and lockfile are
  local evidence under the ignored scratch directory. No credentials are used.

The existing libvirt root requires Terraform 1.17.2; it was not changed or tested
with 1.16.5. The isolated probe intentionally permits 1.16.5 and has no resources.

## Findings from the exact provider release

Source reviewed: GitHub repository `terra-farm/terraform-provider-virtualbox`,
tag `v0.2.2-alpha.1`, files `virtualbox/resource_vm.go`, `virtualbox/image.go`
and `website/docs/r/vm.html.markdown`.

1. Image input is a tar-readable archive containing top-level VDI/VMDK disks.
   A raw QCOW2 image or Ubuntu installer ISO is not a drop-in image input.
2. `user_data` is written to VirtualBox ExtraData named `user_data`. It does not
   generate a standard NoCloud seed. Do not assume Ubuntu consumes this value.
3. `optical_disks` attaches an ISO, but its implementation executes external
   `cp -a`. A PowerShell `cp` alias does not satisfy Go's executable lookup.
   Git's `C:\Program Files\Git\usr\bin\cp.exe` exists on this host, but it
   was not added to PATH or tested for this workflow.
4. Gold images and VM folders are hardcoded under the current user's home:
   `.terraform/virtualbox/gold` and `.terraform/virtualbox/machine`. The schema
   has no storage-directory option. Setting VirtualBox's default VM folder
   alone will not redirect these explicit paths to `E:\DevOpsVMs`.
5. The schema has no disk-size argument. A 32 GiB disk must be prepared and
   verified outside this resource before it is cloned.
6. Although checksum fields exist, the reviewed create/download path does not
   invoke the image verification method. Verify SHA256 independently.
7. Absolute Windows drive paths are parsed as URL schemes by `fetchIfRemote`;
   prefer a tested relative archive path rather than assuming `E:/...` works.
8. The create path explicitly starts the VM. Do not use `status = "poweroff"`
   as a guarantee of a no-boot create. No apply was attempted in this probe.
9. Reported guest IPv4 information relies on VirtualBox guest properties. Guest
   integration and DHCP/bridge reachability still need a real runtime test.

## Ubuntu and SSH approach to validate next

Canonical's Ubuntu 24.04 cloud image listing includes
`noble-server-cloudimg-amd64.vmdk` and `.ova`, plus `SHA256SUMS` and its signature.
Only the index, checksums and package manifest were fetched. The manifest lists
cloud-init and openssh-server; this alone does not prove successful SSH boot.

Proposed workflow, not implemented or runtime-validated:

1. Select an immutable Canonical image build, verify the signed checksum manifest
   using an independently trusted Ubuntu signing key, then verify the download.
   Do not pin an image using the mutable `current` URL alone.
2. Prepare a 32 GiB disk and a tar archive matching the provider's disk scanner.
   Keep both prepared image and VM data on E; settle storage redirection before
   any apply. Do not move the user's home or modify existing VM paths implicitly.
3. Generate a NoCloud seed with volume label `cidata` containing `user-data` and
   `meta-data`. Seed a `clinicops` sudo user with the operator's public SSH key,
   disable password/root SSH, and use DHCP initially. Never put private SSH keys,
   Jenkins credentials or Vault passwords into Terraform/cloud-init state.
4. Resolve the optical ISO/external `cp` requirement, or investigate a supported
   alternative seed disk. Neither route has been tested here.
5. Test cloud-init completion, key-only SSH, guest integration and LAN reachability
   before invoking the existing Ansible roles. Do not assume bridged Wi-Fi works
   simply because the host adapter is listed.

## Decision

**Plugin probe passed; direct deployment is not yet approved.** The upstream
alpha provider has concrete storage and bootstrap limitations for this laptop.
Do not describe this result as a supported or working Ubuntu 24.04/VirtualBox
7.2 deployment. Before implementation, choose and test an explicit E-drive
storage strategy and NoCloud seed mechanism. If those cannot be made reliable,
evaluate another Terraform-managed approach rather than presenting manual VM
creation as Terraform compliance.

References (official upstream sources): provider source and release documentation
above; Canonical Ubuntu Cloud Images `noble` listing; cloud-init NoCloud datasource
documentation. This document deliberately separates source review and static
plugin checks from missing VM runtime evidence.