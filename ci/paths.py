"""Portable command construction for the optional Windows/WSL control host."""

import os
import subprocess
from pathlib import Path


def wsl_bash(script: Path, *, distro: str | None = None) -> list[str]:
    """Translate the current checkout path without shell interpolation or a fixed drive."""
    source = script.resolve(strict=True)
    selected = distro if distro is not None else os.environ.get("CLINIC_WSL_DISTRO")
    prefix = ["wsl", *(["-d", selected] if selected else []), "-e"]
    translated = subprocess.check_output(
        [*prefix, "wslpath", "-a", "-u", str(source)],
        text=True,
        encoding="utf-8",
        timeout=30,
    ).strip()
    if not translated.startswith("/") or "\n" in translated or "\r" in translated:
        raise ValueError("WSL returned an invalid absolute script path")
    return [*prefix, "bash", translated]
