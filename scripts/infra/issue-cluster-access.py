"""Operator-only short-lived namespace kubeconfigs; never prints tokens or API private keys."""

import argparse
import base64
import json
import os
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
    data = json.loads(run(["kubectl", "config", "view", "--minify", "--raw", "-o", "json"]).stdout)
    cluster = data["clusters"][0]["cluster"]
    if "certificate-authority-data" not in cluster:
        cluster["certificate-authority-data"] = base64.b64encode(
            Path(cluster["certificate-authority"]).read_bytes()
        ).decode()
        cluster.pop("certificate-authority")
    destination = ROOT / ".infra-local/access"
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    for namespace in ["staging", "production"]:
        token = run(
            ["kubectl", "-n", namespace, "create", "token", "clinic-deployer", "--duration=8h"]
        ).stdout.strip()
        configuration = {
            "apiVersion": "v1",
            "kind": "Config",
            "clusters": [{"name": "clinic", "cluster": cluster}],
            "users": [{"name": "clinic-deployer", "user": {"token": token}}],
            "contexts": [
                {
                    "name": namespace,
                    "context": {
                        "cluster": "clinic",
                        "user": "clinic-deployer",
                        "namespace": namespace,
                    },
                }
            ],
            "current-context": namespace,
        }
        path = destination / (namespace + ".json")
        if path.exists():
            raise RuntimeError(
                "Existing kubeconfig retained; rotate explicitly after checking Jenkins credential"
            )
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as output:
            json.dump(configuration, output)
        print("Wrote namespace-only short-lived kubeconfig:", path)
    certificate = run(
        [
            "kubectl",
            "-n",
            "cert-manager",
            "get",
            "secret",
            "clinic-root-ca",
            "-o",
            "jsonpath={.data.tls\\.crt}",
        ]
    ).stdout.strip()
    (destination / "lab-root-ca.crt").write_bytes(base64.b64decode(certificate))
    print("Exported public lab CA; client trust installation remains a separate operator step")


if __name__ == "__main__":
    main()
