output "nodes" {
  value = { for name, node in local.nodes : name => { name = module.node[name].name, ip = cidrhost(var.network_cidr, node.address) } }
}
output "ansible_inventory" {
  value = yamlencode({ all = {
    vars = { ansible_user = "clinicops", ansible_python_interpreter = "/usr/bin/python3", clinic_node_cidr = var.network_cidr, clinic_operator_public_key = trimspace(var.ssh_public_key) }
    children = {
      jenkins    = { hosts = { "${var.prefix}-jenkins" = { ansible_host = cidrhost(var.network_cidr, local.nodes.jenkins.address) } } }
      k3s_server = { hosts = { "${var.prefix}-server" = { ansible_host = cidrhost(var.network_cidr, local.nodes.server.address) } } }
      k3s_agent  = { hosts = { "${var.prefix}-agent" = { ansible_host = cidrhost(var.network_cidr, local.nodes.agent.address) } } }
    }
  } })
}
output "resource_budget" {
  value = { memory_mib = sum([for node in values(local.nodes) : node.memory_mib]), virtual_disk_gib = sum([for node in values(local.nodes) : node.disk_gib]), vcpus = sum([for node in values(local.nodes) : node.vcpus]) }
}
