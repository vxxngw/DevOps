"""Install checksum-verified local tools/addons; does not install a hypervisor or create VMs."""

import hashlib
import io
import json
import os
import tarfile
import zipfile
from pathlib import Path

import httpx

ROOT = next(
    (
        p
        for p in Path(__file__).resolve().parents
        if (p / "Jenkinsfile").is_file() and (p / "pyproject.toml").is_file()
    ),
    Path.cwd(),
)


def main():
    versions = json.loads((ROOT / "infra/versions.json").read_text(encoding="utf-8"))
    target = ROOT / ".infra-local"
    records = []
    with httpx.Client(timeout=180, follow_redirects=True) as client:

        def download(url):
            response = client.get(url)
            response.raise_for_status()
            return response.content

        tf = versions["terraform"]
        base = f"https://releases.hashicorp.com/terraform/{tf}/"
        checksums = download(base + f"terraform_{tf}_SHA256SUMS").decode()
        for platform in ["windows", "linux"]:
            name = f"terraform_{tf}_{platform}_amd64.zip"
            expected = next(
                line.split()[0] for line in checksums.splitlines() if line.split()[-1] == name
            )
            content = download(base + name)
            actual = hashlib.sha256(content).hexdigest()
            if actual != expected:
                raise RuntimeError("Terraform checksum mismatch; no extraction")
            executable = "terraform.exe" if platform == "windows" else "terraform"
            directory = target / "bin" / platform
            directory.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(content)) as package:
                (directory / executable).write_bytes(package.read(executable))
            records.append(
                {
                    "tool": "terraform",
                    "platform": platform,
                    "version": tf,
                    "url": base + name,
                    "sha256": actual,
                }
            )
        uv = versions["uv"]
        uv_url = f"https://github.com/astral-sh/uv/releases/download/{uv}/uv-x86_64-unknown-linux-gnu.tar.gz"
        content = download(uv_url)
        expected = download(uv_url + ".sha256").decode().split()[0]
        actual = hashlib.sha256(content).hexdigest()
        if actual != expected:
            raise RuntimeError("uv checksum mismatch")
        with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as package:
            member = next(
                item
                for item in package.getmembers()
                if item.isfile() and Path(item.name).name == "uv"
            )
            (target / "bin/linux/uv").write_bytes(package.extractfile(member).read())
        records.append({"tool": "uv", "version": uv, "url": uv_url, "sha256": actual})
        for name, addon in versions["addons"].items():
            content = download(addon["url"])
            actual = hashlib.sha256(content).hexdigest()
            if actual != addon["sha256"]:
                raise RuntimeError("Addon checksum mismatch: " + name)
            path = target / "vendor" / (name + ".yaml")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            records.append({"tool": name, **addon})
        content = download(versions["kubernetes_schema"]["url"])
        if hashlib.sha256(content).hexdigest() != versions["kubernetes_schema"]["sha256"]:
            raise RuntimeError("Kubernetes schema checksum mismatch")
        (target / "vendor/kubernetes-swagger.json").write_bytes(content)
        for name, collection in versions["collections"].items():
            content = download(collection["url"])
            if hashlib.sha256(content).hexdigest() != collection["sha256"]:
                raise RuntimeError("Collection checksum mismatch: " + name)
            directory = target / "collection-artifacts"
            directory.mkdir(exist_ok=True)
            (directory / collection["filename"]).write_bytes(content)
            records.append({"tool": name, **collection})
    (target / "tool-checksums.json").write_text(
        json.dumps(records, indent=2) + "\n", encoding="utf-8"
    )
    if os.name != "nt":
        for path in (target / "bin/linux").iterdir():
            path.chmod(0o755)
    print("Verified Terraform Windows/Linux, uv Linux and pinned cert-manager/KEDA manifests")


if __name__ == "__main__":
    main()
