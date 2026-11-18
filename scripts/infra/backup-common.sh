#!/usr/bin/env bash
# Shared path/transport guards. Sourcing this file performs no database operations.

canonical_backup_path() {
  local resolved
  resolved="$(realpath -m -- "$1")"
  case "${OSTYPE:-}" in
    msys*|cygwin*) cygpath -u -- "$resolved" ;;
    *) printf '%s\n' "$resolved" ;;
  esac
}

configure_backup_paths() {
  namespace="$1"
  case "$namespace" in
    staging|production)
      transport=kubectl
      backup_root="${CLINIC_BACKUP_ROOT:-/srv/clinic-backups}"
      [[ "$backup_root" == /srv/clinic-backups ]] || { echo 'Unexpected backup root' >&2; return 2; }
      metric_dir=/var/lib/node_exporter/textfile
      ;;
    dev)
      transport=docker-dev
      local repo_root allowed_root
      repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
      [[ -f "$repo_root/Jenkinsfile" && -f "$repo_root/pyproject.toml" ]] || { echo 'Dev backup needs a repository checkout' >&2; return 2; }
      allowed_root="$repo_root/.infra-local/db-backups"
      backup_root="$(canonical_backup_path "${CLINIC_BACKUP_ROOT:-$allowed_root}")"
      [[ "$backup_root" == "$allowed_root" || "$backup_root" == "$allowed_root/"* ]] || { echo 'Dev backup root must stay inside .infra-local/db-backups' >&2; return 2; }
      metric_dir="$backup_root/metrics"
      pg_container="${CLINIC_BACKUP_CONTAINER:-clinic-dev-postgres-1}"
      [[ "$pg_container" =~ ^[a-zA-Z0-9][a-zA-Z0-9_.-]*$ ]] || { echo 'Invalid container name' >&2; return 2; }
      ;;
    *) echo 'Only dev, staging or production backup profiles are supported' >&2; return 2 ;;
  esac
}

docker_cmd() {
  MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*' docker "$@"
}

validate_pg_transport() {
  if [[ "$transport" == docker-dev ]]; then
    local endpoint identity
    endpoint="${DOCKER_HOST:-$(docker_cmd context inspect --format '{{.Endpoints.docker.Host}}')}"
    case "$endpoint" in unix://*|npipe://*) ;; *) echo 'Dev backup is restricted to a local Docker engine' >&2; return 2 ;; esac
    identity="$(docker_cmd inspect --format '{{index .Config.Labels "com.docker.compose.project"}}|{{index .Config.Labels "com.docker.compose.service"}}|{{.State.Running}}' "$pg_container")"
    [[ "$identity" == 'clinic-dev|postgres|true' ]] || { echo 'Refusing a container outside the running clinic-dev Postgres service' >&2; return 2; }
  else
    command -v kubectl >/dev/null || { echo 'kubectl is required for cluster backup/restore' >&2; return 2; }
  fi
}

pg_exec() {
  local mode="$1"
  shift
  local flags=()
  [[ "$mode" == stdin ]] && flags+=(-i)
  if [[ "$transport" == docker-dev ]]; then
    docker_cmd exec "${flags[@]}" --user postgres "$pg_container" "$@"
  else
    kubectl -n "$namespace" exec "${flags[@]}" postgres-0 -- "$@"
  fi
}
