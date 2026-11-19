terraform {
  required_providers { libvirt = { source = "dmacvicar/libvirt", version = "= 0.9.9" } }
}
variable "name" { type = string }
variable "pool" { type = string }
variable "base_image_path" { type = string }
variable "network_name" { type = string }
variable "memory_mib" { type = number }
variable "vcpus" { type = number }
variable "disk_gib" { type = number }
variable "mac" { type = string }
variable "ssh_public_key" { type = string }

resource "libvirt_volume" "root" {
  name          = "${var.name}.qcow2"
  pool          = var.pool
  capacity      = var.disk_gib * 1024 * 1024 * 1024
  allocation    = 0
  target        = { format = { type = "qcow2" } }
  backing_store = { path = var.base_image_path, format = { type = "qcow2" } }
}
resource "libvirt_cloudinit_disk" "init" {
  name      = "${var.name}-init"
  meta_data = yamlencode({ instance-id = var.name, local-hostname = var.name })
  user_data = join("\n", ["#cloud-config", yamlencode({
    hostname         = var.name
    manage_etc_hosts = true
    ssh_pwauth       = false
    disable_root     = true
    users = [{
      name                = "clinicops", groups = "sudo", shell = "/bin/bash", lock_passwd = true
      sudo                = "ALL=(ALL) NOPASSWD:ALL"
      ssh_authorized_keys = [trimspace(var.ssh_public_key)]
    }]
  })])
}
resource "libvirt_volume" "init" {
  name   = "${var.name}-cidata.iso"
  pool   = var.pool
  target = { format = { type = "raw" } }
  create = { content = { url = libvirt_cloudinit_disk.init.path } }
}
resource "libvirt_domain" "node" {
  name        = var.name
  type        = "kvm"
  memory      = var.memory_mib
  memory_unit = "MiB"
  vcpu        = var.vcpus
  running     = true
  autostart   = false
  os          = { type = "hvm", type_arch = "x86_64", type_machine = "q35", boot_devices = [{ dev = "hd" }] }
  devices = {
    disks = [
      { source = { file = { file = libvirt_volume.root.path } }, target = { dev = "vda", bus = "virtio" } },
      { device = "cdrom", source = { file = { file = libvirt_volume.init.path } }, target = { dev = "sda", bus = "sata" }, read_only = true }
    ]
    interfaces = [{ mac = { address = var.mac }, model = { type = "virtio" }, source = { network = { network = var.network_name } } }]
  }
}
output "name" { value = libvirt_domain.node.name }
