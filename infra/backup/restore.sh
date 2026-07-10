#!/usr/bin/env bash
set -euo pipefail

umask 077

fail() { printf 'restore_error code=%s message=%s\n' "$1" "$2" >&2; audit "failed" "$1"; exit 1; }
audit() {
  local status="$1" detail="${2:-none}" now
  now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"; mkdir -p "${BACKUP_AUDIT_DIR}"
  printf '{"timestamp":"%s","operation":"restore","status":"%s","actor":"%s","trace_id":"%s","detail":"%s"}\n' \
    "$now" "$status" "${BACKUP_ACTOR}" "${BACKUP_TRACE_ID}" "$detail" >>"${BACKUP_AUDIT_DIR}/operations.jsonl"
}
require_command() { command -v "$1" >/dev/null 2>&1 || fail "dependency_unavailable" "$1 is required"; }

artifact="${1:-}"
BACKUP_ROOT="${BACKUP_ROOT:-/var/backups/zayd}"
BACKUP_AUDIT_DIR="${BACKUP_AUDIT_DIR:-${BACKUP_ROOT}/audit}"
BACKUP_ACTOR="${BACKUP_ACTOR:-restore-operator}"
BACKUP_TRACE_ID="${BACKUP_TRACE_ID:-restore-$(date -u +%Y%m%dT%H%M%SZ)-$$}"
BACKUP_ENCRYPTION_KEY_FILE="${BACKUP_ENCRYPTION_KEY_FILE:-}"
RESTORE_DATABASE_URL="${RESTORE_DATABASE_URL:-}"
RESTORE_S3_BUCKET="${RESTORE_S3_BUCKET:-}"
RESTORE_S3_ENDPOINT="${RESTORE_S3_ENDPOINT:-}"

[[ "${RESTORE_ENVIRONMENT:-}" == "isolated" ]] || fail "restore_not_isolated" "RESTORE_ENVIRONMENT=isolated is required"
[[ -n "${artifact}" && -r "${artifact}" ]] || fail "artifact_unavailable" "a readable encrypted artifact is required"
[[ -r "${artifact}.sha256" ]] || fail "checksum_unavailable" "artifact checksum is required"
[[ -n "${BACKUP_ENCRYPTION_KEY_FILE}" && -r "${BACKUP_ENCRYPTION_KEY_FILE}" ]] || fail "encryption_key_unavailable" "readable BACKUP_ENCRYPTION_KEY_FILE is required"
[[ -n "${RESTORE_DATABASE_URL}" ]] || fail "invalid_configuration" "RESTORE_DATABASE_URL is required"
[[ -n "${RESTORE_S3_BUCKET}" ]] || fail "invalid_configuration" "RESTORE_S3_BUCKET is required"
for command_name in pg_restore psql aws gpg tar sha256sum; do require_command "$command_name"; done

sha256sum --check "${artifact}.sha256" >/dev/null || fail "artifact_corrupt" "encrypted artifact checksum failed"
work_dir="$(mktemp -d "${TMPDIR:-/tmp}/zayd-restore.XXXXXX")"; trap 'rm -rf "${work_dir}"' EXIT
gpg --batch --yes --decrypt --passphrase-file "${BACKUP_ENCRYPTION_KEY_FILE}" --output "${work_dir}/backup.tar" "${artifact}" \
  || fail "decryption_failed" "gpg decryption failed"
tar --extract --file="${work_dir}/backup.tar" --directory="${work_dir}"
payload="${work_dir}/payload"
[[ -f "${payload}/MANIFEST.sha256" ]] || fail "manifest_unavailable" "payload manifest is missing"
(cd "${payload}" && sha256sum --check MANIFEST.sha256 >/dev/null) || fail "artifact_corrupt" "payload checksum failed"

# Restore roles first so grants and ownership references in the custom archive remain valid.
psql "${RESTORE_DATABASE_URL}" --set ON_ERROR_STOP=1 --file="${payload}/database/roles.sql" \
  || fail "role_restore_failed" "database roles could not be restored"
pg_restore --exit-on-error --clean --if-exists --no-owner --dbname="${RESTORE_DATABASE_URL}" "${payload}/database/data.dump" \
  || fail "database_restore_failed" "database restore failed"

aws_args=(); [[ -z "${RESTORE_S3_ENDPOINT}" ]] || aws_args+=(--endpoint-url "${RESTORE_S3_ENDPOINT}")
aws "${aws_args[@]}" s3 sync "${payload}/objects" "s3://${RESTORE_S3_BUCKET}" --delete --only-show-errors \
  || fail "object_restore_failed" "object storage restore failed"

psql "${RESTORE_DATABASE_URL}" --set ON_ERROR_STOP=1 --tuples-only --command='SELECT 1' >/dev/null \
  || fail "consistency_check_failed" "database verification failed"
aws "${aws_args[@]}" s3 ls "s3://${RESTORE_S3_BUCKET}" >/dev/null \
  || fail "consistency_check_failed" "object storage verification failed"
audit "completed" "$(basename "${artifact}")"
printf 'restore_completed artifact=%s trace_id=%s\n' "${artifact}" "${BACKUP_TRACE_ID}"
