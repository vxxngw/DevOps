terraform {
  required_version = "= 1.17.2"
  required_providers {
    virtualbox = {
      source  = "terra-farm/virtualbox"
      version = "= 0.2.2-alpha.1"
    }
  }
}

provider "virtualbox" {}

variable "vm_name" {
  type = string
  validation {
    condition     = can(regex("^anuyen-[a-z0-9-]+$", var.vm_name))
    error_message = "Use a dedicated anuyen- VM name."
  }
}

variable "image_archive" {
  type        = string
  description = "Relative tar archive path; upstream does not parse Windows drive paths."
  validation {
    condition     = !can(regex("^[A-Za-z]:|^[/\\\\]", var.image_archive))
    error_message = "Use a relative archive path."
  }
}

variable "image_sha256" {
  type = string
  validation {
    condition     = can(regex("^[a-f0-9]{64}$", var.image_sha256))
    error_message = "Supply the verified prepared archive SHA256."
  }
}

variable "seed_iso" {
  type = string
}

variable "seed_sha256" {
  type = string
}

variable "bridge_interface" {
  type = string
}

resource "virtualbox_vm" "jenkins" {
  name          = var.vm_name
  image         = var.image_archive
  cpus          = 2
  memory        = "6.0 gib"
  status        = "running"
  optical_disks = [var.seed_iso]

  network_adapter {
    type           = "bridged"
    device         = "IntelPro1000MTServer"
    host_interface = var.bridge_interface
  }

  lifecycle {
    prevent_destroy = true
    precondition {
      condition     = filesha256(var.image_archive) == var.image_sha256
      error_message = "Prepared image archive checksum mismatch."
    }
    precondition {
      condition     = filesha256(var.seed_iso) == var.seed_sha256
      error_message = "NoCloud seed checksum mismatch."
    }
  }
}

output "vm_name" {
  value = virtualbox_vm.jenkins.name
}

output "ipv4_address" {
  value = virtualbox_vm.jenkins.network_adapter[0].ipv4_address
}