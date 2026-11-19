"""Build-stage only: install exact Terraform/kubectl, verify upstream checksums."""

import hashlib
import io
import json
import urllib.request
import zipfile
from pathlib import Path

versions = json.loads(Path("/tmp/versions.json").read_text())


def fetch(url):
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


destination = Path("/out")
destination.mkdir(exist_ok=True)
name = f"terraform_{versions['terraform']}_linux_amd64.zip"
base = f"https://releases.hashicorp.com/terraform/{versions['terraform']}/"
expected = next(
    line.split()[0]
    for line in fetch(base + f"terraform_{versions['terraform']}_SHA256SUMS").decode().splitlines()
    if line.split()[-1] == name
)
content = fetch(base + name)
if hashlib.sha256(content).hexdigest() != expected:
    raise RuntimeError("Terraform checksum mismatch")
with zipfile.ZipFile(io.BytesIO(content)) as archive:
    (destination / "terraform").write_bytes(archive.read("terraform"))
url = f"https://dl.k8s.io/release/v{versions['kubernetes']}/bin/linux/amd64/kubectl"
content = fetch(url)
if hashlib.sha256(content).hexdigest() != fetch(url + ".sha256").decode().strip():
    raise RuntimeError("kubectl checksum mismatch")
(destination / "kubectl").write_bytes(content)
for executable in destination.iterdir():
    executable.chmod(0o755)
