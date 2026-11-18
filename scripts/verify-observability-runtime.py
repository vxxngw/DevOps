"""Prove the observability stack actually runs, alerts and ships logs.

This is the runtime half of Bài 10 / P1-04. The static half (schema, policy,
secret scanning) lives in ci/observability.py and observability/gates.py; this
script answers a different question: when the stack is up, does a real failure
produce a real FIRING notification and a real RESOLVED notification, and do
application logs really land in Elasticsearch and show up in Kibana?

What it does, in order:

1. derives the local Prometheus rule set from the production rule file
   (observability/local/derive_rules.py) and records both sha256 hashes;
2. starts observability/local/compose.yaml next to the existing clinic-dev
   stack, reusing the same images and the same clinic network;
3. waits for Prometheus, Alertmanager, Grafana, Elasticsearch, Fluentd, Kibana
   and the webhook receiver to answer;
4. asserts every scrape target is UP and the Grafana dashboard is provisioned;
5. triggers a real failure (RabbitMQ stopped, so the backend dependency gauge
   drops to 0), waits for ClinicDependencyDown to reach Alertmanager, then
   restarts RabbitMQ and waits for the RESOLVED notification;
6. queries Elasticsearch for the application logs Fluentd shipped and Kibana
   for the data view;
7. writes a JSON receipt with every observation and a pass/fail verdict.

Nothing is faked: every value in the receipt comes from an HTTP response of a
running container. If a step fails the receipt records the failure and the
script exits non-zero.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = REPO_ROOT / "observability" / "local" / "compose.yaml"
EVIDENCE_DIR = REPO_ROOT / "observability" / "local" / "evidence"
RECEIPT = EVIDENCE_DIR / "runtime-receipt.json"
ALERT_RECEIPTS = EVIDENCE_DIR / "alertmanager-receipts.jsonl"

PROMETHEUS = "http://127.0.0.1:19090"
ALERTMANAGER = "http://127.0.0.1:19093"
GRAFANA = "http://127.0.0.1:13000"
ELASTICSEARCH = "http://127.0.0.1:19200"
KIBANA = "http://127.0.0.1:15601"
RECEIVER = "http://127.0.0.1:19099"

GRAFANA_USER = "clinicops"
GRAFANA_PASSWORD = os.environ.get("GRAFANA_ADMIN_PASSWORD", "clinicops-local-only")

CLINIC_COMPOSE = REPO_ROOT / "compose.yaml"
RABBIT_CONTAINER = "clinic-dev-rabbitmq-1"


def now() -> str:
    return datetime.now(UTC).isoformat()


def http(
    url: str,
    *,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict | None = None,
    timeout: int = 10,
):
    request = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, response.read()


def http_json(url: str, **kwargs):
    status, payload = http(url, **kwargs)
    return status, json.loads(payload or b"null")


def wait_for(label: str, probe, *, timeout: int, interval: float = 2.0):
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            value = probe()
            if value:
                return value
        except Exception as exc:  # noqa: BLE001 - probe failures are expected while booting
            last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(interval)
    raise RuntimeError(f"timeout waiting for {label} (last error: {last_error})")


def compose(*args: str, timeout: int = 900) -> subprocess.CompletedProcess:
    command = ["docker", "compose", "-f", str(COMPOSE_FILE), *args]
    return subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, timeout=timeout)


def clinic_compose(*args: str, timeout: int = 300) -> subprocess.CompletedProcess:
    command = ["docker", "compose", "-f", str(CLINIC_COMPOSE), *args]
    env = {**os.environ, **env_from_dotenv()}
    return subprocess.run(
        command, cwd=REPO_ROOT, capture_output=True, text=True, timeout=timeout, env=env
    )


def env_from_dotenv() -> dict:
    values = {}
    dotenv = REPO_ROOT / ".env"
    if dotenv.exists():
        for line in dotenv.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def prom_query(expr: str):
    status, payload = http_json(f"{PROMETHEUS}/api/v1/query?query={urllib.parse.quote(expr)}")
    if status != 200 or payload.get("status") != "success":
        raise RuntimeError(f"prometheus query failed: {expr}")
    return payload["data"]["result"]


def prom_targets():
    status, payload = http_json(f"{PROMETHEUS}/api/v1/targets?state=active")
    if status != 200 or payload.get("status") != "success":
        raise RuntimeError("prometheus targets query failed")
    return payload["data"]["activeTargets"]


def alertmanager_alerts():
    status, payload = http_json(f"{ALERTMANAGER}/api/v2/alerts")
    if status != 200:
        raise RuntimeError("alertmanager alerts query failed")
    return payload


def read_alert_receipts() -> list[dict]:
    if not ALERT_RECEIPTS.exists():
        return []
    rows = []
    for line in ALERT_RECEIPTS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def grafana_headers() -> dict:
    token = base64.b64encode(f"{GRAFANA_USER}:{GRAFANA_PASSWORD}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def ensure_kibana_data_view() -> dict:
    """Create the clinic-logs-* data view so Kibana can actually query the logs."""
    payload = {
        "data_view": {
            "title": "clinic-logs-*",
            "name": "Clinic logs",
            "timeFieldName": "@timestamp",
        },
        "override": True,
    }
    status, body = http(
        f"{KIBANA}/api/data_views/data_view",
        method="POST",
        body=json.dumps(payload).encode(),
        headers={"kbn-xsrf": "true", "content-type": "application/json"},
    )
    return {"status": status, "body": json.loads(body or b"{}")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-up", action="store_true", help="reuse an already running stack")
    parser.add_argument(
        "--keep-running", action="store_true", help="do not stop the stack at the end"
    )
    parser.add_argument("--alert-timeout", type=int, default=300)
    args = parser.parse_args()

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    if ALERT_RECEIPTS.exists():
        ALERT_RECEIPTS.unlink()

    receipt: dict = {
        "generated_at": now(),
        "compose_file": str(COMPOSE_FILE.relative_to(REPO_ROOT)).replace("\\", "/"),
        "steps": {},
        "checks": {},
        "verdict": "FAIL",
    }

    def record(step: str, **fields):
        receipt["steps"].setdefault(step, {}).update(fields)
        print(f"[{step}] " + json.dumps(fields, ensure_ascii=False)[:400], flush=True)

    def check(name: str, ok: bool, detail=None):
        receipt["checks"][name] = {"ok": bool(ok), "detail": detail}
        print(f"[check] {name}: {'PASS' if ok else 'FAIL'}", flush=True)
        return ok

    try:
        # 1. derive rules from the production file
        sys.path.insert(0, str(REPO_ROOT))
        from observability.local.derive_rules import derive  # noqa: PLC0415

        derivation = derive()
        record("derive_rules", **derivation)

        # 2. start the stack
        if not args.skip_up:
            env = {**os.environ, **env_from_dotenv()}
            command = ["docker", "compose", "-f", str(COMPOSE_FILE), "up", "-d", "--build"]
            result = subprocess.run(
                command, cwd=REPO_ROOT, capture_output=True, text=True, timeout=1800, env=env
            )
            record("compose_up", returncode=result.returncode, stderr=result.stderr[-2000:])
            if result.returncode != 0:
                raise RuntimeError("docker compose up failed")

        # 3. wait for every component
        wait_for("prometheus", lambda: http(f"{PROMETHEUS}/-/ready")[0] == 200, timeout=180)
        wait_for("alertmanager", lambda: http(f"{ALERTMANAGER}/-/ready")[0] == 200, timeout=180)
        wait_for("receiver", lambda: http(f"{RECEIVER}/health")[0] == 200, timeout=120)
        wait_for("grafana", lambda: http(f"{GRAFANA}/api/health")[0] == 200, timeout=240)
        wait_for(
            "elasticsearch", lambda: http(f"{ELASTICSEARCH}/_cluster/health")[0] == 200, timeout=420
        )
        wait_for("fluentd", lambda: http("http://127.0.0.1:24231/metrics")[0] == 200, timeout=300)
        wait_for("kibana", lambda: http(f"{KIBANA}/api/status")[0] == 200, timeout=600)
        record("components_ready", at=now())

        # 4. scrape targets
        targets = wait_for(
            "clinic targets up",
            lambda: (lambda t: t if t and all(x["health"] == "up" for x in t) else None)(
                prom_targets()
            ),
            timeout=180,
        )
        summary = [
            {
                "scrapeUrl": t["scrapeUrl"],
                "health": t["health"],
                "job": t["labels"].get("job"),
                "namespace": t["labels"].get("namespace"),
                "service": t["labels"].get("service"),
            }
            for t in targets
        ]
        record("targets", count=len(summary), targets=summary)
        check("all_targets_up", all(t["health"] == "up" for t in summary), summary)
        clinic_targets = [t for t in summary if t["job"] == "clinic"]
        check(
            "clinic_targets_present",
            len(clinic_targets) >= 3,
            [t["scrapeUrl"] for t in clinic_targets],
        )

        # 5. Grafana provisioning
        status, dashboards = http_json(
            f"{GRAFANA}/api/search?query=An%20Uy%C3%AAn", headers=grafana_headers()
        )
        record("grafana_dashboards", status=status, dashboards=dashboards)
        check("grafana_dashboard_provisioned", status == 200 and len(dashboards) >= 1, dashboards)
        status, datasources = http_json(f"{GRAFANA}/api/datasources", headers=grafana_headers())
        names = sorted(d["name"] for d in datasources) if status == 200 else []
        record("grafana_datasources", status=status, names=names)
        check(
            "grafana_datasources_provisioned", {"Prometheus", "Elasticsearch"} <= set(names), names
        )

        # 6. real failure -> FIRING
        before = prom_query('clinic_dependency_ready{dependency="rabbitmq"}')
        record("dependency_before", samples=before)
        stop = clinic_compose("stop", "rabbitmq")
        record("rabbitmq_stopped", returncode=stop.returncode, stderr=stop.stderr[-500:])

        firing = wait_for(
            "ClinicDependencyDown firing",
            lambda: (
                [
                    a
                    for a in alertmanager_alerts()
                    if a.get("labels", {}).get("alertname") == "ClinicDependencyDown"
                    and a.get("status", {}).get("state") == "active"
                ]
                or None
            ),
            timeout=args.alert_timeout,
            interval=3,
        )
        record("alertmanager_firing", alerts=firing)
        check("alertmanager_received_firing", bool(firing), firing)

        firing_receipt = wait_for(
            "firing webhook receipt",
            lambda: (
                [
                    r
                    for r in read_alert_receipts()
                    if r["alertname"] == "ClinicDependencyDown" and r["status"] == "firing"
                ]
                or None
            ),
            timeout=120,
            interval=2,
        )
        record("webhook_firing", receipts=firing_receipt)
        check("webhook_delivered_firing", bool(firing_receipt), firing_receipt)

        # 7. recovery -> RESOLVED
        start = clinic_compose("start", "rabbitmq")
        record("rabbitmq_started", returncode=start.returncode, stderr=start.stderr[-500:])
        wait_for(
            "dependency recovered",
            lambda: prom_query('clinic_dependency_ready{dependency="rabbitmq"}'),
            timeout=180,
            interval=3,
        )
        resolved = wait_for(
            "resolved webhook receipt",
            lambda: (
                [
                    r
                    for r in read_alert_receipts()
                    if r["alertname"] == "ClinicDependencyDown" and r["status"] == "resolved"
                ]
                or None
            ),
            timeout=args.alert_timeout,
            interval=3,
        )
        record("webhook_resolved", receipts=resolved)
        check("webhook_delivered_resolved", bool(resolved), resolved)

        # 8. logs really reach Elasticsearch and Kibana
        wait_for(
            "clinic logs in elasticsearch",
            lambda: http_json(f"{ELASTICSEARCH}/clinic-logs-*/_count")[1].get("count", 0) > 0,
            timeout=300,
            interval=5,
        )
        status, count = http_json(f"{ELASTICSEARCH}/clinic-logs-*/_count")
        record("elasticsearch_log_count", status=status, count=count.get("count"))
        check("logs_indexed", status == 200 and count.get("count", 0) > 0, count)

        status, sample = http_json(
            f"{ELASTICSEARCH}/clinic-logs-*/_search?size=3&sort=@timestamp:desc",
        )
        hits = [h["_source"] for h in sample.get("hits", {}).get("hits", [])]
        record("elasticsearch_sample", hits=hits)
        check(
            "logs_have_structured_fields",
            bool(hits) and all({"service", "level", "message"} <= set(h) for h in hits),
            hits,
        )

        status, kibana_status = http_json(f"{KIBANA}/api/status")
        record(
            "kibana_status",
            status=status,
            level=kibana_status.get("status", {}).get("overall", {}).get("level"),
        )
        check("kibana_available", status == 200, kibana_status.get("status", {}).get("overall"))

        data_view = ensure_kibana_data_view()
        record("kibana_data_view", **data_view)
        check("kibana_data_view_created", data_view["status"] in (200, 201), data_view["status"])

        status, found = http_json(f"{KIBANA}/api/data_views")
        titles = [v.get("title") for v in found.get("data_view", [])] if status == 200 else []
        record("kibana_data_views", status=status, titles=titles)
        check("kibana_data_view_present", "clinic-logs-*" in titles, titles)

        receipt["verdict"] = "PASS" if all(c["ok"] for c in receipt["checks"].values()) else "FAIL"
    except Exception as exc:  # noqa: BLE001 - the receipt must record the failure
        receipt["error"] = f"{type(exc).__name__}: {exc}"
        receipt["verdict"] = "FAIL"
        print(f"[error] {receipt['error']}", file=sys.stderr, flush=True)
    finally:
        receipt["finished_at"] = now()
        RECEIPT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"receipt: {RECEIPT}", flush=True)
        if not args.keep_running:
            compose("down", "--remove-orphans", timeout=300)

    return 0 if receipt["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
