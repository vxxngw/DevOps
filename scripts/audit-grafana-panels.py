"""Audit every Grafana panel against the live Prometheus/Elasticsearch data.

For each panel in observability/grafana/dashboards/operations.json this script
runs the panel's own targets through the Grafana datasource proxy (so the query
is evaluated exactly as the UI would evaluate it) and records whether the panel
returns data or "No data".

Output: observability/local/evidence/panel-audit.json
Exit code: 0 when every panel returns data, 1 otherwise.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = REPO_ROOT / "observability" / "grafana" / "dashboards" / "operations.json"
OUTPUT = REPO_ROOT / "observability" / "local" / "evidence" / "panel-audit.json"

GRAFANA = os.environ.get("GRAFANA_URL", "http://127.0.0.1:13000")
GRAFANA_USER = os.environ.get("GRAFANA_USER", "clinicops")
GRAFANA_PASSWORD = os.environ.get("GRAFANA_ADMIN_PASSWORD", "clinicops-local-only")
PROM_UID = "clinic-prometheus"
ES_UID = "clinic-elasticsearch"


def headers() -> dict:
    token = base64.b64encode(f"{GRAFANA_USER}:{GRAFANA_PASSWORD}".encode()).decode()
    return {"Authorization": f"Basic {token}", "content-type": "application/json"}


def post(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode(), method="POST", headers=headers()
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read() or b"{}")


def query_prometheus(expr: str) -> dict:
    url = f"{GRAFANA}/api/datasources/proxy/uid/{PROM_UID}/api/v1/query?query={urllib.parse.quote(expr)}"
    request = urllib.request.Request(url, headers=headers())
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read() or b"{}")


def query_elasticsearch(expr: str) -> dict:
    return post(
        f"{GRAFANA}/api/ds/query",
        {
            "queries": [
                {
                    "refId": "A",
                    "datasource": {"type": "elasticsearch", "uid": ES_UID},
                    "query": expr,
                    "metrics": [{"type": "count", "id": "1"}],
                    "bucketAggs": [
                        {
                            "type": "date_histogram",
                            "id": "2",
                            "field": "@timestamp",
                            "settings": {"interval": "auto"},
                        }
                    ],
                    "timeField": "@timestamp",
                }
            ],
            "from": "now-15m",
            "to": "now",
        },
    )


def series_count(payload: dict) -> int:
    results = payload.get("data", {}).get("result", [])
    return len(results)


def es_frame_count(payload: dict) -> int:
    frames = payload.get("results", {}).get("A", {}).get("frames", [])
    total = 0
    for frame in frames:
        values = frame.get("data", {}).get("values", [])
        if values:
            total += len(values[0])
    return total


def template_values(dashboard: dict) -> dict:
    """Return the value Grafana would substitute for each dashboard variable.

    Without this every `$namespace` query is sent literally and matches nothing,
    so the audit would report "No data" for panels that render fine in the UI.
    NAMESPACE (env) overrides the dashboard's saved selection.
    """
    values = {}
    for var in dashboard.get("templating", {}).get("list", []):
        current = var.get("current", {}).get("value")
        if isinstance(current, list):
            current = "|".join(current)
        values[var["name"]] = current or ""
    if os.environ.get("NAMESPACE"):
        values["namespace"] = os.environ["NAMESPACE"]
    values.setdefault("__rate_interval", "1m")
    values.setdefault("__interval", "15s")
    return values


def interpolate(expr: str, values: dict) -> str:
    # Longest names first so `$__rate_interval` is not eaten by `$__rate`.
    for name in sorted(values, key=len, reverse=True):
        expr = expr.replace("${" + name + "}", values[name]).replace("$" + name, values[name])
    return expr


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    dashboard = json.loads(DASHBOARD.read_text(encoding="utf-8"))
    variables = template_values(dashboard)
    panels = dashboard["panels"]
    rows = []
    for index, panel in enumerate(panels):
        title = panel.get("title", f"panel-{index}")
        targets = panel.get("targets", [])
        entry = {"index": index, "title": title, "type": panel.get("type"), "targets": []}
        for target in targets:
            expr = interpolate(target.get("expr") or target.get("query") or "", variables)
            datasource = target.get("datasource") or panel.get("datasource") or {}
            uid = datasource.get("uid") if isinstance(datasource, dict) else None
            try:
                if uid == ES_UID:
                    payload = query_elasticsearch(expr)
                    count = es_frame_count(payload)
                else:
                    payload = query_prometheus(expr)
                    count = series_count(payload)
                entry["targets"].append(
                    {"expr": expr, "datasource": uid, "series": count, "ok": count > 0}
                )
            except Exception as exc:  # noqa: BLE001 - record the failure
                entry["targets"].append(
                    {"expr": expr, "datasource": uid, "error": f"{type(exc).__name__}: {exc}", "ok": False}
                )
        entry["ok"] = bool(entry["targets"]) and all(t["ok"] for t in entry["targets"])
        rows.append(entry)
        print(f"[{index:02d}] {'PASS' if entry['ok'] else 'NO DATA'} {title}", flush=True)

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "dashboard": str(DASHBOARD.relative_to(REPO_ROOT)).replace("\\", "/"),
        "variables": variables,
        "panel_count": len(panels),
        "panels_with_data": sum(1 for r in rows if r["ok"]),
        "panels_without_data": [r["title"] for r in rows if not r["ok"]],
        "panels": rows,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"report: {OUTPUT}", flush=True)
    print(f"{report['panels_with_data']}/{report['panel_count']} panels with data", flush=True)
    return 0 if report["panels_with_data"] == report["panel_count"] else 1


if __name__ == "__main__":
    sys.exit(main())
