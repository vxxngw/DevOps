# Copy to ignored lab.tfvars and supply ACTUAL values before plan/apply.
libvirt_uri     = "qemu:///system"
storage_path    = "/mnt/d/CODE/OOPs/Do_An/.infra-local/vms"
base_image_path = "/mnt/d/CODE/OOPs/Do_An/.infra-local/images/ubuntu-24.04.img"
# Required: base_image_sha256 and ssh_public_key. No fake keys/checksums supplied.
