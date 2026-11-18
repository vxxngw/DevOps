#!/usr/bin/env bash
set -euo pipefail
umask 077
namespace="${1:?Usage: restore.sh dev|staging BACKUP.dump clinic_restore_NAME}"
restore_db="${3:?Missing NEW database name}"
[[ "$namespace" == staging || "$namespace" == dev ]] || { echo 'Automatic drill is restricted to dev/staging; production cutover needs the restore runbook' >&2; exit 2; }
[[ "$restore_db" =~ ^clinic_restore_[a-zA-Z0-9_]{1,30}$ ]] || { echo 'Restore target must be a new clinic_restore_ database' >&2; exit 2; }
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
helper="$script_dir/backup-common.sh"
[[ -f "$helper" ]] || helper="$script_dir/clinic-backup-common.sh"
# shellcheck source=backup-common.sh
source "$helper"
configure_backup_paths "$namespace"
artifact="$(realpath -- "${2:?Missing backup}")"
artifact="$(canonical_backup_path "$artifact")"
[[ "$(dirname -- "$artifact")" == "$backup_root/$namespace" ]] || exit 2
[[ "$(basename -- "$artifact")" =~ ^clinic-$namespace-[0-9]{8}T[0-9]{6}Z\.dump$ ]] || exit 2
[[ -s "$artifact" && -f "$artifact.sha256" ]] || exit 2
(cd "$(dirname "$artifact")" && sha256sum -c "$(basename "$artifact").sha256")
validate_pg_transport
started="$(date +%s)"
# createdb refuses existing databases. Never drop/reset or restore into the live DB.
pg_exec plain sh -ec \
  'export PGPASSWORD="$POSTGRES_PASSWORD"; exec createdb -U "$POSTGRES_USER" "$1"' sh "$restore_db"
printf '{"event":"restore_database_created","database":"%s"}\n' "$restore_db"
pg_exec stdin sh -ec \
  'export PGPASSWORD="$POSTGRES_PASSWORD"; exec pg_restore -U "$POSTGRES_USER" -d "$1" --exit-on-error --no-owner --no-privileges' sh "$restore_db" < "$artifact"
pg_exec plain sh -ec \
  'export PGPASSWORD="$POSTGRES_PASSWORD"; exec psql -U "$POSTGRES_USER" -d "$1" -v ON_ERROR_STOP=1 -c "SELECT version_num FROM alembic_version; SELECT count(*) AS appointments FROM appointments;"' sh "$restore_db"
printf '{"event":"restore_drill_complete","database":"%s","seconds":%s,"transport":"%s","scope":"New dev/staging database; no live cutover"}\n' "$restore_db" "$(( $(date +%s)-started ))" "$transport"
