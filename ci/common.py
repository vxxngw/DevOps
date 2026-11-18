import json
import os
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "ci-out"
PRIVATE = ROOT / ".ci-local"
IMAGES = ("app", "frontend", "postgres", "rabbitmq", "mailpit")
TOOLS = json.loads((ROOT / "ci/tools.json").read_text(encoding="utf-8"))


def now():
    return datetime.now(UTC).isoformat()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def run(command, *, log=None, check=True, timeout=1200, input_text=None, env=None, cwd=ROOT):
    command = [str(part) for part in command]
    # Passwords are only passed on stdin/env; command arguments must never contain them.
    print("Running:", " ".join(command), flush=True)
    environment = (os.environ if env is None else env).copy()
    temporary = PRIVATE / "temp"
    temporary.mkdir(parents=True, exist_ok=True, mode=0o700)
    environment.update(TMP=str(temporary), TEMP=str(temporary), TMPDIR=str(temporary))
    result = subprocess.run(
        command,
        cwd=cwd,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=environment,
    )
    if log:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(result.stdout + result.stderr, encoding="utf-8")
        print(f"Exit{result.returncode}; log:{log.relative_to(ROOT)}", flush=True)
    elif result.returncode:
        print(result.stderr[-2000:], flush=True)
    if check and result.returncode:
        raise subprocess.CalledProcessError(result.returncode, command)
    return result


def tool(name):
    local = PRIVATE / "bin" / (name + (".exe" if os.name == "nt" else ""))
    executable = str(local) if local.is_file() else shutil.which(name)
    if not executable:
        raise RuntimeError(
            f"Missing {name}; run scripts/ci/install-ci-tools.py or use the CI agent"
        )
    return executable


def commit():
    actual = run(
        ["git", "-c", "safe.directory=" + ROOT.as_posix(), "rev-parse", "HEAD"]
    ).stdout.strip()
    if not re.fullmatch(r"[a-f0-9]{40}", actual):
        raise RuntimeError("A real Git commit is required for SHA image tags")
    expected = os.environ.get("CLINIC_COMMIT", actual)
    if actual != expected:
        raise RuntimeError("Checkout does not match CLINIC_COMMIT")
    return actual


def image(name, revision=None):
    if name not in IMAGES:
        raise ValueError("Unknown release image")
    registry = os.environ.get("CLINIC_REGISTRY", TOOLS["registry"])
    if not re.fullmatch(r"ghcr\.io/[a-z0-9][a-z0-9_-]*", registry):
        raise ValueError("Registry must be an explicit GHCR namespace")
    return f"{registry}/devops-{name}:{revision or commit()}"


def python_executable():
    configured = os.environ.get("CLINIC_CI_PYTHON")
    if configured:
        return configured
    return str(PRIVATE / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
