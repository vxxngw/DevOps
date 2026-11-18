"""Capture non-secret runtime facts and source hashes; no config/env/credential dumps."""

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import httpx

root = next(
    (
        p
        for p in Path(__file__).resolve().parents
        if (p / "Jenkinsfile").is_file() and (p / "pyproject.toml").is_file()
    ),
    Path.cwd(),
)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--brief", type=Path, help="Optional original brief used for source provenance")
parser.add_argument("--assignment-pdf", type=Path, help="Optional original assignment PDF")
args = parser.parse_args()
for document in [args.brief, args.assignment_pdf]:
    if document is not None and not document.is_file():
        parser.error(f"Document does not exist: {document}")
folder = root / "docs/evidence" / ("inspection-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"))
folder.mkdir(parents=True)
metadata = {
    "at_utc": datetime.now(UTC).isoformat(),
    "commit": "UNCOMMITTED",
    "commands": [],
    "http": [],
}
commands = [
    ["docker", "version"],
    ["docker", "compose", "version"],
    ["docker", "compose", "config", "--quiet"],
    ["docker", "compose", "ps", "-a"],
    ["git", "-c", "safe.directory=" + root.as_posix(), "status", "--short"],
]
for image in [
    "clinic-app:dev",
    "clinic-frontend:dev",
    "clinic-postgres:dev",
    "clinic-rabbitmq:dev",
    "axllent/mailpit:v1.27.10",
]:
    commands.append(
        [
            "docker",
            "image",
            "inspect",
            image,
            "--format",
            '{{.Id}} user={{index .Config "User"}} health={{json (index .Config "Healthcheck")}}',
        ]
    )
for service in ["api", "publisher", "worker", "postgres", "rabbitmq"]:
    commands.append(["docker", "compose", "exec", "-T", service, "id"])
for service in ["api", "publisher", "worker"]:
    commands.append(["docker", "logs", "--tail", "100", f"clinic-dev-{service}-1"])
    commands.append(
        [
            "docker",
            "inspect",
            f"clinic-dev-{service}-1",
            "--format",
            "user={{.Config.User}} log_driver={{.HostConfig.LogConfig.Type}} cap_drop={{json .HostConfig.CapDrop}} security_opt={{json .HostConfig.SecurityOpt}}",
        ]
    )
commands.append(
    [
        "docker",
        "compose",
        "exec",
        "-T",
        "worker",
        "python",
        "-c",
        "from clinic.config import settings; print('worker_delay_seconds=', settings().worker_delay_seconds)",
    ]
)
for index, command in enumerate(commands):
    try:
        result = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
        filename = f"command-{index:02d}.log"
        (folder / filename).write_text(result.stdout + result.stderr, encoding="utf-8")
        metadata["commands"].append(
            {"command": command, "exit_code": result.returncode, "output": filename}
        )
    except subprocess.TimeoutExpired:
        metadata["commands"].append({"command": command, "status": "TIMEOUT"})
for port in [8000, 8001, 8002]:
    for endpoint in ["health", "ready", "metrics"]:
        url = f"http://localhost:{port}/{endpoint}"
        try:
            response = httpx.get(url, timeout=5, trust_env=False)
            filename = f"{port}-{endpoint}.txt"
            (folder / filename).write_text(response.text, encoding="utf-8")
            metadata["http"].append(
                {"url": url, "status": response.status_code, "output": filename}
            )
        except httpx.HTTPError as exc:
            metadata["http"].append({"url": url, "error_type": type(exc).__name__})
for endpoint in ["metrics", "metrics/per-object"]:
    response = httpx.get("http://localhost:15693/" + endpoint, timeout=5, trust_env=False)
    filename = "rabbitmq-" + endpoint.replace("/", "-") + ".txt"
    (folder / filename).write_text(response.text, encoding="utf-8")
    metadata["http"].append(
        {
            "url": "http://localhost:15693/" + endpoint,
            "status": response.status_code,
            "output": filename,
        }
    )
for result in metadata["commands"]:
    if result["command"][:2] == ["docker", "logs"] and "output" in result:
        lines = (folder / result["output"]).read_text(encoding="utf-8").splitlines()
        parsed = 0
        for line in lines:
            try:
                json.loads(line)
                parsed += 1
            except json.JSONDecodeError:
                pass
        metadata.setdefault("json_log_validation", []).append(
            {"service": result["command"][-1], "lines": len(lines), "json_lines": parsed}
        )
for filename in [
    "compose-dns-fix.log",
    "compose-plugins.log",
    "dependencies-alpine.log",
    "dependencies-run.log",
]:
    source = root / "tmp" / filename
    if source.exists():
        (folder / filename).write_bytes(source.read_bytes())
        metadata.setdefault("historical_logs", []).append(
            {
                "file": filename,
                "source_mtime_utc": datetime.fromtimestamp(source.stat().st_mtime, UTC).isoformat(),
                "note": "Original earlier command output; read log/evidence index for success or failure",
            }
        )
for label, source in [
    ("brief", args.brief),
    ("pdf", args.assignment_pdf),
]:
    if source is None:
        metadata[label] = {"status": "NOT_PROVIDED"}
        continue
    metadata[label] = {
        "filename": source.name,
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }
metadata["source_sha256"] = {}
for pattern in [
    "services/**/*.py",
    "tests/**/*.py",
    "contracts/*.json",
    "frontend/src/**/*",
    "*compose*.yaml",
    "requirements.lock",
    "frontend/package-lock.json",
    "images/**/*",
    "frontend/Dockerfile",
    "frontend/nginx.conf",
    "scripts/**/*.py",
    "scripts/**/*.ps1",
]:
    for source in root.glob(pattern):
        if source.is_file():
            metadata["source_sha256"][str(source.relative_to(root))] = hashlib.sha256(
                source.read_bytes()
            ).hexdigest()
(folder / "metadata.json").write_text(
    json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("Runtime inspection evidence:", folder.relative_to(root))
