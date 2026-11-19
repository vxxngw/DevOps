"""Operator-stack security regression tests, separate from application telemetry tests."""

import copy
import hashlib
import importlib.util
import json
from datetime import UTC, datetime

import pytest
import yaml

from ci.common import ROOT
from ci.observability import policy
from observability.config import alertmanager_config
from observability.gates import check_scan_receipt, validate_secrets


@pytest.fixture
def resources():
    return list(yaml.safe_load_all((ROOT / "observability/k8s/resources.yaml").read_text()))


def test_monitoring_cannot_read_secrets_or_proxy_kubelet(resources):
    for forbidden in ["secrets", "nodes/proxy"]:
        changed = copy.deepcopy(resources)
        role = next(item for item in changed if item["kind"] == "ClusterRole")
        role["rules"][0]["resources"].append(forbidden)
        with pytest.raises(ValueError, match="RBAC"):
            policy(changed)


def test_collector_exception_does_not_allow_writable_host_logs(resources):
    collector = next(item for item in resources if item["kind"] == "DaemonSet")
    mount = next(
        item
        for item in collector["spec"]["template"]["spec"]["containers"][0]["volumeMounts"]
        if item["name"] == "logs"
    )
    mount["readOnly"] = False
    with pytest.raises(ValueError, match="read-only"):
        policy(resources)


def test_unpinned_image_cannot_enter_operator_stack(resources):
    next(item for item in resources if item["kind"] == "Deployment")["spec"]["template"]["spec"][
        "containers"
    ][0]["image"] = "prom/prometheus:latest"
    with pytest.raises(ValueError, match="digest"):
        policy(resources)


def test_alert_receiver_uses_file_and_sends_resolved():
    with pytest.raises(ValueError):
        alertmanager_config(0)
    receiver = alertmanager_config(-1001234567890)["receivers"][0]["telegram_configs"][0]
    assert "bot_token" not in receiver
    assert receiver["bot_token_file"].endswith("telegram-token")
    assert receiver["send_resolved"] is True


def test_log_collector_cannot_receive_elasticsearch_private_key(resources):
    pod = next(item for item in resources if item["kind"] == "DaemonSet")["spec"]["template"][
        "spec"
    ]
    secret = next(
        item["secret"]
        for item in pod["volumes"]
        if item.get("secret", {}).get("secretName") == "elasticsearch-tls"
    )
    secret.pop("items")
    with pytest.raises(ValueError, match="public CA"):
        policy(resources)


def test_scrape_keeps_event_service_labels_and_verifies_kubelet_tls():
    config = yaml.safe_load((ROOT / "observability/prometheus/prometheus.yml").read_text())
    jobs = {item["job_name"]: item for item in config["scrape_configs"]}
    assert jobs["clinic"]["honor_labels"] is True
    assert jobs["kubelet"]["scheme"] == "https"
    assert jobs["kubelet"]["tls_config"]["ca_file"]
    assert not jobs["kubelet"]["tls_config"].get("insecure_skip_verify")
    assert jobs["rabbitmq-staging"]["metrics_path"] == "/metrics/per-object"


def test_generated_operator_credentials_are_isolated_and_not_an_app_secret():
    spec = importlib.util.spec_from_file_location(
        "prepare_obs", ROOT / "scripts/prepare-observability-secrets.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = module.build(-1001234567890, "LOCAL-PARSER-FIXTURE")
    validate_secrets(data)
    passwords = [
        item["stringData"]["password"] for item in data["items"] if "password" in item["stringData"]
    ]
    assert len(passwords) == len(set(passwords))
    data["items"][0]["metadata"]["name"] = "clinic-app"
    with pytest.raises(ValueError):
        validate_secrets(data)


@pytest.fixture
def scan(tmp_path):
    reference = "quay.io/prometheus/prometheus@sha256:" + "a" * 64
    versions = tmp_path / "versions.json"
    versions.write_text(json.dumps({"images": {"prometheus": {"reference": reference}}}))
    report = tmp_path / "prometheus.json"
    report.write_text(
        json.dumps(
            {"ArtifactName": reference, "Results": [{"Target": "test", "Vulnerabilities": []}]}
        )
    )
    receipt = {
        "passed": True,
        "at_utc": datetime.now(UTC).isoformat(),
        "versions_sha256": hashlib.sha256(versions.read_bytes()).hexdigest(),
        "images": {
            "prometheus": {
                "reference": reference,
                "exit_code": 0,
                "report_sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
            }
        },
    }
    path = tmp_path / "metadata.json"
    path.write_text(json.dumps(receipt))
    return path, versions, report, receipt


def test_modified_scanner_report_blocks_bootstrap(scan):
    path, versions, report, _ = scan
    check_scan_receipt(path, versions)
    report.write_text("{}")
    with pytest.raises(ValueError, match="changed"):
        check_scan_receipt(path, versions)


def test_critical_finding_cannot_be_hidden_by_passing_metadata(scan):
    path, versions, report, receipt = scan
    data = json.loads(report.read_text())
    data["Results"][0]["Vulnerabilities"] = [{"Severity": "CRITICAL"}]
    report.write_text(json.dumps(data))
    receipt["images"]["prometheus"]["report_sha256"] = hashlib.sha256(
        report.read_bytes()
    ).hexdigest()
    path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="CRITICAL"):
        check_scan_receipt(path, versions)


def test_scanner_outage_does_not_hide_other_reports_or_open_gate(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "scan_obs", ROOT / "scripts/scan-observability.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    versions = {
        "images": {
            name: {"reference": name + "@sha256:" + "a" * 64} for name in ["blocked", "scannable"]
        }
    }
    (tmp_path / "observability").mkdir()
    (tmp_path / "observability/versions.json").write_text(json.dumps(versions))
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "OUTPUT", tmp_path / "output")
    calls = []

    def scanner(reference, report, remote):
        calls.append(reference)
        assert remote is True
        if reference.startswith("blocked"):
            raise RuntimeError("No scanner report due to test network outage")
        data = {"ArtifactName": reference, "Results": [{"Target": "test", "Vulnerabilities": []}]}
        report.write_text(json.dumps(data))
        from types import SimpleNamespace

        return SimpleNamespace(returncode=0), data, []

    monkeypatch.setattr(module, "trivy", scanner)
    with pytest.raises(SystemExit):
        module.main()
    receipt = json.loads((tmp_path / "output/observability-images/metadata.json").read_text())
    assert len(calls) == 2
    assert receipt["passed"] is False
    assert receipt["images"]["blocked"]["status"] == "BLOCKED"
    assert receipt["images"]["scannable"]["exit_code"] == 0
