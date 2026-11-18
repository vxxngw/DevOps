#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
for script_file in scripts/*.sh; do bash -n "$script_file"; done
terraform="$project_root/.infra-local/bin/linux/terraform"
"$terraform" -chdir=infra/terraform fmt -check -recursive
"$terraform" -chdir=infra/terraform validate
set +e
python3 scripts/preflight-infra.py --output .infra-local/preflight.json
preflight_exit=$?
set -e
if [[ "$preflight_exit" != 0 && "$preflight_exit" != 2 ]]; then exit "$preflight_exit"; fi
printf 'PRECHECK_ONLY: Terraform/Bash checks passed; VM preflight exit=%s (2 means BLOCKED)\n' "$preflight_exit"
