import argparse
import hashlib
import os
import secrets as random_secrets
import shutil
import string
import subprocess
from pathlib import Path

from ci.common import (
    IMAGES,
    OUTPUT,
    PRIVATE,
    ROOT,
    TOOLS,
    commit,
    now,
    read_json,
    run,
    tool,
    write_json,
)


def critical_findings(report):
    if (
        not isinstance(report, dict)
        or not isinstance(report.get("Results"), list)
        or not report["Results"]
    ):
        raise ValueError("Missing or empty scanner result structure; not a clean scan")
    return [
        vulnerability
        for result in report["Results"]
        for vulnerability in result.get("Vulnerabilities") or []
        if vulnerability.get("Severity") == "CRITICAL"
    ]


def check_version(name):
    version = run([tool(name), "version" if name == "gitleaks" else "--version"]).stdout
    expected = TOOLS[name]["version"]
    if expected not in version:
        raise RuntimeError(f"Expected {name}{expected}; refusing a different scanner version")


def secrets_scan():
    check_version("gitleaks")
    report = OUTPUT / "security/gitleaks.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.unlink(missing_ok=True)
    (OUTPUT / "secret-gate.json").unlink(missing_ok=True)
    environment = os.environ.copy()
    environment.update(
        GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="safe.directory", GIT_CONFIG_VALUE_0=ROOT.as_posix()
    )
    result = run(
        [
            tool("gitleaks"),
            "git",
            str(ROOT),
            "--log-opts=--all",
            "--config",
            ROOT / ".gitleaks.toml",
            "--redact",
            "--no-banner",
            "--report-format",
            "json",
            "--report-path",
            report,
        ],
        env=environment,
        check=False,
        log=OUTPUT / "security/gitleaks.log",
    )
    findings = read_json(
        report
    )  # A missing/corrupt report is a failure, including scanner outages.
    if result.returncode or not isinstance(findings, list) or findings:
        raise RuntimeError("Secret gate failed; inspect the redacted Gitleaks report")
    write_json(
        OUTPUT / "secret-gate.json",
        {
            "commit": commit(),
            "at_utc": now(),
            "scanner": TOOLS["gitleaks"],
            "findings": 0,
            "report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
        },
    )


def trivy(target, report, *, source="image", remote=False):
    check_version("trivy")
    PRIVATE.mkdir(exist_ok=True, mode=0o700)
    ignore = PRIVATE / "empty-trivy-ignore"
    ignore.write_text("", encoding="utf-8")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.unlink(missing_ok=True)
    cache = Path(os.environ.get("TRIVY_CACHE_DIR", str(PRIVATE / "trivy-cache")))
    command = [
        tool("trivy"),
        source,
        "--cache-dir",
        cache,
        "--scanners",
        "vuln",
        "--severity",
        "CRITICAL",
        "--exit-code",
        "1",
        "--ignorefile",
        ignore,
        "--format",
        "json",
        "--output",
        report,
    ]
    if remote:
        command += ["--image-src", "remote"]
    if source == "fs":
        command += ["--include-dev-deps"]
        for directory in [".git", ".ci-local", "ci-out", "tmp", ".venv", "frontend/node_modules"]:
            command += ["--skip-dirs", ROOT / directory]
    env = os.environ.copy()
    env["TRIVY_IGNORE_UNFIXED"] = "false"
    result = run(command + [target], env=env, check=False, log=report.with_suffix(".log"))
    if not report.is_file():
        raise RuntimeError("Trivy produced no report; inspect the scanner log. Gate is BLOCKED")
    parsed = read_json(report)
    findings = critical_findings(parsed)
    return result, parsed, findings


def images():
    (OUTPUT / "security-summary.json").unlink(missing_ok=True)
    built = read_json(OUTPUT / "built-images.json")
    revision = commit()
    if built["commit"] != revision or set(built["images"]) != set(IMAGES):
        raise ValueError("Build record does not match the checkout and complete image set")
    records = {}
    for name, item in built["images"].items():
        report = OUTPUT / "security" / ("trivy-" + name + ".json")
        result, parsed, findings = trivy(item["tag"], report)
        if result.returncode or findings:
            raise RuntimeError(
                f"Trivy gate failed for {name}; CRITICAL findings or scanner failure"
            )
        if parsed.get("Metadata", {}).get("ImageID") != item["image_id"]:
            raise RuntimeError("Scanner did not inspect the expected image ID")
        records[name] = {
            **item,
            "critical": 0,
            "report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
        }
    dependency = dependencies()
    write_json(
        OUTPUT / "security-summary.json",
        {
            "commit": revision,
            "at_utc": now(),
            "scanner": TOOLS["trivy"],
            "ignore_unfixed": False,
            "ignorefile": "empty",
            "images": records,
            "dependency_report_sha256": dependency["report_sha256"],
            "dependency_inputs": dependency["inputs"],
        },
    )


def dependencies():
    (OUTPUT / "dependency-gate.json").unlink(missing_ok=True)
    inputs = PRIVATE / "dependency-input"
    (inputs / "frontend").mkdir(parents=True, exist_ok=True)
    checksums = {}
    # Trivy recognizes requirements.txt, but not this repository's requirements.lock.
    # Copy the exact pinned bytes under the recognized name; never resolve new versions.
    for original, target in [
        ("requirements.lock", "requirements.txt"),
        ("frontend/package.json", "frontend/package.json"),
        ("frontend/package-lock.json", "frontend/package-lock.json"),
        ("infra/requirements-ansible.lock", "infra-control/requirements.txt"),
        ("infra/requirements-static.txt", "infra-static/requirements.txt"),
    ]:
        (inputs / target).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / original, inputs / target)
        checksums[original] = hashlib.sha256((ROOT / original).read_bytes()).hexdigest()
    report = OUTPUT / "security/trivy-dependencies.json"
    result, parsed, findings = trivy(str(inputs), report, source="fs")
    if result.returncode or findings:
        raise RuntimeError("Dependency gate failed; this is separate from container image scans")
    if not {"pip", "npm"}.issubset({item.get("Type") for item in parsed["Results"]}):
        raise RuntimeError("Dependency scan must inspect both Python and Node lockfiles")
    receipt = {
        "inputs": checksums,
        "report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
    }
    write_json(OUTPUT / "dependency-gate.json", {"commit": commit(), "at_utc": now(), **receipt})
    print(
        "Python/Node dependency scan passed, including dev dependencies; image scans are separate"
    )
    return receipt


def demo_secret():
    check_version("gitleaks")
    report = OUTPUT / "security-demo/gitleaks.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "security-demo/gitleaks-result.json").unlink(missing_ok=True)
    report.unlink(missing_ok=True)
    fake = "ghp_" + "".join(
        random_secrets.choice(string.ascii_letters + string.digits) for _ in range(36)
    )
    result = run(
        [
            tool("gitleaks"),
            "stdin",
            "--config",
            ROOT / ".gitleaks.toml",
            "--redact",
            "--no-banner",
            "--report-format",
            "json",
            "--report-path",
            report,
        ],
        input_text="demo_only_token=" + fake + "\n",
        check=False,
        log=report.with_suffix(".log"),
    )
    findings = read_json(report)
    if result.returncode != 1 or not isinstance(findings, list) or not findings:
        raise RuntimeError(
            "Negative demo did not produce a real finding; cannot claim the gate worked"
        )
    write_json(
        OUTPUT / "security-demo/gitleaks-result.json",
        {
            "kind": "generated synthetic token, never a real credential",
            "scanner_exit": result.returncode,
            "findings": len(findings),
            "at_utc": now(),
            "scope": "Scanner invocation; Jenkins failed-build evidence is separate",
        },
    )
    raise subprocess.CalledProcessError(result.returncode, result.args)


def demo_critical():
    report = OUTPUT / "security-demo/trivy.json"
    (OUTPUT / "security-demo/trivy-result.json").unlink(missing_ok=True)
    result, _, findings = trivy("docker.io/library/alpine:3.12.0", report, remote=True)
    if result.returncode != 1 or not findings:
        raise RuntimeError(
            "Negative demo requires real CRITICAL findings, not a scanner/network error"
        )
    write_json(
        OUTPUT / "security-demo/trivy-result.json",
        {
            "kind": "Known old upstream Alpine image, remote scan; never a release image",
            "scanner_exit": result.returncode,
            "critical": len(findings),
            "at_utc": now(),
            "scope": "Scanner invocation; Jenkins failed-build evidence is separate",
        },
    )
    raise subprocess.CalledProcessError(result.returncode, result.args)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", choices=["secrets", "dependencies", "images", "demo-secret", "demo-critical"]
    )
    action = parser.parse_args().action
    {
        "secrets": secrets_scan,
        "images": images,
        "dependencies": dependencies,
        "demo-secret": demo_secret,
        "demo-critical": demo_critical,
    }[action]()


if __name__ == "__main__":
    main()
