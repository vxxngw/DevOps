"""Download pinned scanner binaries to the workspace and verify upstream SHA256 checksums."""

import argparse
import hashlib
import io
import json
import os
import platform
import re
import tarfile
import zipfile
from pathlib import Path

import httpx


def install(name, version, destination):
    repository = {"gitleaks": "gitleaks/gitleaks", "trivy": "aquasecurity/trivy"}[name]
    windows = platform.system() == "Windows"
    if platform.machine().lower() not in {"amd64", "x86_64"}:
        raise RuntimeError("This installer supports amd64; use the pinned CI image on other hosts")
    patterns = {
        ("gitleaks", True): r"_windows_x64\.zip$",
        ("gitleaks", False): r"_linux_x64\.tar\.gz$",
        ("trivy", True): r"_windows-64bit\.zip$",
        ("trivy", False): r"_Linux-64bit\.tar\.gz$",
    }
    executable = name + (".exe" if windows else "")
    with httpx.Client(timeout=180, follow_redirects=True, trust_env=False) as client:
        response = client.get(f"https://api.github.com/repos/{repository}/releases/tags/v{version}")
        response.raise_for_status()
        assets = response.json()["assets"]
        archive = next(
            asset for asset in assets if re.search(patterns[name, windows], asset["name"])
        )
        checksums = next(asset for asset in assets if asset["name"].endswith("checksums.txt"))
        checksum_response = client.get(checksums["browser_download_url"])
        checksum_response.raise_for_status()
        expected = next(
            line.split()[0]
            for line in checksum_response.text.splitlines()
            if line.split()[-1].lstrip("*") == archive["name"]
        )
        archive_response = client.get(archive["browser_download_url"])
        archive_response.raise_for_status()
        content = archive_response.content
    actual = hashlib.sha256(content).hexdigest()
    if actual.lower() != expected.lower():
        raise RuntimeError(f"Checksum mismatch for {name}; nothing installed")
    if windows:
        with zipfile.ZipFile(io.BytesIO(content)) as package:
            binary = package.read(
                next(member for member in package.namelist() if Path(member).name == executable)
            )
    else:
        with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as package:
            member = next(
                item
                for item in package.getmembers()
                if Path(item.name).name == executable and item.isfile()
            )
            binary = package.extractfile(member).read()
    # Extract only the exact executable, never arbitrary archive paths.
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / executable
    target.write_bytes(binary)
    if not windows:
        target.chmod(0o755)
    return {
        "name": name,
        "version": version,
        "archive": archive["name"],
        "archive_sha256": actual,
        "binary_sha256": hashlib.sha256(binary).hexdigest(),
        "source": archive["browser_download_url"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", default=".ci-local/bin")
    args = parser.parse_args()
    root = next(
        (
            p
            for p in Path(__file__).resolve().parents
            if (p / "Jenkinsfile").is_file() and (p / "pyproject.toml").is_file()
        ),
        Path.cwd(),
    )
    destination = (root / args.destination).resolve()
    destination.relative_to(root)  # Keep managed binaries inside the workspace.
    versions = json.loads((root / "ci/tools.json").read_text(encoding="utf-8"))
    results = [
        install(name, versions[name]["version"], destination) for name in ("gitleaks", "trivy")
    ]
    (destination / "checksums.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    for item in results:
        print(
            f"Verified {item['name']} {item['version']} SHA256; installed in {os.path.relpath(destination, root)}"
        )


if __name__ == "__main__":
    main()
