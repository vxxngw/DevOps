"""Create the single Bai 3 VirtualBox VM from the official Ubuntu 24.04 cloud image.

cloud-init gets clinicops + SSH key + a host-only static IP through NoCloud over SMBIOS/HTTP
(VirtualBox NAT maps 10.0.2.2 to the host), so no ISO tool is needed. Ansible linux-lab.yml
does the rest. Remove the VM with: VBoxManage unregistervm anuyen-lab --delete
"""

import argparse
import hashlib
import http.server
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = next(
    p
    for p in Path(__file__).resolve().parents
    if (p / "Jenkinsfile").is_file() and (p / "pyproject.toml").is_file()
)
IMAGE_URL = "https://cloud-images.ubuntu.com/releases/noble/release/"
IMAGE = "ubuntu-24.04-server-cloudimg-amd64.vmdk"
WORK = ROOT / ".infra-local/vbox"


def expected_sha256(sums: str, name: str) -> str:
    for line in sums.splitlines():
        digest, _, filename = line.partition(" ")
        if filename.lstrip("*") == name:
            return digest
    raise ValueError(f"{name} is missing from SHA256SUMS")


def seed_files(public_key: str, ip: str, name: str) -> dict[str, str]:
    """Same login contract as the Terraform cloud-init: clinicops, key only, passwordless sudo."""
    config = {
        "hostname": name,
        "ssh_pwauth": False,
        "users": [
            {
                "name": "clinicops",
                "groups": "sudo",
                "shell": "/bin/bash",
                "lock_passwd": True,
                "sudo": "ALL=(ALL) NOPASSWD:ALL",
                "ssh_authorized_keys": [public_key.strip()],
            }
        ],
        "write_files": [
            {
                "path": "/etc/netplan/60-hostonly.yaml",
                "permissions": "0600",
                "content": json.dumps(
                    {
                        "network": {
                            "version": 2,
                            "ethernets": {"enp0s8": {"addresses": [f"{ip}/24"]}},
                        }
                    }
                ),
            }
        ],
        "runcmd": [["netplan", "apply"]],
    }
    return {
        # JSON is valid YAML, so no YAML dependency is needed.
        "user-data": "#cloud-config\n" + json.dumps(config, indent=2) + "\n",
        "meta-data": f"instance-id: {name}-{int(time.time())}\nlocal-hostname: {name}\n",
        "vendor-data": "",
    }


def vboxmanage() -> str:
    found = shutil.which("VBoxManage")
    default = Path(os.environ.get("ProgramFiles", "")) / "Oracle/VirtualBox/VBoxManage.exe"
    if found or default.is_file():
        return found or str(default)
    sys.exit("VBoxManage not found: install VirtualBox first")


def vbox(*args: str) -> str:
    # stderr stays on the console so VBoxManage errors are visible.
    return subprocess.run(
        [vboxmanage(), *args], check=True, stdout=subprocess.PIPE, text=True
    ).stdout


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch_image() -> Path:
    # shortcut: trusts HTTPS + SHA256SUMS without its GPG signature; verify SHA256SUMS.gpg for production.
    expected = expected_sha256(
        urllib.request.urlopen(IMAGE_URL + "SHA256SUMS").read().decode(), IMAGE
    )
    path = ROOT / ".infra-local/downloads" / IMAGE
    if not path.is_file() or sha256(path) != expected:
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_suffix(".part")
        with urllib.request.urlopen(IMAGE_URL + IMAGE) as response, partial.open("wb") as out:
            shutil.copyfileobj(response, out)
        if sha256(partial) != expected:
            partial.unlink()
            sys.exit("Downloaded image checksum mismatch")
        partial.replace(path)
    return path


def hostonly_adapter() -> str:
    adapter = None
    for line in vbox("list", "hostonlyifs").splitlines():
        key, _, value = line.partition(":")
        if key == "Name":
            adapter = value.strip()
        elif key == "IPAddress" and value.strip() == "192.168.56.1":
            return adapter
    sys.exit(
        "No VirtualBox host-only adapter on 192.168.56.1; create one in VirtualBox Network Manager"
    )


def serve(files: dict[str, str]) -> tuple[http.server.HTTPServer, set[str]]:
    fetched: set[str] = set()

    class Seed(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = files.get(self.path.strip("/"))
            if body is None:
                self.send_error(404)
                return
            fetched.add(self.path.strip("/"))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body.encode())

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Seed)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, fetched


def wait_for_ssh(ip: str, timeout: int) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((ip, 22), timeout=3) as connection:
                if connection.recv(64).startswith(b"SSH-"):
                    return True
        except OSError:
            time.sleep(5)
    return False


def create(args):
    if f'"{args.name}"' in vbox("list", "vms"):
        sys.exit(
            f"VM {args.name} already exists; remove it first: VBoxManage unregistervm {args.name} --delete"
        )
    public_key = Path(args.public_key).expanduser().read_text(encoding="utf-8")
    if not public_key.startswith("ssh-"):
        sys.exit("--public-key must be an OpenSSH public key file (.pub)")
    adapter = hostonly_adapter()
    image = fetch_image()
    folder = WORK / args.name
    disk = folder / f"{args.name}.vdi"
    vbox(
        "createvm",
        "--name",
        args.name,
        "--ostype",
        "Ubuntu_64",
        "--basefolder",
        str(WORK),
        "--register",
    )
    vbox(
        "modifyvm",
        args.name,
        "--memory",
        str(args.memory),
        "--cpus",
        str(args.cpus),
        "--nic1",
        "nat",
        # VirtualBox >= 6.1.28 blocks 10.0.2.2 -> host loopback unless enabled; the seed is served there.
        "--nat-localhostreachable1",
        "on",
        "--nic2",
        "hostonly",
        "--hostonlyadapter2",
        adapter,
        # Ubuntu cloud images log to ttyS0; without a serial port boot stalls.
        "--uart1",
        "0x3F8",
        "4",
        "--uartmode1",
        "file",
        str(folder / "console.log"),
    )
    vbox("clonemedium", "disk", str(image), str(disk), "--format", "VDI")
    # Unregister the shared source image, or the next VM's clone fails on a stale registry entry.
    vbox("closemedium", "disk", str(image))
    vbox("modifymedium", "disk", str(disk), "--resize", str(args.disk_gb * 1024))
    vbox("storagectl", args.name, "--name", "SATA", "--add", "sata", "--portcount", "1")
    vbox(
        "storageattach",
        args.name,
        "--storagectl",
        "SATA",
        "--port",
        "0",
        "--device",
        "0",
        "--type",
        "hdd",
        "--medium",
        str(disk),
    )
    server, fetched = serve(seed_files(public_key, args.ip, args.name))
    try:
        vbox(
            "setextradata",
            args.name,
            "VBoxInternal/Devices/pcbios/0/Config/DmiSystemSerial",
            f"ds=nocloud;s=http://10.0.2.2:{server.server_address[1]}/",
        )
        vbox("startvm", args.name, "--type", "headless")
        ready = wait_for_ssh(args.ip, args.timeout)
    finally:
        server.shutdown()
    if not ready or "user-data" not in fetched:
        sys.exit(
            f"VM did not come up (seed fetched: {sorted(fetched)}); see {folder / 'console.log'}"
        )
    print(
        json.dumps({"vm": args.name, "ip": args.ip, "user": "clinicops", "seed": sorted(fetched)})
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--public-key", required=True)
    parser.add_argument("--name", default="anuyen-lab")
    parser.add_argument("--ip", default="192.168.56.10")
    parser.add_argument("--memory", type=int, default=4096)
    # Under Hyper-V (WSL2 hosts) VirtualBox falls back to NEM: 2 vCPUs stall in initramfs and
    # paravirt none/hyperv panics on the timer; 1 vCPU with KVM paravirt boots reliably.
    parser.add_argument("--cpus", type=int, default=1)
    parser.add_argument("--disk-gb", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=900)
    create(parser.parse_args())


if __name__ == "__main__":
    main()
