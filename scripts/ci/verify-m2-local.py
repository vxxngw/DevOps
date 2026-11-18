"""Record local checks only; never promote them to Jenkins/image/registry evidence."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = next(
    (
        p
        for p in Path(__file__).resolve().parents
        if (p / "Jenkinsfile").is_file() and (p / "pyproject.toml").is_file()
    ),
    Path.cwd(),
)


def main():
    os.chdir(ROOT)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = ROOT / "docs/evidence" / ("m2-local-" + stamp)
    destination.mkdir(parents=True)
    environment = os.environ.copy()
    environment["CLINIC_CI_PYTHON"] = sys.executable
    temporary = ROOT / ".ci-local/temp"
    temporary.mkdir(parents=True, exist_ok=True)
    environment.update(TEMP=str(temporary), TMP=str(temporary), TMPDIR=str(temporary))
    git = ["git", "-c", "safe.directory=" + ROOT.as_posix()]
    metadata = {
        "at_utc": datetime.now(UTC).isoformat(),
        "scope": "Native local checks; NOT Jenkins execution, image scan, registry publication or deployment",
        "head_commit": subprocess.check_output(git + ["rev-parse", "HEAD"], text=True).strip(),
        "working_tree": subprocess.check_output(git + ["status", "--short"], text=True),
        "checks": [],
    }
    sources = set()
    for folder in ["services", "tests", "scripts", "ci"]:
        sources.update((ROOT / folder).rglob("*.py"))
    for pattern in [
        "Jenkinsfile",
        "compose*.yaml",
        "requirements.lock",
        "pyproject.toml",
        "frontend/package*.json",
        "frontend/eslint.config.js",
        "frontend/src/**/*.ts*",
        "**/Dockerfile",
        "ci/**/*.yaml",
        "ci/**/*.groovy",
        "ci/controller/plugins*.json",
        "ci/controller/plugins.txt",
    ]:
        sources.update(ROOT.glob(pattern))
    metadata["files"] = [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in sorted(sources)
        if not any(
            part in {"tmp", ".venv", "node_modules", ".ci-local"}
            for part in path.relative_to(ROOT).parts
        )
    ]
    commands = [
        ("lint", [sys.executable, "-m", "ci.pipeline", "lint"], 0),
        ("unit", [sys.executable, "-m", "ci.pipeline", "unit"], 0),
        ("committed-history-secret-scan", [sys.executable, "-m", "ci.security", "secrets"], 0),
        ("dependency-scan", [sys.executable, "-m", "ci.security", "dependencies"], 0),
        ("negative-secret", [sys.executable, "-m", "ci.security", "demo-secret"], 1),
        ("negative-critical", [sys.executable, "-m", "ci.security", "demo-critical"], 1),
    ]
    successful = True
    for name, command, expected in commands:
        print("Checking", name, flush=True)
        result = subprocess.run(
            command,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1200,
        )
        (destination / (name + ".log")).write_text(result.stdout + result.stderr, encoding="utf-8")
        passed = result.returncode == expected
        if name.startswith("negative-"):
            filename = "gitleaks-result.json" if name == "negative-secret" else "trivy-result.json"
            receipt = ROOT / "ci-out/security-demo" / filename
            if not receipt.is_file():
                passed = False
            else:
                proof = json.loads(receipt.read_text(encoding="utf-8"))
                passed &= (
                    proof.get("scanner_exit") == 1
                    and (proof.get("findings", 0) + proof.get("critical", 0)) > 0
                )
        metadata["checks"].append(
            {
                "name": name,
                "exit_code": result.returncode,
                "expected_exit": expected,
                "verified": passed,
            }
        )
        successful &= passed
    for pattern in [
        "junit-unit.xml",
        "unit.log",
        "ruff.log",
        "format.log",
        "eslint.log",
        "frontend-build.log",
        "dependency-gate.json",
        "security/*.json",
        "security/*.log",
        "security-demo/*-result.json",
        "security-demo/*.json",
    ]:
        for path in (ROOT / "ci-out").glob(pattern):
            if path.name == "result.json":
                continue  # Obsolete scratch result from early investigation, not per-demo evidence.
            target = destination / "reports" / path.relative_to(ROOT / "ci-out")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    metadata["local_checks_passed"] = successful
    metadata["runtime_remaining"] = [
        "Activate Docker data on D and verify preserved data",
        "Build/run all five SHA images and scan them",
        "Protected dedicated Jenkins positive/negative builds",
        "Real GitHub push/PR webhook delivery",
        "GHCR push and pull-by-digest with write:packages credential",
        "Human review/semver release and available branch protection",
    ]
    (destination / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(destination, "LOCAL_PASS" if successful else "LOCAL_FAIL")
    return 0 if successful else 1


if __name__ == "__main__":
    raise SystemExit(main())
