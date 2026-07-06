#!/usr/bin/env bash
# TASK-01-06 — backup: development database backup (pg_dump)
# This is a DEVELOPMENT backup helper. Production backup requires EPIC-13.
set -euo pipefail

PROJECT="Zayd"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
SERVICE="postgres"
DB_NAME="${PGDATABASE:-zayd_dev}"
DB_USER="${PGUSER:-zayd_dev}"

mkdir -p "${BACKUP_DIR}"

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_FILE="${BACKUP_DIR}/${PROJECT}-${DB_NAME}-${TIMESTAMP}.sql.gz"

echo "Backing up ${DB_NAME} database to ${BACKUP_FILE}"

# Prefer running inside the postgres container to avoid host-tool dependency
if docker compose exec -T "${SERVICE}" pg_isready -U "${DB_USER}" -d "${DB_NAME}" >/dev/null 2>&1; then
  docker compose exec -T "${SERVICE}" \
    pg_dump --no-owner --no-acl -U "${DB_USER}" -d "${DB_NAME}" \
    | gzip > "${BACKUP_FILE}"
else
  # Fall back to host pg_dump if the container is not running
  pg_dump --no-owner --no-acl -U "${DB_USER}" -h localhost -d "${DB_NAME}" \
    | gzip > "${BACKUP_FILE}"
fi

echo "Backup written to: ${BACKUP_FILE}"
echo "WARNING: This is a development backup helper."
echo "         Production backup policy will be implemented under EPIC-13."