"""Two explicit operator phases; scan failure or credential mismatch stops before apply."""

import argparse
import base64
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ci.cluster import context
from ci.common import OUTPUT, ROOT, run
from ci.observability import main as check_configuration
from observability.gates import check_scan_receipt, validate_secrets


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["foundation", "complete"])
    parser.add_argument("--expected-server", required=True)
    parser.add_argument("--secrets-file", required=True, type=Path)
    parser.add_argument(
        "--scan-receipt", type=Path, default=OUTPUT / "observability-images/metadata.json"
    )
    args = parser.parse_args()
    context(expected_server=args.expected_server)
    check_scan_receipt(args.scan_receipt, ROOT / "observability/versions.json")
    private = json.loads(args.secrets_file.read_text(encoding="utf-8"))
    validate_secrets(private)
    if args.phase == "complete":
        marker = json.loads(
            run(
                [
                    "kubectl",
                    "-n",
                    "monitoring",
                    "get",
                    "configmap",
                    "clinic-observability-configured",
                    "-o",
                    "json",
                ]
            ).stdout
        )["data"]
        expected = hashlib.sha256((ROOT / "observability/versions.json").read_bytes()).hexdigest()
        if marker.get("status") != "configured" or marker.get("versions_sha256") != expected:
            raise ValueError(
                "Complete requires the operator configuration phase for these versions"
            )
    pending = []
    for item in private["items"]:
        ns, name = item["metadata"]["namespace"], item["metadata"]["name"]
        result = subprocess.run(
            ["kubectl", "-n", ns, "get", "secret", name, "--ignore-not-found", "-o", "json"],
            text=True,
            capture_output=True,
            timeout=30,
        )
        if result.returncode:
            # A missing operator namespace is normal on the first foundation phase.
            namespace = subprocess.run(
                ["kubectl", "get", "namespace", ns, "--ignore-not-found", "-o", "name"],
                text=True,
                capture_output=True,
                timeout=30,
            )
            if namespace.returncode or namespace.stdout.strip():
                raise RuntimeError("Cannot safely inspect existing operator credentials")
        if result.stdout.strip():
            current = json.loads(result.stdout).get("data", {})
            if any(
                base64.b64decode(current.get(key, "")).decode() != value
                for key, value in item["stringData"].items()
            ):
                raise ValueError("Refusing to rotate an existing credential: " + ns + "/" + name)
        else:
            pending.append(item)
    for ns in ["staging", "production"]:
        run(["kubectl", "get", "namespace", ns])
    check_configuration()
    resources = json.loads((OUTPUT / "observability/rendered.json").read_text(encoding="utf-8"))

    def apply(items):
        if items:
            run(
                [
                    "kubectl",
                    "apply",
                    "--server-side",
                    "--field-manager=clinic-observability-operator",
                    "-f",
                    "-",
                ],
                input_text=json.dumps({"apiVersion": "v1", "kind": "List", "items": items}),
            )

    apply([item for item in resources if item["kind"] == "Namespace"])
    # The ordinary app deployer has no access to these operator Secret values.
    if pending:
        result = subprocess.run(
            ["kubectl", "create", "-f", "-"],
            input=json.dumps({"apiVersion": "v1", "kind": "List", "items": pending}),
            text=True,
            capture_output=True,
            timeout=60,
        )
        if result.returncode:
            raise RuntimeError(
                "Operator Secret creation failed; inspect names without printing values"
            )
    foundation = [
        item
        for item in resources
        if item["kind"] not in {"Namespace", "Deployment", "StatefulSet", "DaemonSet"}
    ]
    apply(foundation)
    run(
        [
            "kubectl",
            "-n",
            "logging",
            "wait",
            "certificate/elasticsearch-tls",
            "--for=condition=Ready",
            "--timeout=180s",
        ]
    )
    apply([item for item in resources if item["kind"] == "StatefulSet"])
    run(
        [
            "kubectl",
            "-n",
            "logging",
            "rollout",
            "status",
            "statefulset/elasticsearch",
            "--timeout=300s",
        ]
    )
    if args.phase == "foundation":
        print(
            "Foundation only. Configure restricted ES/PG users through the runbook, then run complete."
        )
        return
    apply([item for item in resources if item["kind"] in {"Deployment", "DaemonSet"}])
    for item in resources:
        if item["kind"] in {"Deployment", "DaemonSet"}:
            run(
                [
                    "kubectl",
                    "-n",
                    item["metadata"]["namespace"],
                    "rollout",
                    "status",
                    item["kind"].lower() + "/" + item["metadata"]["name"],
                    "--timeout=300s",
                ]
            )
    print(
        "Rollouts complete. External FIRING/RESOLVED receipts, real scrapes and log search still need acceptance evidence."
    )


if __name__ == "__main__":
    main()
