"""Record real preparation checks; never provision VMs or infer runtime from static checks."""

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    os.chdir(ROOT)
    folder = ROOT / "docs/evidence" / ("m3-local-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"))
    folder.mkdir(parents=True)
    git = ["git", "-c", "safe.directory=" + ROOT.as_posix()]
    paths = subprocess.check_output(
        git + ["ls-files", "--cached", "--others", "--exclude-standard"], text=True
    ).splitlines()
    sources = sorted(
        {
            ROOT / name
            for name in paths
            if name.startswith(("ci/", "infra/", "deploy/", "scripts/", "services/"))
            and name.endswith(
                (".py", ".sh", ".tf", ".json", ".yml", ".yaml", ".lock", ".txt", ".j2")
            )
        }
        | {
            ROOT / "Jenkinsfile",
            ROOT / "compose.ci.yaml",
            ROOT / "compose.ci.vm.yaml",
            ROOT / ".dockerignore",
        }
    )
    metadata = {
        "at_utc": datetime.now(UTC).isoformat(),
        "scope": "Local preparation only: static checks, unit tests, scanner and actual host preflight. No VM apply, Ansible convergence, cluster deploy, trusted HTTPS, scale, backup/restore or rollback runtime claim",
        "head_commit": subprocess.check_output(git + ["rev-parse", "HEAD"], text=True).strip(),
        "working_tree": subprocess.check_output(git + ["status", "--short"], text=True),
        "files": [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in sources
            if path.is_file()
        ],
        "checks": [],
    }
    commands = [
        ("ruff", [sys.executable, "-m", "ruff", "check", "ci", "scripts", "services", "tests"]),
        (
            "format",
            [
                sys.executable,
                "-m",
                "ruff",
                "format",
                "--check",
                "ci",
                "scripts",
                "services",
                "tests",
            ],
        ),
        (
            "unit",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests",
                "ci/tests",
                "--basetemp=.infra-local/pytest-final",
                "--junitxml=ci-out/junit-m3-unit.xml",
            ],
        ),
        ("infrastructure", [sys.executable, "-m", "ci.infrastructure"]),
        (
            "ansible-bash-host",
            [
                "wsl",
                "-d",
                "Ubuntu-22.04",
                "-e",
                "bash",
                "/mnt/d/CODE/OOPs/Do_An/scripts/check-infra-control.sh",
            ]
            if platform.system() == "Windows"
            else ["bash", "scripts/check-infra-control.sh"],
        ),
        ("dependencies", [sys.executable, "-m", "ci.security", "dependencies"]),
        ("committed-history-secrets", [sys.executable, "-m", "ci.security", "secrets"]),
    ]
    passed = True
    for name, command in commands:
        print("Checking", name, flush=True)
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1200,
        )
        (folder / (name + ".log")).write_text(result.stdout + result.stderr, encoding="utf-8")
        metadata["checks"].append(
            {"name": name, "exit_code": result.returncode, "passed": result.returncode == 0}
        )
        passed &= result.returncode == 0
    try:
        response = httpx.post(
            "http://127.0.0.1:8080/pipeline-model-converter/validate",
            data={"jenkinsfile": (ROOT / "Jenkinsfile").read_text()},
            timeout=15,
            trust_env=False,
        )
        valid = (
            response.status_code == 200 and "Jenkinsfile successfully validated" in response.text
        )
        (folder / "jenkins-parser.log").write_text(
            "Existing8080parser only; no auth/credentials sent, no jobs changed.\nHTTP"
            + str(response.status_code)
            + "\n"
            + response.text,
            encoding="utf-8",
        )
        metadata["jenkins_parser"] = "VERIFIED_PARSE_ONLY" if valid else "FAILED_OR_BLOCKED"
        if response.status_code == 200 and not valid:
            passed = False
    except httpx.HTTPError as error:
        metadata["jenkins_parser"] = "BLOCKED:" + type(error).__name__
    artifacts = [
        ROOT / "ci-out/junit-m3-unit.xml",
        ROOT / "ci-out/dependency-gate.json",
        ROOT / "ci-out/security/trivy-dependencies.json",
        ROOT / "ci-out/security/trivy-dependencies.log",
        ROOT / "ci-out/security/gitleaks.json",
        ROOT / "ci-out/security/gitleaks.log",
        ROOT / ".infra-local/preflight.json",
        ROOT / ".infra-local/tool-checksums.json",
    ]
    artifacts += list((ROOT / "ci-out/infra").glob("*"))
    for path in artifacts:
        if path.is_file():
            relative = path.relative_to(ROOT)
            destination = folder / "reports" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
    if (ROOT / ".infra-local/preflight.json").exists():
        metadata["vm_host_preflight"] = json.loads(
            (ROOT / ".infra-local/preflight.json").read_text()
        )["status"]
    metadata["local_checks_passed"] = passed
    metadata["runtime_status"] = "NOT_RUN"
    metadata["registry_token_present"] = (ROOT / ".registry-token").is_file()
    (folder / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (ROOT / "docs/evidence/m3-latest.json").write_text(
        json.dumps(
            {
                "latest": folder.name + "/metadata.json",
                "scope": "Preparation checks only",
                "local_checks_passed": passed,
                "runtime_status": "NOT_RUN",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(folder, "LOCAL_PASS" if passed else "LOCAL_FAIL", "runtime NOT_RUN", flush=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
