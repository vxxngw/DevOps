resource "libvirt_pool" "lab" {
  name   = "${var.prefix}-images"
  type   = "dir"
  target = { path = var.storage_path }
}
resource "libvirt_network" "lab" {
  name      = "${var.prefix}-net"
  autostart = true
  forward   = { mode = "nat" }
  bridge    = { name = "vbr${substr(sha256(var.prefix), 0, 11)}" }
  domain    = { name = "anuyen.test", local_only = "yes" }
  dns = {
    host = [{
      ip        = cidrhost(var.network_cidr, local.nodes.server.address)
      hostnames = [{ hostname = "staging.anuyen.test" }, { hostname = "hospital.anuyen.test" }]
    }]
  }
  ips = [{
    address = cidrhost(var.network_cidr, 1)
    prefix  = tonumber(split("/", var.network_cidr)[1])
    dhcp = {
      ranges = [{ start = cidrhost(var.network_cidr, 100), end = cidrhost(var.network_cidr, 199) }]
      hosts  = [for name, node in local.nodes : { name = "${var.prefix}-${name}", mac = node.mac, ip = cidrhost(var.network_cidr, node.address) }]
    }
  }]
}
resource "libvirt_volume" "base" {
  name   = "${var.prefix}-ubuntu-24.04.qcow2"
  pool   = libvirt_pool.lab.name
  target = { format = { type = "qcow2" } }
  create = { content = { url = abspath(var.base_image_path) } }
  lifecycle {
    precondition {
      condition     = filesha256(var.base_image_path) == var.base_image_sha256
      error_message = "Cloud image checksum does not match; refusing VM creation."
    }
  }
}
module "node" {
  source          = "./modules/vm"
  for_each        = local.nodes
  name            = "${var.prefix}-${each.key}"
  pool            = libvirt_pool.lab.name
  base_image_path = libvirt_volume.base.path
  network_name    = libvirt_network.lab.name
  memory_mib      = each.value.memory_mib
  vcpus           = each.value.vcpus
  disk_gib        = each.value.disk_gib
  mac             = each.value.mac
  ssh_public_key  = var.ssh_public_key
  operator_cidrs  = var.operator_cidrs
}
