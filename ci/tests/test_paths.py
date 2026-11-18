import subprocess

import pytest

from ci.paths import wsl_bash


def test_wsl_uses_current_checkout_and_preserves_spaces(tmp_path, monkeypatch):
    script = tmp_path / "team project" / "control.sh"
    script.parent.mkdir()
    script.write_text("#!/bin/sh\n", encoding="utf-8")
    received = []

    def convert(command, **kwargs):
        received.append(command)
        return "/mnt/e/team project/control.sh\n"

    monkeypatch.delenv("CLINIC_WSL_DISTRO", raising=False)
    monkeypatch.setattr(subprocess, "check_output", convert)
    assert wsl_bash(script) == ["wsl", "-e", "bash", "/mnt/e/team project/control.sh"]
    assert received == [["wsl", "-e", "wslpath", "-a", "-u", str(script.resolve())]]


def test_wsl_distro_is_explicit_or_uses_user_setting(tmp_path, monkeypatch):
    script = tmp_path / "control.sh"
    script.touch()
    received = []

    def convert(command, **kwargs):
        received.append(command)
        return "/work/control.sh"

    monkeypatch.setenv("CLINIC_WSL_DISTRO", "TeamLinux")
    monkeypatch.setattr(subprocess, "check_output", convert)
    assert wsl_bash(script)[:3] == ["wsl", "-d", "TeamLinux"]
    assert wsl_bash(script, distro="OtherLinux")[:3] == ["wsl", "-d", "OtherLinux"]
    assert received[0][:3] == ["wsl", "-d", "TeamLinux"]


def test_wsl_rejects_missing_or_invalid_script_path(tmp_path, monkeypatch):
    with pytest.raises(FileNotFoundError):
        wsl_bash(tmp_path / "missing.sh")
    script = tmp_path / "control.sh"
    script.touch()
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "not-absolute")
    with pytest.raises(ValueError, match="invalid absolute"):
        wsl_bash(script)


def test_wsl_translation_failure_is_not_hidden(tmp_path, monkeypatch):
    script = tmp_path / "control.sh"
    script.touch()

    def failure(command, **kwargs):
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(subprocess, "check_output", failure)
    with pytest.raises(subprocess.CalledProcessError):
        wsl_bash(script)
