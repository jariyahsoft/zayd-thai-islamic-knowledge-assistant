#!/usr/bin/env bash
# TASK-01-06 — restore: development database restore (pg_restore from gzip)
# Requires explicit confirmation before overwriting the current database.
# This is a DEVELOPMENT restore helper. Production restore requires EPIC-13.
set -euo pipefail

PROJECT="Zayd"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
SERVICE="postgres"
DB_NAME="${PGDATABASE:-zayd_dev}"
DB_USER="${PGUSER:-zayd_dev}"

RESTORE_FILE="${1:-}"

if [ -z "${RESTORE_FILE}" ]; then
  echo "Usage: $0 <backup-file>"
  echo ""
  echo "Restore a ${PROJECT} development database from a .sql.gz backup file."
  echo "Available backups:"
  ls -1 "${BACKUP_DIR}"/*.sql.gz 2>/dev/null || echo "(no backups found in ${BACKUP_DIR}/)"
  exit 1
fi

if [ ! -f "${RESTORE_FILE}" ]; then
  echo "Error: backup file not found: ${RESTORE_FILE}" >&2
  exit 1
fi

echo "=== RESTORE WARNING ==="
echo "This will OVERWRITE the current '${DB_NAME}' database with data from:"
echo "  ${RESTORE_FILE}"
echo ""
read -r -p "Type the database name (${DB_NAME}) to confirm: " CONFIRM
if [ "${CONFIRM}" != "${DB_NAME}" ]; then
  echo "Confirmation did not match. Aborting."
  exit 1
fi

echo "Restoring ${DB_NAME} from ${RESTORE_FILE}…"

if docker compose exec -T "${SERVICE}" pg_isready -U "${DB_USER}" -d "${DB_NAME}" >/dev/null 2>&1; then
  # Drop and recreate the target database for a clean restore
  docker compose exec -T "${SERVICE}" psql -U "${DB_USER}" -d postgres \
    -c "SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '${DB_NAME}' AND pid <> pg_backend_pid();" \
    -c "DROP DATABASE IF EXISTS \"${DB_NAME}\";" \
    -c "CREATE DATABASE \"${DB_NAME}\" OWNER \"${DB_USER}\";"
  gunzip -c "${RESTORE_FILE}" | docker compose exec -T "${SERVICE}" \
    psql -U "${DB_USER}" -d "${DB_NAME}"
else
  # Fall back to host psql
  gunzip -c "${RESTORE_FILE}" | psql -U "${DB_USER}" -h localhost -d "${DB_NAME}"
fi

echo "Restore completed from: ${RESTORE_FILE}"
echo "WARNING: This is a development restore helper."
echo "         Production restore policy will be implemented under EPIC-13."