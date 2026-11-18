#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$project_root"
export ANSIBLE_CONFIG="$project_root/infra/ansible/ansible.cfg"
export ANSIBLE_HOME="$project_root/.infra-local/ansible-home"
export ANSIBLE_COLLECTIONS_PATH="$project_root/.infra-local/collections"
while IFS= read -r -d '' script_file; do bash -n "$script_file"; done < <(find scripts -type f -name '*.sh' -print0)
for inventory in lab dev; do
  .infra-local/ansible-venv/bin/ansible-playbook -i "infra/ansible/inventories/$inventory/hosts.example.yml" infra/ansible/site.yml --syntax-check
done
.infra-local/ansible-venv/bin/python scripts/infra/check-vault-local.py
set +e
python3 scripts/infra/preflight-infra.py --output .infra-local/preflight.json
preflight_exit=$?
set -e
if [[ "$preflight_exit" != 0 && "$preflight_exit" != 2 ]]; then exit "$preflight_exit"; fi
printf 'PRECHECK_ONLY: Ansible/Bash syntax passed; VM preflight exit=%s (2 means BLOCKED)\n' "$preflight_exit"
