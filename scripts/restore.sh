#!/usr/bin/env bash
set -euo pipefail
umask 077
namespace="${1:?Usage: restore.sh staging BACKUP.dump clinic_restore_NAME}"
artifact="$(realpath -- "${2:?Missing backup}")"
restore_db="${3:?Missing NEW database name}"
[[ "$namespace" == staging ]] || { echo 'Automatic drill is restricted to staging; production cutover needs the restore runbook' >&2; exit 2; }
[[ "$artifact" == /srv/clinic-backups/staging/clinic-staging-*.dump ]] || exit 2
[[ "$restore_db" =~ ^clinic_restore_[a-zA-Z0-9_]{1,30}$ ]] || exit 2
[[ -s "$artifact" && -f "$artifact.sha256" ]] || exit 2
(cd "$(dirname "$artifact")" && sha256sum -c "$(basename "$artifact").sha256")
started="$(date +%s)"
# createdb refuses existing databases. Never drop/reset or restore into the live DB.
kubectl -n staging exec postgres-0 -- sh -ec \
  'export PGPASSWORD="$POSTGRES_PASSWORD"; exec createdb -U "$POSTGRES_USER" "$1"' sh "$restore_db"
kubectl -n staging exec -i postgres-0 -- sh -ec \
  'export PGPASSWORD="$POSTGRES_PASSWORD"; exec pg_restore -U "$POSTGRES_USER" -d "$1" --exit-on-error --no-owner --no-privileges' sh "$restore_db" < "$artifact"
kubectl -n staging exec postgres-0 -- sh -ec \
  'export PGPASSWORD="$POSTGRES_PASSWORD"; exec psql -U "$POSTGRES_USER" -d "$1" -v ON_ERROR_STOP=1 -c "SELECT version_num FROM alembic_version; SELECT count(*) AS appointments FROM appointments;"' sh "$restore_db"
printf '{"event":"restore_drill_complete","database":"%s","seconds":%s,"scope":"New staging database; no live cutover"}\n' "$restore_db" "$(( $(date +%s)-started ))"
