"""Scan all pinned operator images; missing or CRITICAL findings block bootstrap."""

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(
    0,
    str(
        next(
            (
                p
                for p in Path(__file__).resolve().parents
                if (p / "Jenkinsfile").is_file() and (p / "pyproject.toml").is_file()
            ),
            Path.cwd(),
        )
    ),
)
from ci.common import OUTPUT, ROOT, now, write_json
from ci.security import trivy


def main():
    versions_file = ROOT / "observability/versions.json"
    versions = json.loads(versions_file.read_text(encoding="utf-8"))
    destination = OUTPUT / "observability-images"
    destination.mkdir(parents=True, exist_ok=True)
    receipt = destination / "metadata.json"
    receipt.unlink(missing_ok=True)
    results = {}
    for name, image in versions["images"].items():
        report = destination / (name + ".json")
        report.unlink(missing_ok=True)
        try:
            result, data, findings = trivy(image["reference"], report, remote=True)
        except RuntimeError as error:
            # A network/scanner failure is not a clean image. Keep collecting other
            # independent reports while ensuring the overall gate remains closed.
            results[name] = {
                "reference": image["reference"],
                "exit_code": None,
                "critical": None,
                "report_valid": False,
                "report_sha256": None,
                "status": "BLOCKED",
                "error_type": type(error).__name__,
            }
            continue
        critical = len(findings)
        valid = bool(
            data and data.get("ArtifactName") == image["reference"] and data.get("Results")
        )
        results[name] = {
            "reference": image["reference"],
            "exit_code": result.returncode,
            "critical": critical,
            "report_valid": valid,
            "report_sha256": hashlib.sha256(report.read_bytes()).hexdigest() if data else None,
        }
    passed = all(
        item["exit_code"] == 0 and item["critical"] == 0 and item["report_valid"]
        for item in results.values()
    )
    write_json(
        receipt,
        {
            "at_utc": now(),
            "versions_sha256": hashlib.sha256(versions_file.read_bytes()).hexdigest(),
            "passed": passed,
            "images": results,
            "policy": {"ignore_unfixed": False, "ignorefile": "empty", "source": "remote"},
        },
    )
    if not passed:
        raise SystemExit("Operator image gate failed; do not bootstrap this stack")


if __name__ == "__main__":
    main()
