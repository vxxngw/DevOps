# Copy to ignored lab.tfvars and supply ACTUAL values before plan/apply.
libvirt_uri     = "qemu:///system"
operator_cidrs  = ["192.168.150.1/32"]
storage_path    = "/var/lib/libvirt/anuyen-lab"
base_image_path = "/var/lib/libvirt/clinic-images/ubuntu-24.04.img"
# Required: base_image_sha256 and ssh_public_key. No fake keys/checksums supplied.
