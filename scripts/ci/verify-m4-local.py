"""Record bounded preparation evidence without promoting fixtures to runtime acceptance."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx


def main():
    root = next(
        (
            p
            for p in Path(__file__).resolve().parents
            if (p / "Jenkinsfile").is_file() and (p / "pyproject.toml").is_file()
        ),
        Path.cwd(),
    )
    sys.path.insert(0, str(root))
    from ci.paths import wsl_bash

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = root / "docs/evidence" / ("m4-local-" + stamp)
    destination.mkdir(parents=True)
    python = str(root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
    paths = [
        path
        for directory in ["ci", "services", "scripts", "infra", "deploy", "observability"]
        for path in (root / directory).rglob("*")
        if path.is_file()
        and not any(part in path.parts for part in [".terraform", "__pycache__"])
        and path.suffix
        in {".py", ".sh", ".tf", ".json", ".yaml", ".yml", ".j2", ".txt", ".lock", ".conf"}
    ]
    paths += [
        root / name
        for name in ["Jenkinsfile", "ci/agent/Dockerfile", "frontend/nginx.conf", ".dockerignore"]
    ]
    sources = {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(set(paths))
    }
    git = ["git", "-c", "safe.directory=" + root.as_posix()]
    head = subprocess.check_output(git + ["rev-parse", "HEAD"], cwd=root, text=True).strip()
    checks = []
    env = os.environ.copy()
    temporary = root / ".ci-local/temp"
    temporary.mkdir(parents=True, exist_ok=True)
    env.update(
        TMP=str(temporary), TEMP=str(temporary), TMPDIR=str(temporary), PYTHONIOENCODING="utf-8"
    )
    for variable in ["TEST_DATABASE_URL", "RUN_BROKER_TESTS", "DATABASE_URL"]:
        env.pop(variable, None)
    commands = [
        (
            "ruff",
            [python, "-m", "ruff", "check", "services", "tests", "scripts", "ci", "observability"],
        ),
        (
            "format",
            [
                python,
                "-m",
                "ruff",
                "format",
                "--check",
                "services",
                "tests",
                "scripts",
                "ci",
                "observability",
            ],
        ),
        (
            "unit",
            [
                python,
                "-m",
                "pytest",
                "-q",
                "tests",
                "ci/tests",
                "--tb=short",
                "--junitxml=" + str(destination / "junit.xml"),
            ],
        ),
        ("observability", [python, "-m", "ci.observability"]),
        ("infrastructure", [python, "-m", "ci.infrastructure"]),
        ("dependencies", [python, "-m", "ci.security", "dependencies"]),
    ]
    for name, command in commands:
        result = subprocess.run(command, cwd=root, env=env, capture_output=True, timeout=600)
        (destination / (name + ".log")).write_bytes(result.stdout + result.stderr)
        checks.append({"name": name, "command": command, "exit_code": result.returncode})
        print(name, result.returncode, flush=True)
    preflight = root / ".infra-local/preflight.json"
    preflight.unlink(missing_ok=True)
    if os.name == "nt":
        command = wsl_bash(root / "scripts/infra/check-infra-control.sh")
    else:
        command = ["bash", "scripts/infra/check-infra-control.sh"]
    result = subprocess.run(command, cwd=root, env=env, capture_output=True, timeout=180)
    (destination / "ansible-bash-vault.log").write_bytes(result.stdout + result.stderr)
    checks.append(
        {"name": "ansible-bash-vault", "exit_code": result.returncode, "command": command}
    )
    print("ansible-bash-vault", result.returncode, flush=True)
    if preflight.is_file():
        shutil.copyfile(preflight, destination / "preflight.json")
    parser_status = "NOT_RUN"
    try:
        response = httpx.post(
            "http://127.0.0.1:8080/pipeline-model-converter/validate",
            data={"jenkinsfile": (root / "Jenkinsfile").read_text()},
            timeout=5,
        )
        if response.status_code == 200:
            result = response.json()
            parser_status = (
                "PASSED" if result.get("data", {}).get("result") == "success" else "FAILED"
            )
            (destination / "jenkins-parser.json").write_text(
                json.dumps(result, indent=2), encoding="utf-8"
            )
        else:
            parser_status = "BLOCKED:HTTP" + str(response.status_code)
    except (httpx.HTTPError, ValueError) as exc:
        parser_status = "BLOCKED:" + type(exc).__name__
    for name in ["observability", "infra"]:
        if (root / "ci-out" / name).is_dir():
            shutil.copytree(root / "ci-out" / name, destination / name)
    changed = [
        name
        for name, digest in sources.items()
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest
    ]
    passed = all(check["exit_code"] == 0 for check in checks) and not changed
    metadata = {
        "at_utc": datetime.now(UTC).isoformat(),
        "head_commit": head,
        "source_scope": "Working tree before commit, identified by source hashes",
        "files": [{"path": name, "sha256": digest} for name, digest in sources.items()],
        "checks": checks,
        "source_changed_during_checks": changed,
        "local_checks_passed": passed,
        "jenkins_parser": parser_status,
        "runtime_status": "NOT_RUN",
        "fluentd_parser": "NOT_RUN",
        "operator_image_scan": "NOT_RUN",
        "external_alert_delivery": "BLOCKED: no configured real receiver or cluster",
        "scope": "Local parser, schema, policy, unit and synthetic rule/Vault fixture checks only; no VM, stack, dashboard UI, external notification, HPA/KEDA, load, backup or rollback acceptance.",
    }
    (destination / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    pointer = {
        "path": destination.relative_to(root).as_posix(),
        "local_checks_passed": passed,
        "runtime_status": "NOT_RUN",
        "jenkins_parser": parser_status,
    }
    (root / "docs/evidence/m4-latest.json").write_text(
        json.dumps(pointer, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(pointer), flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
