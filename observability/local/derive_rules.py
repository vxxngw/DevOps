"""Derive the local Prometheus rule set from the production rule file.

The production file (observability/prometheus/rules/clinic.yml) is the single
source of truth. Two things in it cannot be evaluated in the local Docker
runtime:

* the `clinic:service_expected` / `clinic:backup_expected` recording rules are
  hard-coded `vector(1)` expectations for the `production` namespace and for a
  backup CronJob that do not exist locally, so `ClinicServiceDown` and
  `ClinicBackupStale` would fire forever;
* `clinic:container_cpu_cores5m` / `clinic:container_memory_bytes` need
  cAdvisor metrics that only exist inside a cluster.

Everything else - every alert expression, `for` duration, label and annotation -
is copied byte for byte. The derivation is deterministic and is recorded in the
evidence receipt with sha256 hashes of the source and the derived file.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_RULES = REPO_ROOT / "observability" / "prometheus" / "rules" / "clinic.yml"
LOCAL_RULES_DIR = REPO_ROOT / "observability" / "local" / "prometheus" / "rules"
DERIVED_RULES = LOCAL_RULES_DIR / "clinic.local.yml"

# Recording rules that encode cluster-only expectations.
DROPPED_RECORDS = {
    "clinic:service_expected",
    "clinic:backup_expected",
    "clinic:container_cpu_cores5m",
    "clinic:container_memory_bytes",
}

# Alerts that depend exclusively on the dropped recording rules.
DROPPED_ALERTS = {
    "ClinicServiceDown",
    "ClinicBackupStale",
    "ClinicBackupFailed",
    "ClinicHighNodeCpu",
    "ClinicHighNodeMemory",
}

HEADER = """# GENERATED FILE - do not edit by hand.
#
# Derived from observability/prometheus/rules/clinic.yml by
# scripts/verify-observability-runtime.py for the local Docker runtime.
# Dropped recording rules: {records}
# Dropped alerts: {alerts}
# Every remaining expression, `for`, label and annotation is unchanged.
"""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def derive() -> dict:
    source = yaml.safe_load(PRODUCTION_RULES.read_text(encoding="utf-8"))
    kept_groups = []
    dropped_records: list[str] = []
    dropped_alerts: list[str] = []
    for group in source["groups"]:
        rules = []
        for rule in group["rules"]:
            if rule.get("record") in DROPPED_RECORDS:
                dropped_records.append(rule["record"])
                continue
            if rule.get("alert") in DROPPED_ALERTS:
                dropped_alerts.append(rule["alert"])
                continue
            rules.append(rule)
        if rules:
            kept_groups.append({"name": group["name"], "rules": rules})

    header = HEADER.format(
        records=", ".join(sorted(set(dropped_records))) or "none",
        alerts=", ".join(sorted(set(dropped_alerts))) or "none",
    )
    body = yaml.safe_dump({"groups": kept_groups}, sort_keys=False, allow_unicode=True, width=1000)
    LOCAL_RULES_DIR.mkdir(parents=True, exist_ok=True)
    DERIVED_RULES.write_text(header + body, encoding="utf-8")

    return {
        "source": str(PRODUCTION_RULES.relative_to(REPO_ROOT)).replace("\\", "/"),
        "source_sha256": sha256(PRODUCTION_RULES),
        "derived": str(DERIVED_RULES.relative_to(REPO_ROOT)).replace("\\", "/"),
        "derived_sha256": sha256(DERIVED_RULES),
        "dropped_recording_rules": sorted(set(dropped_records)),
        "dropped_alerts": sorted(set(dropped_alerts)),
        "kept_alerts": sorted(
            rule["alert"] for group in kept_groups for rule in group["rules"] if rule.get("alert")
        ),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(derive(), indent=2, ensure_ascii=False))
