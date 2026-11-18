"""Validate the actual reports before an operator may install monitoring images."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path


def check_scan_receipt(receipt_path, versions_path):
    receipt_path, versions_path = Path(receipt_path), Path(versions_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    versions = json.loads(versions_path.read_text(encoding="utf-8"))
    if (
        receipt.get("passed") is not True
        or receipt.get("versions_sha256") != hashlib.sha256(versions_path.read_bytes()).hexdigest()
    ):
        raise ValueError("Missing passing scan for the exact pinned versions")
    age = datetime.now(UTC) - datetime.fromisoformat(receipt["at_utc"])
    if age < timedelta(0) or age > timedelta(hours=24):
        raise ValueError("Operator image scan must be from the last 24 hours")
    if set(receipt["images"]) != set(versions["images"]):
        raise ValueError("Every operator image must have its own report")
    for name, image in versions["images"].items():
        record = receipt["images"][name]
        report = receipt_path.parent / (name + ".json")
        if record["reference"] != image["reference"] or record["exit_code"] != 0:
            raise ValueError("Image scan was not successful: " + name)
        if hashlib.sha256(report.read_bytes()).hexdigest() != record["report_sha256"]:
            raise ValueError("Image report content changed: " + name)
        data = json.loads(report.read_text(encoding="utf-8"))
        if data.get("ArtifactName") != image["reference"] or not data.get("Results"):
            raise ValueError("Missing real scanner artifact/results: " + name)
        if any(
            v["Severity"] == "CRITICAL"
            for item in data["Results"]
            for v in item.get("Vulnerabilities", [])
        ):
            raise ValueError("CRITICAL findings block bootstrap: " + name)


def validate_secrets(data):
    expected = {
        ("monitoring", "grafana-admin"),
        ("monitoring", "alertmanager-config"),
        ("logging", "elastic-admin"),
        ("logging", "kibana-auth"),
        ("logging", "fluentd-auth"),
        ("staging", "postgres-metrics"),
        ("production", "postgres-metrics"),
    }
    keys = [(item["metadata"].get("namespace"), item["metadata"]["name"]) for item in data["items"]]
    if set(keys) != expected or len(keys) != len(expected):
        raise ValueError("Secret file must contain exactly the dedicated operator credentials")
    if any(item["kind"] != "Secret" or not item.get("stringData") for item in data["items"]):
        raise ValueError("Unexpected private object")
