#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$project_root"
export UV_CACHE_DIR="$project_root/.infra-local/uv-cache"
export UV_PYTHON_INSTALL_DIR="$project_root/.infra-local/python"
export TMPDIR="$project_root/.infra-local/temp"
export ANSIBLE_HOME="$project_root/.infra-local/ansible-home"
export ANSIBLE_COLLECTIONS_PATH="$project_root/.infra-local/collections"
mkdir -p "$TMPDIR"
uv_tool="$project_root/.infra-local/bin/linux/uv"
chmod 0755 "$uv_tool" "$project_root/.infra-local/bin/linux/terraform"
control_python="$(python3 -c 'import json; print(json.load(open("infra/versions.json"))["control_python"])')"
"$uv_tool" python install "$control_python"
if [[ ! -x .infra-local/ansible-venv/bin/python ]]; then
  "$uv_tool" venv --python "$control_python" .infra-local/ansible-venv
fi
if [[ ! -f infra/requirements-ansible.lock ]]; then
  "$uv_tool" pip compile --python-version 3.13 --no-header infra/requirements-ansible.txt -o infra/requirements-ansible.lock
fi
"$uv_tool" pip install --python .infra-local/ansible-venv/bin/python -r infra/requirements-ansible.lock
.infra-local/ansible-venv/bin/ansible-playbook --version
mapfile -t artifacts < <(python3 -c 'import json; d=json.load(open("infra/versions.json")); print("\n".join(".infra-local/collection-artifacts/"+v["filename"] for v in d["collections"].values()))')
.infra-local/ansible-venv/bin/ansible-galaxy collection install --offline --no-deps "${artifacts[@]}" -p "$ANSIBLE_COLLECTIONS_PATH"
