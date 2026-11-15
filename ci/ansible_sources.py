"""Validate checked-in controller-side copy/template sources before host changes."""

import hashlib
import re
from pathlib import Path

import yaml


def tasks_in(value):
    if isinstance(value, list):
        for task in value:
            if isinstance(task, dict):
                yield task
                for section in ("block", "rescue", "always"):
                    yield from tasks_in(task.get(section, []))


def check_local_sources(root: Path):
    root = root.resolve()
    roles = root / "infra/ansible/roles"
    if not roles.is_dir():
        raise ValueError("Missing Ansible roles directory")
    checked, remote = [], []
    files = sorted(set(roles.glob("*/tasks/**/*.yml")) | set(roles.glob("*/tasks/**/*.yaml")))
    for file in files:
        role = roles / file.relative_to(roles).parts[0]
        for task in tasks_in(yaml.safe_load(file.read_text(encoding="utf-8"))):
            for kind in ("copy", "template"):
                body = task.get("ansible.builtin." + kind, task.get(kind))
                if not isinstance(body, dict) or "src" not in body:
                    continue
                if body.get("remote_src") is True:
                    remote.append(
                        {
                            "task_file": file.relative_to(root).as_posix(),
                            "task": task.get("name"),
                            "reason": "remote_src is a target-host path",
                        }
                    )
                    continue
                source = body["src"]
                if not isinstance(source, str):
                    raise ValueError("Ansible local src must be a string")
                uses_item = bool(re.search(r"{{\s*item\s*}}", source))
                items = task.get("loop") if uses_item else [None]
                if (
                    not isinstance(items, list)
                    or uses_item
                    and not all(isinstance(item, str) for item in items)
                ):
                    raise ValueError("Controller source loop requires literal string items")
                for item in items:
                    rendered = re.sub(
                        r"{{\s*playbook_dir\s*}}", (root / "infra/ansible").as_posix(), source
                    )
                    if uses_item:
                        rendered = re.sub(r"{{\s*item\s*}}", lambda match: item, rendered)
                    if "{{" in rendered or "{%" in rendered:
                        raise ValueError(
                            "Unsupported controller source template; add explicit source validation before apply"
                        )
                    path = Path(rendered)
                    if not path.is_absolute():
                        path = role / ("templates" if kind == "template" else "files") / path
                    path = path.resolve()
                    if not path.is_relative_to(root):
                        raise ValueError("Ansible local source escapes the repository")
                    if not path.is_file():
                        raise ValueError(f"Missing Ansible local source: {path}")
                    checked.append(
                        {
                            "task_file": file.relative_to(root).as_posix(),
                            "task": task.get("name"),
                            "path": path.relative_to(root).as_posix(),
                            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        }
                    )
    return {
        "checked": checked,
        "remote_sources": remote,
        "scope": "Controller-side checked-in source paths only; not Ansible convergence, target-host existence or idempotency.",
    }
