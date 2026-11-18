"""Run the SHA stack checker from this checkout against the dedicated CI engine."""

import argparse
import base64
import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path


def main():
    root = next(
        (
            p
            for p in Path(__file__).resolve().parents
            if (p / "Jenkinsfile").is_file() and (p / "pyproject.toml").is_file()
        ),
        Path.cwd(),
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("security_summary", type=Path)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    receipt = json.loads(args.security_summary.read_text(encoding="utf-8"))
    if not receipt.get("images") or any(
        item.get("critical") != 0 for item in receipt["images"].values()
    ):
        raise ValueError("Require an actual clean image scan summary")
    revision = receipt["commit"]
    if not re.fullmatch("[a-f0-9]{40}", revision):
        raise ValueError("Require a full source commit SHA before invoking Git")
    compose = subprocess.check_output(
        ["git", "-c", "safe.directory=" + root.as_posix(), "show", revision + ":compose.yaml"],
        cwd=root,
    )
    script = (root / "scripts/ci/verify-sha-stack.py").read_bytes()
    command = [
        "docker",
        "exec",
        "-i",
        "clinic-ci-agent-1",
        "python3",
        "-",
        "--revision",
        revision,
        "--registry",
        json.loads((root / "ci/tools.json").read_text(encoding="utf-8"))["registry"],
        "--compose-base64",
        base64.b64encode(compose).decode(),
        "--images-base64",
        base64.b64encode(json.dumps(receipt).encode()).decode(),
        "--verifier-sha256",
        hashlib.sha256(script).hexdigest(),
    ]
    output = args.evidence or root / "docs/evidence" / (
        "sha-runtime-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    )
    output.mkdir(parents=True, exist_ok=False)
    print("Checking five scanned SHA images in an isolated test project:", revision, flush=True)
    result = subprocess.run(command, input=script, cwd=root, capture_output=True, timeout=900)
    if result.stderr:
        (output / "launcher-stderr.log").write_bytes(result.stderr)
    try:
        data = json.loads(result.stdout.decode("utf-8").strip().splitlines()[-1])
    except (ValueError, IndexError):
        raise RuntimeError("Checker produced no JSON receipt; inspect launcher stderr") from None
    logs = data.pop("public_logs", {})
    for name, text in logs.items():
        if name not in {"up.log", "client.log", "cleanup.log"}:
            raise ValueError("Unexpected log filename")
        (output / name).write_text(text, encoding="utf-8", newline="\n")
    data["public_log_files"] = list(logs)
    data["launcher_exit_code"] = result.returncode
    (output / "metadata.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(
        "Runtime exit:",
        result.returncode,
        "cleanup:",
        data.get("cleanup_exit_code"),
        "evidence:",
        output,
        flush=True,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
