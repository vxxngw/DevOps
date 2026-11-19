"""Real parser/schema checks for observability preparation; never a runtime acceptance receipt."""

import hashlib
import json
import os
import shutil

import yaml

from ci.common import OUTPUT, ROOT, commit, now, run, write_json
from ci.infrastructure import load_documents, schema_index, validate_schema
from observability.config import alertmanager_config


def tool(name):
    local = ROOT / ".infra-local/observability" / ("windows" if os.name == "nt" else "linux")
    binary = local / (name + (".exe" if os.name == "nt" else ""))
    result = str(binary) if binary.is_file() else shutil.which(name)
    if not result:
        raise RuntimeError("Install pinned observability tools first: " + name)
    return result


def policy(resources):
    versions = json.loads((ROOT / "observability/versions.json").read_text(encoding="utf-8"))
    images = {item["reference"] for item in versions["images"].values()}
    for item in resources:
        if item["kind"] == "Secret":
            raise ValueError(
                "Real observability Secrets must remain operator-owned and outside Git"
            )
        if item["kind"] in {"ClusterRole", "Role"}:
            for rule in item["rules"]:
                if (
                    "secrets" in rule.get("resources", [])
                    or "nodes/proxy" in rule.get("resources", [])
                    or any(verb not in {"get", "list", "watch"} for verb in rule["verbs"])
                ):
                    raise ValueError(
                        "Observability RBAC must be read-only without secret or proxy access"
                    )
        if item["kind"] == "Service" and item["spec"].get("type", "ClusterIP") != "ClusterIP":
            raise ValueError(
                "Expose dashboards through explicit local forwarding, not public services"
            )
        if item["kind"] not in {"Deployment", "StatefulSet", "DaemonSet"}:
            continue
        pod = item["spec"]["template"]["spec"]
        collector = item["metadata"]["name"] == "fluentd"
        needs_api = item["metadata"]["name"] in {"prometheus", "kube-state-metrics"}
        if bool(pod.get("automountServiceAccountToken")) != needs_api:
            raise ValueError("Only discovery/metrics readers may receive API credentials")
        if not collector and pod.get("securityContext", {}).get("runAsNonRoot") is not True:
            raise ValueError("Only the host log collector may use root")
        for volume in pod.get("volumes", []):
            secret = volume.get("secret", {})
            if (
                secret.get("secretName") == "elasticsearch-tls"
                and item["metadata"]["name"] != "elasticsearch"
            ):
                if secret.get("items") != [{"key": "ca.crt", "path": "ca.crt"}]:
                    raise ValueError("Elasticsearch clients may receive its public CA only")
            if "hostPath" in volume:
                if not collector or volume["hostPath"]["path"] not in {
                    "/var/log/pods",
                    "/var/lib/anuyen-fluentd",
                }:
                    raise ValueError("Unexpected host filesystem access")
        for container in pod["containers"]:
            if container["image"] not in images or "@sha256:" not in container["image"]:
                raise ValueError("Every observability workload must use a resolved image digest")
            security = container.get("securityContext", {})
            if security.get("allowPrivilegeEscalation") is not False or security.get("privileged"):
                raise ValueError("Collector exception does not permit privileged containers")
            if "ALL" not in security.get("capabilities", {}).get("drop", []):
                raise ValueError("Drop container capabilities")
            if not all(
                key in container for key in ["startupProbe", "readinessProbe", "livenessProbe"]
            ):
                raise ValueError("Missing workload probe")
            if not all(key in container.get("resources", {}) for key in ["requests", "limits"]):
                raise ValueError("Missing requests or limits")
            if collector:
                log_mount = next(m for m in container["volumeMounts"] if m["name"] == "logs")
                if log_mount.get("readOnly") is not True:
                    raise ValueError("Host logs must be read-only")


def main():
    destination = OUTPUT / "observability"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "metadata.json").unlink(missing_ok=True)
    versions = json.loads((ROOT / "observability/versions.json").read_text(encoding="utf-8"))
    for name, component in [("promtool", "prometheus"), ("amtool", "alertmanager")]:
        version = run([tool(name), "--version"]).stdout
        if versions["tools"][component]["version"] not in version:
            raise RuntimeError("Unexpected tool version: " + name)
    run(
        [
            tool("promtool"),
            "check",
            "config",
            "--syntax-only",
            ROOT / "observability/prometheus/prometheus.yml",
        ],
        log=destination / "prometheus-config.log",
    )
    run(
        [
            tool("promtool"),
            "check",
            "rules",
            "--lint-fatal",
            ROOT / "observability/prometheus/rules/clinic.yml",
            ROOT / "observability/prometheus/demo/clinic-demo.yml",
        ],
        log=destination / "rules-check.log",
    )
    run(
        [
            tool("promtool"),
            "test",
            "rules",
            ROOT / "observability/prometheus/tests/clinic.test.yml",
        ],
        log=destination / "rules-test.log",
    )
    dashboard = json.loads(
        (ROOT / "observability/grafana/dashboards/operations.json").read_text(encoding="utf-8")
    )
    for panel in dashboard["panels"]:
        for target in panel["targets"]:
            run(
                [tool("promtool"), "--experimental", "promql", "format", target["expr"]],
                log=destination / "queries" / (str(panel["id"]) + ".log"),
            )
    fixture = ROOT / ".infra-local/observability/validation"
    fixture.mkdir(parents=True, exist_ok=True)
    token = fixture / "synthetic-token"
    token.write_text("LOCAL-PARSER-FIXTURE-NOT-A-REAL-TOKEN", encoding="utf-8")
    receiver = fixture / "alertmanager.yml"
    receiver.write_text(
        yaml.safe_dump(alertmanager_config(-1001234567890, str(token))), encoding="utf-8"
    )
    run([tool("amtool"), "check-config", receiver], log=destination / "alertmanager-config.log")
    content = run(["kubectl", "kustomize", ROOT / "observability"]).stdout
    resources = load_documents(content)
    validate_schema(resources, schema_index())
    policy(resources)
    write_json(destination / "rendered.json", resources)
    files = sorted(
        path
        for path in (ROOT / "observability").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )
    write_json(
        destination / "metadata.json",
        {
            "at_utc": now(),
            "head_commit": commit(),
            "scope": "Prometheus syntax/rules/fixture scenarios and dashboard PromQL, Alertmanager synthetic local config parser, K8s schema/policy only. No target scrape, delivery, Grafana UI, Fluentd parser or EFK ingestion claim.",
            "runtime_status": "NOT_RUN",
            "fluentd_parser": "NOT_RUN: Linux container/runtime required",
            "kubernetes_objects": len(resources),
            "dashboard_panels": len(dashboard["panels"]),
            "files": [
                {
                    "path": path.relative_to(ROOT).as_posix(),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
                for path in files
            ],
        },
    )
    print("Observability preparation checks passed; cluster/delivery/log ingestion still NOT_RUN")


if __name__ == "__main__":
    main()
