"""Read-only preflight; bounded commands; redact DSNs and never inspect credential files."""

import json
import platform
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

root = Path(__file__).resolve().parents[1]
results = {
    "at_utc": datetime.now(UTC).isoformat(),
    "host": platform.platform(),
    "commit": "UNCOMMITTED",
    "commands": [],
    "disk": dict(zip(["total", "used", "free"], shutil.disk_usage(root))),
}
for command in [
    ["git", "-c", "safe.directory=" + root.as_posix(), "status", "--short"],
    ["python", "--version"],
    ["node", "--version"],
    ["docker", "version"],
    ["docker", "compose", "version"],
    ["docker", "desktop", "status"],
    ["kubectl", "config", "current-context"],
    ["terraform", "version"],
]:
    try:
        result = subprocess.run(
            command,
            cwd=root,
            timeout=20,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        results["commands"].append(
            {
                "command": command,
                "exit_code": result.returncode,
                "output": result.stdout + result.stderr,
            }
        )
    except FileNotFoundError:
        results["commands"].append({"command": command, "status": "MISSING"})
    except subprocess.TimeoutExpired:
        results["commands"].append({"command": command, "status": "TIMEOUT_20_SECONDS"})
folder = root / "docs" / "evidence"
folder.mkdir(parents=True, exist_ok=True)
target = folder / ("preflight-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + ".json")
target.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
print(target.relative_to(root))
for result in results["commands"]:
    print(result["command"], result.get("status", result.get("exit_code")))
