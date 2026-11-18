"""Record real command outputs with metadata and secret redaction. No fabricated pass results."""

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--integration", action="store_true")
    args = parser.parse_args()
    root = next(
        (
            p
            for p in Path(__file__).resolve().parents
            if (p / "Jenkinsfile").is_file() and (p / "pyproject.toml").is_file()
        ),
        Path.cwd(),
    )
    os.chdir(root)
    folder = root / "docs" / "evidence" / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    folder.mkdir(parents=True, exist_ok=False)
    git = ["git", "-c", "safe.directory=" + root.as_posix()]
    commit = subprocess.run(git + ["rev-parse", "HEAD"], capture_output=True, text=True)
    metadata = {
        "started_at_utc": datetime.now(UTC).isoformat(),
        "host": platform.platform(),
        "commit": commit.stdout.strip() if commit.returncode == 0 else "UNCOMMITTED",
        "working_tree": subprocess.run(
            git + ["status", "--short"], capture_output=True, text=True
        ).stdout,
        "scope": "PostgreSQL/RabbitMQ/Mailpit integration"
        if args.integration
        else "SQLite API, application and CI unit tests; external dependency cases may skip",
        "commands": [],
    }
    # Hash source state without storing .env or node_modules, even before the first commit.
    source_paths = sorted(
        set(root.glob("services/**/*.py"))
        | set(root.glob("tests/**/*.py"))
        | set(root.glob("ci/**/*.py"))
        | set(root.glob("contracts/*.json"))
        | {root / "compose.yaml", root / "requirements.lock"}
    )
    metadata["source_sha256"] = {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in source_paths
        if path.is_file()
    }
    commands = [
        ("pip-check", [sys.executable, "-m", "pip", "check"]),
        ("ruff", [sys.executable, "-m", "ruff", "check", "services", "tests", "scripts"]),
        (
            "format",
            [sys.executable, "-m", "ruff", "format", "--check", "services", "tests", "scripts"],
        ),
        (
            "pytest",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "--tb=short",
                "--junitxml=" + str(folder / "junit.xml"),
            ],
        ),
    ]
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    if args.integration:
        from dotenv import dotenv_values

        env["TEST_DATABASE_URL"] = dotenv_values(".env")["DATABASE_URL"]
        env["RUN_BROKER_TESTS"] = "1"
    else:
        env.pop("TEST_DATABASE_URL", None)
        env.pop("RUN_BROKER_TESTS", None)
    failed = False
    for name, command in commands:
        started = datetime.now(UTC).isoformat()
        try:
            result = subprocess.run(
                command,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )
        except subprocess.TimeoutExpired as exc:
            previous = exc.stdout or b""
            previous = (
                previous.decode("utf-8", errors="replace")
                if isinstance(previous, bytes)
                else previous
            )
            result = subprocess.CompletedProcess(
                command, 124, previous, "\nTIMEOUT after 120 seconds\n"
            )
        output = result.stdout + result.stderr
        output = re.sub(
            r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+", "[REDACTED_JWT]", output
        )
        output = re.sub(
            r"(postgresql(?:\+psycopg)?|amqps?)://[^\s'\"]+", r"\1://[REDACTED]", output
        )
        (folder / f"{name}.log").write_text(output, encoding="utf-8")
        metadata["commands"].append(
            {
                "command": command,
                "started_at_utc": started,
                "ended_at_utc": datetime.now(UTC).isoformat(),
                "exit_code": result.returncode,
                "output": f"{name}.log",
            }
        )
        print(f"{name}: exit {result.returncode}")
        failed |= result.returncode != 0
    metadata["ended_at_utc"] = datetime.now(UTC).isoformat()
    (folder / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Evidence:", folder.relative_to(root))
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
