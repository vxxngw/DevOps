#!/usr/bin/env bash
set -euo pipefail
umask 077
namespace="${1:?Usage: backup.sh staging|production}"
[[ "$namespace" == staging || "$namespace" == production ]] || exit 2
backup_root="${CLINIC_BACKUP_ROOT:-/srv/clinic-backups}"
[[ "$backup_root" == /srv/clinic-backups ]] || { echo 'Unexpected backup root' >&2; exit 2; }
retention="${CLINIC_BACKUP_RETENTION_DAYS:-7}"
[[ "$retention" =~ ^[1-9][0-9]?$ ]] || exit 2
metric_dir=/var/lib/node_exporter/textfile
write_status() {
  [[ -d "$metric_dir" ]] || return 0
  local status_file="$metric_dir/clinic-backup-last-run-$namespace.prom"
  printf 'clinic_backup_last_run_success{namespace="%s"} %s\n' "$namespace" "$1" > "$status_file.tmp"
  chmod 0644 "$status_file.tmp"
  mv -- "$status_file.tmp" "$status_file"
}
trap 'status=$?; write_status 0 || true; exit "$status"' ERR
mkdir -p "$backup_root/$namespace"
destination="$(realpath "$backup_root/$namespace")"
[[ "$destination" == "$backup_root/$namespace" ]] || exit 2
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
artifact="$destination/clinic-$namespace-$stamp.dump"
[[ ! -e "$artifact" && ! -e "$artifact.tmp" ]] || exit 2
trap 'rm -f -- "$artifact.tmp"' EXIT
kubectl -n "$namespace" exec postgres-0 -- sh -ec \
  'export PGPASSWORD="$POSTGRES_PASSWORD"; exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$artifact.tmp"
[[ -s "$artifact.tmp" ]] || { echo 'Empty backup' >&2; exit 1; }
mv -- "$artifact.tmp" "$artifact"
(cd "$destination" && sha256sum "$(basename "$artifact")" > "$(basename "$artifact").sha256")
find "$destination" -maxdepth 1 -type f -name "clinic-$namespace-????????T??????Z.dump*" -mtime "+$retention" -delete
if [[ -d "$metric_dir" ]]; then
  printf 'clinic_backup_last_success_timestamp_seconds{namespace="%s"} %s\n' "$namespace" "$(date +%s)" > "$metric_dir/clinic-backup-$namespace.prom.tmp"
  chmod 0644 "$metric_dir/clinic-backup-$namespace.prom.tmp"
  mv -- "$metric_dir/clinic-backup-$namespace.prom.tmp" "$metric_dir/clinic-backup-$namespace.prom"
fi
write_status 1
printf '{"event":"backup_complete","namespace":"%s","artifact":"%s"}\n' "$namespace" "$artifact"
