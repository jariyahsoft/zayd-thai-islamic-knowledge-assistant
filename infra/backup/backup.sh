#!/usr/bin/env bash
set -euo pipefail

umask 077

fail() {
  printf 'backup_error code=%s message=%s\n' "$1" "$2" >&2
  audit "failed" "$1"
  exit 1
}

audit() {
  local status="$1" detail="${2:-none}" now
  now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  mkdir -p "${BACKUP_AUDIT_DIR}"
  printf '{"timestamp":"%s","operation":"backup","status":"%s","actor":"%s","trace_id":"%s","detail":"%s"}\n' \
    "$now" "$status" "${BACKUP_ACTOR}" "${BACKUP_TRACE_ID}" "$detail" >>"${BACKUP_AUDIT_DIR}/operations.jsonl"
}

require_command() { command -v "$1" >/dev/null 2>&1 || fail "dependency_unavailable" "$1 is required"; }

BACKUP_ROOT="${BACKUP_ROOT:-/var/backups/zayd}"
BACKUP_AUDIT_DIR="${BACKUP_AUDIT_DIR:-${BACKUP_ROOT}/audit}"
BACKUP_ACTOR="${BACKUP_ACTOR:-scheduled-backup}"
BACKUP_TRACE_ID="${BACKUP_TRACE_ID:-backup-$(date -u +%Y%m%dT%H%M%SZ)-$$}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
BACKUP_ENCRYPTION_KEY_FILE="${BACKUP_ENCRYPTION_KEY_FILE:-}"
DATABASE_URL="${DATABASE_URL:-}"
S3_BUCKET="${S3_BUCKET:-}"
S3_ENDPOINT="${S3_ENDPOINT:-}"
OFFSITE_S3_URI="${OFFSITE_S3_URI:-}"
BACKUP_CONFIG_PATHS="${BACKUP_CONFIG_PATHS:-docs/governance docs/06_islamic_governance docs/05_data}"

[[ "${BACKUP_RETENTION_DAYS}" =~ ^[1-9][0-9]*$ ]] || fail "invalid_configuration" "BACKUP_RETENTION_DAYS must be a positive integer"
[[ -n "${DATABASE_URL}" ]] || fail "invalid_configuration" "DATABASE_URL is required"
[[ -n "${S3_BUCKET}" ]] || fail "invalid_configuration" "S3_BUCKET is required"
[[ -n "${BACKUP_ENCRYPTION_KEY_FILE}" && -r "${BACKUP_ENCRYPTION_KEY_FILE}" ]] || fail "encryption_key_unavailable" "readable BACKUP_ENCRYPTION_KEY_FILE is required"

for command_name in pg_dump pg_dumpall aws gpg tar sha256sum find; do require_command "$command_name"; done

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
work_dir="$(mktemp -d "${TMPDIR:-/tmp}/zayd-backup.XXXXXX")"
trap 'rm -rf "${work_dir}"' EXIT
payload_dir="${work_dir}/payload"
mkdir -p "${payload_dir}/database" "${payload_dir}/objects" "${payload_dir}/configuration" "${BACKUP_ROOT}"

pg_dump --format=custom --no-owner --file="${payload_dir}/database/data.dump" "${DATABASE_URL}" \
  || fail "database_backup_failed" "pg_dump failed"
pg_dumpall --roles-only --database="${DATABASE_URL}" >"${payload_dir}/database/roles.sql" \
  || fail "database_backup_failed" "role export failed"

aws_args=()
[[ -z "${S3_ENDPOINT}" ]] || aws_args+=(--endpoint-url "${S3_ENDPOINT}")
aws "${aws_args[@]}" s3 sync "s3://${S3_BUCKET}" "${payload_dir}/objects" --only-show-errors \
  || fail "object_backup_failed" "object storage sync failed"

for path in ${BACKUP_CONFIG_PATHS}; do
  [[ -e "$path" ]] || fail "configuration_backup_failed" "configured path does not exist: $path"
  destination="${payload_dir}/configuration/${path}"
  mkdir -p "$(dirname "${destination}")"
  cp -a "$path" "${destination}"
done

printf '{"format_version":1,"created_at":"%s","actor":"%s","trace_id":"%s","database_format":"postgres-custom","object_bucket":"%s"}\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${BACKUP_ACTOR}" "${BACKUP_TRACE_ID}" "${S3_BUCKET}" >"${payload_dir}/metadata.json"
(
  cd "${payload_dir}"
  find . -type f ! -name MANIFEST.sha256 -print0 | sort -z | xargs -0 sha256sum >MANIFEST.sha256
)

archive="${work_dir}/zayd-${timestamp}.tar"
encrypted="${BACKUP_ROOT}/zayd-${timestamp}.tar.gpg"
tar --create --file="${archive}" -C "${work_dir}" payload
gpg --batch --yes --symmetric --cipher-algo AES256 --passphrase-file "${BACKUP_ENCRYPTION_KEY_FILE}" \
  --output "${encrypted}" "${archive}" || fail "encryption_failed" "gpg encryption failed"
sha256sum "${encrypted}" >"${encrypted}.sha256"

if [[ -n "${OFFSITE_S3_URI}" ]]; then
  aws "${aws_args[@]}" s3 cp "${encrypted}" "${OFFSITE_S3_URI%/}/$(basename "${encrypted}")" --only-show-errors \
    || fail "offsite_copy_failed" "encrypted off-site copy failed"
  aws "${aws_args[@]}" s3 cp "${encrypted}.sha256" "${OFFSITE_S3_URI%/}/$(basename "${encrypted}.sha256")" --only-show-errors \
    || fail "offsite_copy_failed" "off-site checksum copy failed"
fi

find "${BACKUP_ROOT}" -maxdepth 1 -type f \( -name 'zayd-*.tar.gpg' -o -name 'zayd-*.tar.gpg.sha256' \) \
  -mtime "+${BACKUP_RETENTION_DAYS}" -delete
audit "completed" "$(basename "${encrypted}")"
printf 'backup_completed artifact=%s trace_id=%s\n' "${encrypted}" "${BACKUP_TRACE_ID}"
