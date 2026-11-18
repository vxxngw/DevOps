"""Operator-only cluster bootstrap. Never called with the namespace Jenkins deployer."""

import argparse
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
from ci.cluster import context  # noqa: E402
from ci.common import ROOT, run  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-server", required=True)
    args = parser.parse_args()
    context(expected_server=args.expected_server)
    nodes = json.loads(run(["kubectl", "get", "nodes", "-o", "json"]).stdout)["items"]
    if len(nodes) != 2 or any(not node["metadata"]["name"].startswith("anuyen-") for node in nodes):
        raise ValueError("This bootstrap targets only the dedicated two-node An Uyen cluster")
    versions = json.loads((ROOT / "infra/versions.json").read_text(encoding="utf-8"))
    for name, item in versions["addons"].items():
        path = ROOT / ".infra-local/vendor" / (name + ".yaml")
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("Addon manifest checksum mismatch")
        run(["kubectl", "apply", "--server-side", "--field-manager=clinic-bootstrap", "-f", path])
    for namespace, deployments in [
        ("cert-manager", ["cert-manager", "cert-manager-cainjector", "cert-manager-webhook"]),
        ("keda", ["keda-operator", "keda-metrics-apiserver", "keda-admission"]),
    ]:
        for deployment in deployments:
            run(
                [
                    "kubectl",
                    "-n",
                    namespace,
                    "rollout",
                    "status",
                    "deployment/" + deployment,
                    "--timeout=240s",
                ]
            )
    for filename in ["namespaces-rbac.yaml", "local-ca.yaml"]:
        run(["kubectl", "apply", "-f", ROOT / "deploy/k8s/bootstrap" / filename])
    run(
        [
            "kubectl",
            "-n",
            "cert-manager",
            "wait",
            "--for=condition=Ready",
            "certificate/clinic-root-ca",
            "--timeout=120s",
        ]
    )
    run(
        [
            "kubectl",
            "wait",
            "--for=condition=Ready",
            "clusterissuer/clinic-lab-ca",
            "--timeout=120s",
        ]
    )
    print(
        "Cluster addons/RBAC/lab CA reconciled; client trust and application smoke remain separate"
    )


if __name__ == "__main__":
    main()
