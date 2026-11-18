import hashlib
import json
import secrets
import subprocess
from pathlib import Path

import pytest

from ci.common import ROOT, tool


def scan_fixture(tmp_path, relative, content):
    try:
        scanner = tool("gitleaks")
    except RuntimeError:
        pytest.skip("Install the pinned scanner for the real Gitleaks configuration tests")
    fixture = tmp_path / "input" / relative
    fixture.parent.mkdir(parents=True)
    fixture.write_text(content, encoding="utf-8")
    report = tmp_path / "report.json"
    result = subprocess.run(
        [
            scanner,
            "dir",
            str(tmp_path / "input"),
            "--config",
            str(ROOT / ".gitleaks.toml"),
            "--redact",
            "--no-banner",
            "--report-format",
            "json",
            "--report-path",
            str(report),
        ],
        capture_output=True,
        timeout=30,
    )
    return result.returncode, json.loads(report.read_text(encoding="utf-8"))


def source_hash_line():
    digest = hashlib.sha256((ROOT / "frontend/src/lib/api.ts").read_bytes()).hexdigest()
    return json.dumps({"frontend/src/lib/api.ts": digest})[1:-1] + "\n"


def test_verified_source_hash_exception_is_narrow(tmp_path):
    code, findings = scan_fixture(
        tmp_path, Path("docs/evidence/test/metadata.json"), source_hash_line()
    )
    assert code == 0 and findings == []


def test_evidence_metadata_still_detects_generated_generic_secret(tmp_path):
    generated = secrets.token_hex(32)
    content = json.dumps({"api_key": generated}, indent=2)
    code, findings = scan_fixture(tmp_path, Path("docs/evidence/test/metadata.json"), content)
    assert code == 1 and findings
    assert all(item["Secret"] == "REDACTED" or "REDACTED" in item["Secret"] for item in findings)


def test_same_source_hash_shape_is_not_exempt_outside_evidence(tmp_path):
    code, findings = scan_fixture(tmp_path, Path("src/config.txt"), source_hash_line())
    assert code == 1 and findings
