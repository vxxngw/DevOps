output "nodes" {
  value = { for name, node in local.nodes : name => { name = module.node[name].name, ip = cidrhost(var.network_cidr, node.address) } }
}
output "ssh_targets" {
  value = { for name, node in local.nodes : name => {
    user = "clinicops", host = cidrhost(var.network_cidr, node.address)
  } }
}
output "resource_budget" {
  value = { memory_mib = sum([for node in values(local.nodes) : node.memory_mib]), virtual_disk_gib = sum([for node in values(local.nodes) : node.disk_gib]), vcpus = sum([for node in values(local.nodes) : node.vcpus]) }
}
