"""Parse every shell script individually, including scripts in nested groups."""

import os
import shutil
from pathlib import Path

from ci.common import OUTPUT, run


def bash_executable():
    if os.name == "nt":
        git = shutil.which("git")
        candidates = [Path(git).parent.parent / "bin/bash.exe"] if git else []
        if os.environ.get("ProgramFiles"):
            candidates.append(Path(os.environ["ProgramFiles"]) / "Git/bin/bash.exe")
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
        raise RuntimeError(
            "Install Git Bash for native Windows syntax checks; WSL is checked separately"
        )
    result = shutil.which("bash")
    if not result:
        raise RuntimeError("Missing Bash; syntax validation cannot be inferred")
    return result


def check_bash_sources(root: Path, *, runner=run):
    scripts = sorted((root / "scripts").rglob("*.sh"))
    if not scripts:
        raise ValueError("No shell scripts found; refusing an empty Bash check")
    binary = bash_executable()
    records = []
    for script in scripts:
        relative = script.relative_to(root).as_posix()
        result = runner(
            [binary, "-n", script.as_posix()],
            log=OUTPUT / "infra/bash" / (relative.replace("/", "__") + ".log"),
        )
        records.append({"path": relative, "exit_code": result.returncode})
    return records
