"""Generate separate local namespace credentials; never rotates existing DB secrets."""

import argparse
import base64
import json
import os
import secrets
from pathlib import Path

ROOT = next(
    (
        p
        for p in Path(__file__).resolve().parents
        if (p / "Jenkinsfile").is_file() and (p / "pyproject.toml").is_file()
    ),
    Path.cwd(),
)


def manifest(namespace, registry_token):
    if namespace not in {"staging", "production"} or len(registry_token.strip()) < 20:
        raise ValueError("Provide a target namespace and actual registry credential")
    database_password = secrets.token_hex(24)
    broker_password = secrets.token_hex(24)

    def secret(name, values, kind="Opaque"):
        return {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {"name": name, "namespace": namespace},
            "type": kind,
            "stringData": values,
        }

    registry = {
        "auths": {
            "ghcr.io": {
                "auth": base64.b64encode(
                    (
                        json.loads((ROOT / "ci/tools.json").read_text(encoding="utf-8"))[
                            "registry"
                        ].split("/", 1)[1]
                        + ":"
                        + registry_token.strip()
                    ).encode()
                ).decode()
            }
        }
    }
    return {
        "apiVersion": "v1",
        "kind": "List",
        "items": [
            secret(
                "postgres-auth",
                {
                    "POSTGRES_USER": "clinic",
                    "POSTGRES_DB": "clinic",
                    "POSTGRES_PASSWORD": database_password,
                },
            ),
            secret(
                "rabbitmq-auth",
                {
                    "RABBITMQ_DEFAULT_USER": "clinic",
                    "RABBITMQ_DEFAULT_PASS": broker_password,
                    "RABBITMQ_DEFAULT_VHOST": "clinic-" + namespace,
                    "RABBITMQ_ERLANG_COOKIE": secrets.token_hex(32),
                },
            ),
            secret(
                "app-secrets",
                {
                    "DATABASE_URL": f"postgresql+psycopg://clinic:{database_password}@postgres:5432/clinic",
                    "RABBITMQ_URL": f"amqp://clinic:{broker_password}@rabbitmq:5672/clinic-{namespace}",
                    "JWT_SECRET": secrets.token_hex(32),
                },
            ),
            secret(
                "registry-pull",
                {".dockerconfigjson": json.dumps(registry)},
                "kubernetes.io/dockerconfigjson",
            ),
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("namespace", choices=["staging", "production"])
    parser.add_argument("--registry-token-file", default=".registry-token")
    args = parser.parse_args()
    destination = ROOT / ".infra-local/secrets" / (args.namespace + ".json")
    if destination.exists():
        raise RuntimeError(
            "Existing secrets retained. Rotation must follow the runbook, not regeneration"
        )
    token = Path(args.registry_token_file).read_text(encoding="utf-8-sig").strip()
    data = manifest(args.namespace, token)
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        json.dump(data, output)
    print("Created private namespace secrets file:", destination)
    print(
        "No cluster changes. Operator must use kubectl create, never replace existing DB credentials"
    )


if __name__ == "__main__":
    main()
