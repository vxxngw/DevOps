"""Install checksum-verified Prometheus/Alertmanager tools in the ignored D workspace cache."""

import argparse
import hashlib
import json
import os
import tarfile
import urllib.request
import zipfile
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--versions", type=Path, default=root / "observability/versions.json")
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--cache", type=Path, default=root / ".infra-local/downloads")
    parser.add_argument("--tools-only", action="store_true")
    args = parser.parse_args()
    versions = json.loads(args.versions.read_text(encoding="utf-8"))
    system = "windows" if os.name == "nt" else "linux"
    destination = args.destination or root / ".infra-local/observability" / system
    destination.mkdir(parents=True, exist_ok=True)
    cache = args.cache
    cache.mkdir(parents=True, exist_ok=True)
    for name, metadata in versions["tools"].items():
        asset = metadata["assets"][system]
        archive = cache / asset["url"].rsplit("/", 1)[-1]
        if not archive.exists():
            temporary = archive.with_suffix(archive.suffix + ".part")
            with urllib.request.urlopen(asset["url"], timeout=120) as response:
                with temporary.open("wb") as output:
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
            temporary.replace(archive)
        with archive.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != asset["sha256"]:
                raise ValueError("Archive checksum mismatch: " + archive.name)
        binaries = (
            ["prometheus", "promtool"] if name == "prometheus" else ["alertmanager", "amtool"]
        )
        if args.tools_only:
            binaries = binaries[1:]
        for binary in binaries:
            filename = binary + (".exe" if system == "windows" else "")
            if system == "windows":
                with zipfile.ZipFile(archive) as bundle:
                    member = next(
                        item for item in bundle.namelist() if item.endswith("/" + filename)
                    )
                    content = bundle.read(member)
            else:
                with tarfile.open(archive) as bundle:
                    member = next(
                        item for item in bundle.getmembers() if item.name.endswith("/" + filename)
                    )
                    content = bundle.extractfile(member).read()
            path = destination / filename
            path.write_bytes(content)
            path.chmod(0o755)
        print(name, metadata["version"], "archive SHA256 verified")


if __name__ == "__main__":
    main()
