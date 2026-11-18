"""Local crypto/loader test with synthetic values; not provisioned VM credential evidence."""

import json
import os
import secrets
import subprocess
from pathlib import Path

ROOT = next(
    (
        p
        for p in Path(__file__).resolve().parents
        if (p / "Jenkinsfile").is_file() and (p / "pyproject.toml").is_file()
    ),
    Path.cwd(),
)


def main():
    folder = ROOT / ".infra-local/vault-test"
    folder.mkdir(parents=True, exist_ok=True)
    password = folder / "password"
    # DrvFS may mark ordinary files executable. Use an intentional helper that
    # reads an ephemeral synthetic test password from the process environment.
    password.write_text('#!/bin/sh\nprintf "%s" "$CLINIC_VAULT_UNIT_PASSWORD"\n')
    password.chmod(0o755)
    vault = folder / "vault.yml"
    vault.write_text("vault_unit_marker: synthetic-only\n")
    plaintext = folder / "plain.yml"
    plaintext.write_text("vault_unit_marker: synthetic-only\n")
    executable = ROOT / ".infra-local/ansible-venv/bin"
    environment = os.environ.copy()
    environment["CLINIC_VAULT_UNIT_PASSWORD"] = secrets.token_hex(32)
    environment.update(
        ANSIBLE_CONFIG=str(ROOT / "infra/ansible/ansible.cfg"),
        ANSIBLE_HOME=str(ROOT / ".infra-local/ansible-home"),
        ANSIBLE_COLLECTIONS_PATH=str(ROOT / ".infra-local/collections"),
    )
    try:
        subprocess.run(
            [executable / "ansible-vault", "encrypt", vault, "--vault-password-file", password],
            env=environment,
            check=True,
            capture_output=True,
        )
        play = folder / "test.yml"
        play.write_text(
            "- hosts: localhost\n  connection: local\n  gather_facts: false\n  vars:\n    clinic_vault_file: "
            + str(vault)
            + "\n  tasks:\n    - import_tasks: "
            + str(ROOT / "infra/ansible/tasks/load-vault.yml")
            + "\n    - assert:\n        that: vault_unit_marker == 'synthetic-only'\n"
        )
        command = [
            executable / "ansible-playbook",
            "-i",
            "localhost,",
            play,
            "--vault-password-file",
            password,
        ]
        positive = subprocess.run(command, env=environment, capture_output=True, text=True)
        play.write_text(play.read_text().replace(str(vault), str(plaintext)))
        negative = subprocess.run(command, env=environment, capture_output=True, text=True)
        (folder / "positive.log").write_text(positive.stdout + positive.stderr)
        (folder / "negative.log").write_text(negative.stdout + negative.stderr)
        result = {
            "scope": "Synthetic local Vault encryption/decryption and plaintext rejection; no VM or real secrets",
            "encrypted_exit": positive.returncode,
            "plaintext_exit": negative.returncode,
            "verified": positive.returncode == 0 and negative.returncode != 0,
        }
        (folder / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))
        return 0 if result["verified"] else 1
    finally:
        password.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
