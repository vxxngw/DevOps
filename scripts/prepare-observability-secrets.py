"""Prepare operator-owned Secrets locally; never apply or send an alert automatically."""

import argparse
import json
import secrets
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from observability.config import alertmanager_config


def build(chat_id, token):
    if not token.strip() or "\n" in token.strip():
        raise ValueError("Expected one Telegram token read from a private file")
    items = []

    def add(namespace, name, values):
        items.append(
            {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {"name": name, "namespace": namespace},
                "type": "Opaque",
                "stringData": values,
            }
        )

    add("monitoring", "grafana-admin", {"password": secrets.token_hex(24)})
    add(
        "monitoring",
        "alertmanager-config",
        {
            "telegram-token": token.strip(),
            "alertmanager.yml": yaml.safe_dump(alertmanager_config(chat_id)),
        },
    )
    add("logging", "elastic-admin", {"password": secrets.token_hex(24)})
    add(
        "logging",
        "kibana-auth",
        {"password": secrets.token_hex(24), "encryption-key": secrets.token_hex(32)},
    )
    add("logging", "fluentd-auth", {"password": secrets.token_hex(24)})
    for namespace in ["staging", "production"]:
        add(namespace, "postgres-metrics", {"password": secrets.token_hex(24)})
    return {"apiVersion": "v1", "kind": "List", "items": items}


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--telegram-chat-id", type=int, required=True)
    parser.add_argument("--telegram-token-file", type=Path, required=True)
    args = parser.parse_args()
    destination = root / ".infra-local/observability/secrets.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Fail before generation when input is missing; refuse rotation of an existing lab.
    data = build(args.telegram_chat_id, args.telegram_token_file.read_text(encoding="utf-8"))
    with destination.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2)
        stream.write("\n")
    destination.chmod(0o600)
    print("Private Secret file prepared; not applied and no notification sent.")


if __name__ == "__main__":
    main()
