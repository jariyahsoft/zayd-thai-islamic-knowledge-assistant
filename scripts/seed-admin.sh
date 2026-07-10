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
export ADMIN_EMAIL ADMIN_PASSWORD

echo "=== ${PROJECT} Admin Credentials ==="
echo "Email:    ${ADMIN_EMAIL}"
echo "Password: ${ADMIN_PASSWORD}"
echo ""
echo "WARNING: This is the only time the password is shown. Save it immediately."
echo ""

# Delegate to the API container if the stack is running
if docker compose exec -T "${SERVICE}" true 2>/dev/null; then
  echo "Provisioning admin user via running API service…" >&2
  docker compose exec -T -e ADMIN_EMAIL -e ADMIN_PASSWORD "${SERVICE}" python - <<'PY'
import os

from sqlalchemy import select
from zayd_common.auth import AuthService
from zayd_common.database import SQLAlchemyUnitOfWork, get_sessionmaker
from zayd_common.database.models import Role, UserRole
from zayd_common.rbac import _bootstrap_system_roles_in_session
from zayd_common.settings import ServiceSettings

settings = ServiceSettings.from_runtime_env(app_name="seed-admin")
factory = get_sessionmaker(settings.database_url)
auth = AuthService(SQLAlchemyUnitOfWork(factory), signing_secret=settings.auth_jwt_secret.get_secret_value())
registered = auth.register(
    email=os.environ["ADMIN_EMAIL"],
    password=os.environ["ADMIN_PASSWORD"],
    display_name="Initial Administrator",
)
with factory() as session:
    _bootstrap_system_roles_in_session(session)
    admin_role = session.scalar(select(Role).where(Role.name == "admin"))
    if admin_role is None:
        raise RuntimeError("admin role is unavailable")
    session.add(
        UserRole(
            user_id=registered.user.id,
            role_id=admin_role.id,
            granted_by=registered.user.id,
        )
    )
    session.commit()
print(f"Admin user {registered.user.email} provisioned.")
PY
else
  echo "API service is not running. Admin credentials generated above." >&2
  echo "Start the stack with 'make dev', then re-run this script." >&2
fi

unset ADMIN_EMAIL ADMIN_PASSWORD
