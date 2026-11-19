import argparse
import hashlib
import os
import re
import secrets
import subprocess
import sys
import uuid
from pathlib import Path

from ci.common import (
    IMAGES,
    OUTPUT,
    PRIVATE,
    ROOT,
    TOOLS,
    commit,
    image,
    now,
    python_executable,
    run,
    write_json,
)


def prepare():
    PRIVATE.mkdir(exist_ok=True, mode=0o700)
    if not Path(python_executable()).is_file():
        run([sys.executable, "-m", "venv", PRIVATE / "venv"])
    run(
        [
            python_executable(),
            "-m",
            "pip",
            "install",
            "--cache-dir",
            PRIVATE / "pip-cache",
            "-r",
            "requirements.lock",
        ],
        log=OUTPUT / "install-python.log",
    )
    run(
        [
            python_executable(),
            "-m",
            "pip",
            "install",
            "--cache-dir",
            PRIVATE / "pip-cache",
            "-r",
            "infra/requirements-static.txt",
        ],
        log=OUTPUT / "install-infra-python.log",
    )
    npm = "npm.cmd" if os.name == "nt" else "npm"
    run(
        [
            npm,
            "ci",
            "--cache",
            PRIVATE / "npm-cache",
            "--ignore-scripts",
            "--no-fund",
            "--no-audit",
        ],
        cwd=ROOT / "frontend",
        log=OUTPUT / "install-node.log",
    )


def lint():
    run(
        [
            python_executable(),
            "-m",
            "ruff",
            "check",
            "services",
            "tests",
            "scripts",
            "ci",
            "observability",
        ],
        log=OUTPUT / "ruff.log",
    )
    run(
        [
            python_executable(),
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
        log=OUTPUT / "format.log",
    )
    npm = "npm.cmd" if os.name == "nt" else "npm"
    run([npm, "run", "lint"], cwd=ROOT / "frontend", log=OUTPUT / "eslint.log")
    run([npm, "run", "build"], cwd=ROOT / "frontend", log=OUTPUT / "frontend-build.log")


def unit():
    (OUTPUT / "unit-metadata.json").unlink(missing_ok=True)
    env = os.environ.copy()
    for name in ("TEST_DATABASE_URL", "RUN_BROKER_TESTS", "DATABASE_URL"):
        env.pop(name, None)
    run(
        [
            python_executable(),
            "-m",
            "pytest",
            "-q",
            "tests",
            "ci/tests",
            "--tb=short",
            "--junitxml=" + str(OUTPUT / "junit-unit.xml"),
        ],
        env=env,
        log=OUTPUT / "unit.log",
    )
    write_json(
        OUTPUT / "unit-metadata.json",
        {
            "commit": commit(),
            "test_exit_code": 0,
            "at_utc": now(),
            "report_sha256": hashlib.sha256((OUTPUT / "junit-unit.xml").read_bytes()).hexdigest(),
            "scope": "Unit suite; dependency integration tests may skip here, never in integration stage",
        },
    )


def build():
    revision = commit()
    dirty = run(
        [
            "git",
            "-c",
            "safe.directory=" + ROOT.as_posix(),
            "status",
            "--porcelain",
            "--untracked-files=all",
        ]
    ).stdout.strip()
    if dirty:
        raise RuntimeError("Refusing SHA-tagged release from modified tracked source")
    images = {}
    for name in IMAGES:
        context = (
            ROOT / "frontend"
            if name == "frontend"
            else ROOT / "images" / name
            if name in {"postgres", "rabbitmq", "mailpit"}
            else ROOT
        )
        dockerfile = ROOT / "services/Dockerfile" if name == "app" else context / "Dockerfile"
        source_revision = revision
        created = now()
        extra = []
        if name in {"postgres", "rabbitmq", "mailpit"}:
            # Keep unchanged middleware metadata stable across app releases. Cache is
            # persistent; cold rebuilds/upgrades still require a maintenance check.
            provenance = run(
                [
                    "git",
                    "-c",
                    "safe.directory=" + ROOT.as_posix(),
                    "log",
                    "-1",
                    "--format=%H%n%ct%n%cI",
                    "--",
                    context.relative_to(ROOT),
                ]
            ).stdout.splitlines()
            source_revision, epoch, created = provenance
            extra = ["--build-arg", "SOURCE_DATE_EPOCH=" + epoch]
        run(
            [
                "docker",
                "build",
                "--label",
                "org.opencontainers.image.source=" + TOOLS["repository"],
                "--label",
                "org.opencontainers.image.revision=" + source_revision,
                "--label",
                "org.opencontainers.image.created=" + created,
                *extra,
                "-f",
                dockerfile,
                "-t",
                image(name, revision),
                context,
            ],
            log=OUTPUT / "build" / f"{name}.log",
        )
        image_id = run(
            ["docker", "image", "inspect", image(name, revision), "--format", "{{.Id}}"]
        ).stdout.strip()
        images[name] = {
            "tag": image(name, revision),
            "image_id": image_id,
            "source_revision": source_revision,
        }
    write_json(
        OUTPUT / "built-images.json", {"commit": revision, "built_at_utc": now(), "images": images}
    )


def integration():
    (OUTPUT / "integration-metadata.json").unlink(missing_ok=True)
    revision = commit()
    project = f"clinic-ci-{revision[:12]}-{uuid.uuid4().hex[:8]}"
    if not re.fullmatch(r"clinic-ci-[a-f0-9]{12}-[a-f0-9]{8}", project):
        raise ValueError("Unsafe CI project name")
    PRIVATE.mkdir(exist_ok=True, mode=0o700)
    env_file = PRIVATE / (project + ".env")
    env_file.write_text(
        "CI_REGISTRY="
        + os.environ.get("CLINIC_REGISTRY", TOOLS["registry"])
        + "\nCI_COMMIT="
        + revision
        + "\nCI_DB_PASSWORD="
        + secrets.token_hex(24)
        + "\nCI_BROKER_PASSWORD="
        + secrets.token_hex(24)
        + "\nCI_JWT_SECRET="
        + secrets.token_hex(32)
        + "\n",
        encoding="utf-8",
    )
    env_file.chmod(0o600)
    compose = [
        "docker",
        "compose",
        "--env-file",
        env_file,
        "-f",
        ROOT / "ci/compose.test.yaml",
        "-p",
        project,
    ]
    test_name = project + "-test"
    try:
        run(
            compose + ["up", "-d", "--wait", "postgres", "rabbitmq", "mailpit"],
            log=OUTPUT / "integration-up.log",
        )
        result = run(
            compose + ["run", "--name", test_name, "--no-deps", "test"],
            check=False,
            timeout=240,
            log=OUTPUT / "integration.log",
        )
        run(
            ["docker", "cp", test_name + ":/tmp/junit.xml", OUTPUT / "junit-integration.xml"],
            log=OUTPUT / "integration-copy.log",
        )
        write_json(
            OUTPUT / "integration-metadata.json",
            {
                "commit": revision,
                "project": project,
                "scope": "Isolated CI PostgreSQL/RabbitMQ/Mailpit; no dev ports or volumes",
                "test_exit_code": result.returncode,
                "report_sha256": hashlib.sha256(
                    (OUTPUT / "junit-integration.xml").read_bytes()
                ).hexdigest(),
                "at_utc": now(),
            },
        )
        if result.returncode:
            raise subprocess.CalledProcessError(result.returncode, result.args)
    finally:
        run(
            ["docker", "rm", "-f", test_name],
            check=False,
            log=OUTPUT / "integration-remove-test.log",
        )
        cleanup = run(
            compose + ["down", "--volumes", "--remove-orphans"],
            check=False,
            log=OUTPUT / "integration-cleanup.log",
        )
        env_file.unlink(missing_ok=True)
        if cleanup.returncode:
            raise RuntimeError("CI resource cleanup failed; inspect integration-cleanup.log")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=[
            "prepare",
            "lint",
            "unit",
            "build",
            "integration",
            "infrastructure",
            "observability",
            "deploy-staging",
            "deploy-production",
        ],
    )
    args = parser.parse_args()
    {
        "prepare": prepare,
        "lint": lint,
        "unit": unit,
        "build": build,
        "integration": integration,
        "infrastructure": lambda: run([python_executable(), "-m", "ci.infrastructure"]),
        "observability": lambda: run([python_executable(), "-m", "ci.observability"]),
        "deploy-staging": lambda: run([python_executable(), "-m", "ci.deploy", "staging"]),
        "deploy-production": lambda: run([python_executable(), "-m", "ci.deploy", "production"]),
    }[args.action]()


if __name__ == "__main__":
    main()
