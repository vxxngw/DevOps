"""Read-only Linux/KVM readiness check. A blocked result is never an apply success."""

import argparse
import json
import os
import platform
import shutil
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = next(
    (
        p
        for p in Path(__file__).resolve().parents
        if (p / "Jenkinsfile").is_file() and (p / "pyproject.toml").is_file()
    ),
    Path.cwd(),
)


def probe(command):
    result = subprocess.run(command, capture_output=True, text=True, timeout=15)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    args = parser.parse_args()
    budget = json.loads((ROOT / "infra/lab-budget.json").read_text())
    required_memory = sum(node["memory_mib"] for node in budget["nodes"].values())
    required_vcpus = sum(node["vcpus"] for node in budget["nodes"].values())
    checks = []

    def add(name, passed, detail):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    linux = platform.system() == "Linux"
    add("linux_control_node", linux, platform.platform())
    add(
        "kvm_device_access",
        os.access("/dev/kvm", os.R_OK | os.W_OK),
        "Requires existing read/write permission; no sudo or group changes attempted",
    )
    add(
        "libvirt_socket",
        Path("/var/run/libvirt/libvirt-sock").exists(),
        "qemu:///system daemon must be installed on the chosen host",
    )
    for executable in ["virsh", "qemu-system-x86_64", "ssh"]:
        add(
            executable,
            shutil.which(executable) is not None,
            "Executable available on control/hypervisor host",
        )
    if linux:
        memory = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines())
        available = int(memory["MemAvailable"].split()[0]) // 1024
        total = int(memory["MemTotal"].split()[0]) // 1024
        add(
            "vm_ram_capacity",
            available >= required_memory + 1024,
            {
                "available_mib": available,
                "linux_total_mib": total,
                "vm_required_mib": required_memory,
                "reserve_mib": 1024,
            },
        )
    add(
        "vcpus",
        (os.cpu_count() or 0) >= required_vcpus,
        {"logical_cpus": os.cpu_count(), "vm_vcpus": required_vcpus},
    )
    free = shutil.disk_usage(ROOT).free
    add(
        "storage",
        free >= budget["minimum_free_storage_gib"] * 1024**3,
        {"free_bytes": free, "minimum_free_gib": budget["minimum_free_storage_gib"]},
    )
    add(
        "libvirt_connection",
        probe(["virsh", "-c", "qemu:///system", "list", "--all"])
        if shutil.which("virsh")
        else False,
        "Read-only connection; no domains created",
    )
    for host in ["registry.terraform.io", "github.com", "ghcr.io", "cloud-images.ubuntu.com"]:
        try:
            socket.getaddrinfo(host, 443)
            resolvable = True
        except OSError:
            resolvable = False
        add(
            "dns:" + host,
            resolvable,
            "DNS only; not registry authentication or webhook connectivity",
        )
    result = {
        "at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Host readiness only; no VM provisioning",
        "status": "READY" if all(item["passed"] for item in checks) else "BLOCKED",
        "checks": checks,
    }
    content = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        destination = Path(args.output).resolve()
        destination.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
    print(content)
    return 0 if result["status"] == "READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
