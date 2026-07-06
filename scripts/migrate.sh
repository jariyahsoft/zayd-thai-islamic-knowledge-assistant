#!/usr/bin/env bash
# TASK-02-02 — development/test migration runner.
# Applies or rolls back the initial PostgreSQL schema migration.
set -euo pipefail

ACTION="${1:-up}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UP_FILE="${ROOT_DIR}/database/migrations/0001_initial_core_domain.up.sql"
DOWN_FILE="${ROOT_DIR}/database/migrations/0001_initial_core_domain.down.sql"
SERVICE="${POSTGRES_SERVICE:-postgres}"
DB_USER="${PGUSER:-zayd_dev}"
DB_NAME="${PGDATABASE:-zayd_dev}"

usage() {
  cat <<'USAGE'
Usage: scripts/migrate.sh [up|down|reset]

Development/test migration runner for Zayd.

Actions:
  up     Apply the initial schema migration.
  down   Roll back the initial schema migration.
  reset  Roll back and re-apply the initial schema migration.

The runner prefers the Docker Compose postgres service and falls back to host psql.
USAGE
}

run_psql_file() {
  local file="$1"
  if docker compose ps --services --filter status=running 2>/dev/null | grep -qx "${SERVICE}"; then
    docker compose exec -T "${SERVICE}" psql -v ON_ERROR_STOP=1 -U "${DB_USER}" -d "${DB_NAME}" < "${file}"
  else
    psql -v ON_ERROR_STOP=1 -U "${DB_USER}" -d "${DB_NAME}" -f "${file}"
  fi
}

run_psql_scalar() {
  local sql="$1"
  if docker compose ps --services --filter status=running 2>/dev/null | grep -qx "${SERVICE}"; then
    docker compose exec -T "${SERVICE}" psql -qAt -v ON_ERROR_STOP=1 -U "${DB_USER}" -d "${DB_NAME}" -c "${sql}"
  else
    psql -qAt -v ON_ERROR_STOP=1 -U "${DB_USER}" -d "${DB_NAME}" -c "${sql}"
  fi
}

is_initial_migration_applied() {
  local table_exists
  table_exists="$(run_psql_scalar "SELECT to_regclass('public.schema_migrations') IS NOT NULL;")"
  if [ "${table_exists}" != "t" ]; then
    return 1
  fi

  local version_exists
  version_exists="$(run_psql_scalar "SELECT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '0001_initial_core_domain');")"
  [ "${version_exists}" = "t" ]
}

case "${ACTION}" in
  up)
    if is_initial_migration_applied; then
      echo "Migration 0001_initial_core_domain already applied."
    else
      run_psql_file "${UP_FILE}"
    fi
    ;;
  down)
    run_psql_file "${DOWN_FILE}"
    ;;
  reset)
    run_psql_file "${DOWN_FILE}"
    run_psql_file "${UP_FILE}"
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    echo "Error: unknown migration action '${ACTION}'." >&2
    usage >&2
    exit 2
    ;;
esac
