variable "libvirt_uri" {
  type    = string
  default = "qemu:///system"
}
variable "prefix" {
  type    = string
  default = "anuyen"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,20}$", var.prefix))
    error_message = "Use a unique lab prefix with lowercase letters, digits and hyphens."
  }
}
variable "storage_path" {
  type        = string
  description = "Absolute Linux path on the libvirt host; dedicated lab storage, never a shared system pool."
}
variable "base_image_path" {
  type        = string
  description = "Locally downloaded Ubuntu24.04 cloud image, verified against its official checksum."
}
variable "base_image_sha256" {
  type = string
  validation {
    condition     = can(regex("^[a-f0-9]{64}$", var.base_image_sha256))
    error_message = "Provide the official image SHA256, not a placeholder."
  }
}
variable "ssh_public_key" {
  type        = string
  description = "Actual operator public key only; never put a private key or password in Terraform."
  validation {
    condition     = can(regex("^ssh-(ed25519|rsa) [A-Za-z0-9+/]+=*", trimspace(var.ssh_public_key)))
    error_message = "Provide a real SSH public key."
  }
}
variable "network_cidr" {
  type    = string
  default = "192.168.150.0/24"
}
variable "operator_cidrs" {
  type        = list(string)
  description = "IPv4 operator source networks allowed to SSH during first boot; include the libvirt gateway if using the hypervisor."
  validation {
    condition = length(var.operator_cidrs) > 0 && alltrue([
      for cidr in var.operator_cidrs : can(cidrnetmask(cidr)) && !endswith(cidr, "/0")
    ])
    error_message = "Supply explicit operator IPv4 CIDRs; unrestricted /0 is forbidden."
  }
}
variable "nodes" {
  type    = map(object({ memory_mib = number, vcpus = number, disk_gib = number, address = number, mac = string }))
  default = null
  validation {
    condition     = var.nodes == null ? true : toset(keys(var.nodes)) == toset(["jenkins", "server", "agent"])
    error_message = "The lab must contain exactly Jenkins, k3s server and k3s agent."
  }
}
locals {
  nodes = var.nodes != null ? var.nodes : jsondecode(file("${path.module}/../lab-budget.json")).nodes
}
