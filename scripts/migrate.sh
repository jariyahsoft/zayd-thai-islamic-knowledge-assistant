#!/usr/bin/env bash
# TASK-02-02 — development/test migration runner.
# Applies or rolls back PostgreSQL schema migrations.
set -euo pipefail

ACTION="${1:-up}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MIGRATIONS_DIR="${ROOT_DIR}/database/migrations"
SERVICE="${POSTGRES_SERVICE:-postgres}"
DB_USER="${PGUSER:-zayd_dev}"
DB_NAME="${PGDATABASE:-zayd_dev}"

usage() {
  cat <<'USAGE'
Usage: scripts/migrate.sh [up|down|reset]

Development/test migration runner for Zayd.

Actions:
  up     Apply pending schema migrations.
  down   Roll back all schema migrations.
  reset  Roll back and re-apply all schema migrations.

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

is_migration_applied() {
  local version="$1"
  local table_exists
  table_exists="$(run_psql_scalar "SELECT to_regclass('public.schema_migrations') IS NOT NULL;")"
  if [ "${table_exists}" != "t" ]; then
    return 1
  fi

  local version_exists
  version_exists="$(run_psql_scalar "SELECT EXISTS (SELECT 1 FROM schema_migrations WHERE version = '${version}');")"
  [ "${version_exists}" = "t" ]
}

apply_up_migrations() {
  local file version
  for file in "${MIGRATIONS_DIR}"/*.up.sql; do
    version="$(basename "${file}" .up.sql)"
    if is_migration_applied "${version}"; then
      echo "Migration ${version} already applied."
    else
      run_psql_file "${file}"
    fi
  done
}

apply_down_migrations() {
  local file
  while IFS= read -r file; do
    run_psql_file "${file}"
  done < <(find "${MIGRATIONS_DIR}" -maxdepth 1 -name '*.down.sql' | sort -r)
}

case "${ACTION}" in
  up)
    apply_up_migrations
    ;;
  down)
    apply_down_migrations
    ;;
  reset)
    apply_down_migrations
    apply_up_migrations
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
