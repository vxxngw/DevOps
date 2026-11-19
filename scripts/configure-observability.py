"""Operator action after cluster install: restricted ES writer and PostgreSQL metric roles."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ci.cluster import context
from ci.common import ROOT, now, run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-server", required=True)
    parser.add_argument("--secrets-file", required=True, type=Path)
    parser.add_argument("--elastic-url", default="https://elasticsearch.logging.svc:19200")
    parser.add_argument("--ca-file", required=True, type=Path)
    args = parser.parse_args()
    context(expected_server=args.expected_server)
    url = urlparse(args.elastic_url)
    if url.scheme != "https" or url.hostname != "elasticsearch.logging.svc" or url.username:
        raise ValueError("Use the verified lab Elasticsearch hostname, including for port-forward")
    data = json.loads(args.secrets_file.read_text(encoding="utf-8"))
    credentials = {
        (item["metadata"]["namespace"], item["metadata"]["name"]): item["stringData"]
        for item in data["items"]
    }
    password = credentials[("logging", "elastic-admin")]["password"]
    with httpx.Client(
        verify=str(args.ca_file), auth=("elastic", password), timeout=30, trust_env=False
    ) as client:

        def send(path, body):
            response = client.put(args.elastic_url + path, json=body)
            if not response.is_success:
                raise RuntimeError(
                    "Elasticsearch configuration failed; HTTP " + str(response.status_code)
                )

        send(
            "/_ilm/policy/clinic-logs",
            {"policy": {"phases": {"delete": {"min_age": "7d", "actions": {"delete": {}}}}}},
        )
        send(
            "/_index_template/clinic-logs",
            {
                "index_patterns": ["clinic-logs-*"],
                "template": {
                    "settings": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                        "index.lifecycle.name": "clinic-logs",
                    },
                    "mappings": {
                        "properties": {
                            **{
                                key: {"type": "keyword"}
                                for key in [
                                    "namespace",
                                    "service",
                                    "container",
                                    "pod",
                                    "level",
                                    "request_id",
                                    "correlation_id",
                                    "event_id",
                                    "environment",
                                    "status",
                                ]
                            },
                            "timestamp": {"type": "date"},
                            "message": {"type": "text"},
                        }
                    },
                },
            },
        )
        send(
            "/_security/role/clinic-log-writer",
            {
                "cluster": ["monitor"],
                "indices": [{"names": ["clinic-logs-*"], "privileges": ["create_index", "write"]}],
            },
        )
        send(
            "/_security/user/fluentd_writer",
            {
                "password": credentials[("logging", "fluentd-auth")]["password"],
                "roles": ["clinic-log-writer"],
            },
        )
        response = client.post(
            args.elastic_url + "/_security/user/kibana_system/_password",
            json={"password": credentials[("logging", "kibana-auth")]["password"]},
        )
        if not response.is_success:
            raise RuntimeError("Kibana service credential configuration failed")
    for namespace in ["staging", "production"]:
        password = credentials[(namespace, "postgres-metrics")]["password"]
        if not re.fullmatch("[a-f0-9]{48}", password):
            raise ValueError("Unexpected generated metric-role password format")
        sql = "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='clinic_metrics') THEN CREATE ROLE clinic_metrics LOGIN; END IF; END $$;\n"
        sql += (
            "ALTER ROLE clinic_metrics NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD '"
            + password
            + "';\n"
        )
        sql += "GRANT pg_monitor TO clinic_metrics; GRANT CONNECT ON DATABASE clinic TO clinic_metrics;\n"
        result = subprocess.run(
            [
                "kubectl",
                "-n",
                namespace,
                "exec",
                "-i",
                "postgres-0",
                "--",
                "sh",
                "-ec",
                'export PGPASSWORD="$POSTGRES_PASSWORD"; exec psql -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"',
            ],
            input=sql,
            text=True,
            capture_output=True,
            timeout=60,
        )
        if result.returncode:
            # Never echo server error text or SQL containing generated passwords.
            raise RuntimeError("Metric-role configuration failed in " + namespace)
    marker = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {"name": "clinic-observability-configured", "namespace": "monitoring"},
        "data": {
            "status": "configured",
            "at_utc": now(),
            "versions_sha256": hashlib.sha256(
                (ROOT / "observability/versions.json").read_bytes()
            ).hexdigest(),
        },
    }
    run(
        [
            "kubectl",
            "apply",
            "--server-side",
            "--field-manager=clinic-observability-operator",
            "-f",
            "-",
        ],
        input_text=json.dumps(marker),
    )
    print(
        "Operator configuration completed; verify exporters, ingestion and dashboards separately."
    )


if __name__ == "__main__":
    main()
