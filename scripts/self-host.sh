#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/infra/compose/minimal.yml"
ENV_FILE="${SELF_HOST_ENV_FILE:-${ROOT_DIR}/.env.self-host}"
ACTION="${1:-help}"

fail() { printf 'self_host_error code=%s message=%s\n' "$1" "$2" >&2; exit 1; }
require_command() { command -v "$1" >/dev/null 2>&1 || fail "dependency_unavailable" "$1 is required"; }
env_value() { awk -F= -v key="$1" '$1 == key {sub(/^[^=]*=/, ""); print; exit}' "${ENV_FILE}"; }
compose() { docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"; }

init_environment() {
  require_command docker
  require_command openssl
  [[ ! -e "${ENV_FILE}" ]] || fail "environment_exists" "${ENV_FILE} already exists"
  cp "${ROOT_DIR}/.env.self-host.example" "${ENV_FILE}"
  chmod 600 "${ENV_FILE}"
  local database_password storage_password jwt_secret session_secret
  database_password="$(openssl rand -hex 24)"
  storage_password="$(openssl rand -hex 24)"
  jwt_secret="$(openssl rand -hex 32)"
  session_secret="$(openssl rand -hex 32)"
  sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${database_password}|" "${ENV_FILE}"
  sed -i "s|^MINIO_ROOT_PASSWORD=.*|MINIO_ROOT_PASSWORD=${storage_password}|" "${ENV_FILE}"
  sed -i "s|^AUTH_JWT_SECRET=.*|AUTH_JWT_SECRET=${jwt_secret}|" "${ENV_FILE}"
  sed -i "s|^AUTH_SESSION_SECRET=.*|AUTH_SESSION_SECRET=${session_secret}|" "${ENV_FILE}"
  printf 'self_host_initialized env_file=%s\n' "${ENV_FILE}"
}

require_environment() {
  require_command docker
  [[ -r "${ENV_FILE}" ]] || fail "environment_unavailable" "run init first"
  ! grep -q 'GENERATE_ON_SETUP' "${ENV_FILE}" || fail "secrets_not_generated" "run init again"
  docker compose version >/dev/null 2>&1 || fail "dependency_unavailable" "Docker Compose v2 is required"
}

profile_args() {
  if [[ "$(env_value PROVIDER_MODE)" == "local" ]]; then
    printf '%s\n' --profile local-ai
  fi
}

case "${ACTION}" in
  init)
    init_environment
    ;;
  validate)
    require_environment
    mapfile -t profile < <(profile_args)
    compose "${profile[@]}" config --quiet
    printf 'self_host_validated profile=%s\n' "$(env_value PROVIDER_MODE)"
    ;;
  up)
    require_environment
    mapfile -t profile < <(profile_args)
    compose "${profile[@]}" up -d --build
    if [[ "$(env_value PROVIDER_MODE)" == "local" ]]; then
      compose "${profile[@]}" exec -T ollama ollama pull "$(env_value LLM_MODEL)"
    fi
    ;;
  down)
    require_environment
    mapfile -t profile < <(profile_args)
    compose "${profile[@]}" down
    ;;
  migrate)
    require_environment
    PGUSER="$(env_value POSTGRES_USER)" PGDATABASE="$(env_value POSTGRES_DB)" \
      COMPOSE_FILE="${COMPOSE_FILE}" COMPOSE_ENV_FILES="${ENV_FILE}" \
      bash "${ROOT_DIR}/scripts/migrate.sh" up
    ;;
  seed-admin)
    require_environment
    [[ -n "${2:-}" ]] || fail "admin_email_required" "usage: self-host.sh seed-admin EMAIL"
    COMPOSE_FILE="${COMPOSE_FILE}" COMPOSE_ENV_FILES="${ENV_FILE}" \
      bash "${ROOT_DIR}/scripts/seed-admin.sh" "$2"
    ;;
  seed-demo)
    require_environment
    compose run --rm api python /workspace/database/seeds/seed.py
    ;;
  health)
    require_environment
    curl --silent --show-error --fail --max-time 10 \
      "http://127.0.0.1:$(env_value API_PORT)/health/dependencies"
    printf '\n'
    ;;
  upgrade)
    require_environment
    mapfile -t profile < <(profile_args)
    compose "${profile[@]}" pull --ignore-buildable
    compose "${profile[@]}" build --pull
    PGUSER="$(env_value POSTGRES_USER)" PGDATABASE="$(env_value POSTGRES_DB)" \
      COMPOSE_FILE="${COMPOSE_FILE}" COMPOSE_ENV_FILES="${ENV_FILE}" \
      bash "${ROOT_DIR}/scripts/migrate.sh" up
    compose "${profile[@]}" up -d --remove-orphans
    ;;
  help|-h|--help)
    printf '%s\n' 'Usage: scripts/self-host.sh {init|validate|up|down|migrate|seed-admin EMAIL|seed-demo|health|upgrade}'
    ;;
  *)
    fail "unknown_action" "use help for supported actions"
    ;;
esac
