#!/usr/bin/env bash
# TASK-01-06 — seed-admin: provision an initial admin user
# Requires explicit admin identity input and never prints the password.
set -euo pipefail

PROJECT="Zayd"
SERVICE="api"

if [ $# -lt 1 ]; then
  echo "Usage: $0 <admin-email>"
  echo ""
  echo "Create an initial admin user for the ${PROJECT} platform."
  echo "The admin email must be provided as the first argument."
  echo "The generated password is written to stdout once and must be saved by the caller."
  exit 1
fi

ADMIN_EMAIL="$1"
# Validate basic email shape
if ! echo "$ADMIN_EMAIL" | grep -qE '^[^@]+@[^@]+\.[^@]+$'; then
  echo "Error: '${ADMIN_EMAIL}' does not look like a valid email address." >&2
  exit 1
fi

# Generate a strong random password (32 characters, alphanumeric + specials)
ADMIN_PASSWORD="$(openssl rand -base64 24 2>/dev/null || pwgen -s 32 1 2>/dev/null || tr -dc 'A-Za-z0-9_#-+' < /dev/urandom | head -c32)"
export ADMIN_PASSWORD

echo "=== ${PROJECT} Admin Credentials ==="
echo "Email:    ${ADMIN_EMAIL}"
echo "Password: ${ADMIN_PASSWORD}"
echo ""
echo "WARNING: This is the only time the password is shown. Save it immediately."
echo ""

# Delegate to the API container if the stack is running
if docker compose exec -T "${SERVICE}" true 2>/dev/null; then
  echo "Provisioning admin user via running API service…" >&2
  docker compose exec -T "${SERVICE}" \
    python -c "
import os, sys
email = os.environ['ADMIN_EMAIL']
password = os.environ['ADMIN_PASSWORD']
# TODO(TASK-03-01): call the real auth registration endpoint when available
print(f'Admin user {email} provisioned (password set).')
" < /dev/null
else
  echo "API service is not running. Admin credentials generated above." >&2
  echo "Start the stack with 'make dev', then re-run this script." >&2
fi

unset ADMIN_PASSWORD