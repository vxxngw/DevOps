import subprocess
from types import SimpleNamespace

import pytest

from ci import release


def fake_run(results):
    calls = []

    def run(command, *, env=None, log=None, check=True):
        calls.append(command)
        code = results.pop(0)
        if check and code:
            raise subprocess.CalledProcessError(code, command)
        return SimpleNamespace(returncode=code)

    return run, calls


def test_verify_pull_retries_until_registry_serves_the_digest(monkeypatch):
    run, calls = fake_run([1, 1, 0])
    monkeypatch.setattr(release, "run", run)
    monkeypatch.setattr(release.time, "sleep", lambda _seconds: None)
    release.verify_pull("ghcr.io/vxxngw/devops-app@sha256:" + "a" * 64, env={}, log=None)
    assert len(calls) == 3


def test_verify_pull_fails_after_last_attempt(monkeypatch):
    run, calls = fake_run([1, 1, 1])
    monkeypatch.setattr(release, "run", run)
    monkeypatch.setattr(release.time, "sleep", lambda _seconds: None)
    with pytest.raises(subprocess.CalledProcessError):
        release.verify_pull("ref@sha256:" + "b" * 64, env={}, log=None, delays=(1, 1))
    assert len(calls) == 3
