#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
export UV_CACHE_DIR="$project_root/.infra-local/uv-cache"
export UV_PYTHON_INSTALL_DIR="$project_root/.infra-local/python"
export TMPDIR="$project_root/.infra-local/temp"
mkdir -p "$TMPDIR"
uv_tool="$project_root/.infra-local/bin/linux/uv"
chmod 0755 "$uv_tool" "$project_root/.infra-local/bin/linux/terraform"
control_python="$(python3 -c 'import json; print(json.load(open("infra/versions.json"))["control_python"])')"
"$uv_tool" python install "$control_python"
if [[ ! -x .infra-local/control-venv/bin/python ]]; then
  "$uv_tool" venv --python "$control_python" .infra-local/control-venv
fi
"$uv_tool" pip install --python .infra-local/control-venv/bin/python -r infra/requirements-static.txt
.infra-local/bin/linux/terraform version
