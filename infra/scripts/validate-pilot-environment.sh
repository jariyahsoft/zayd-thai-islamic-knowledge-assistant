#!/usr/bin/env bash
set -euo pipefail

fail() { printf 'pilot_validation_error code=%s message=%s\n' "$1" "$2" >&2; exit 1; }
require() { [[ -n "${!1:-}" ]] || fail "configuration_missing" "$1 is required"; }

for key in \
  PILOT_ENVIRONMENT_ID PILOT_DATASET_MANIFEST PILOT_DATASET_SHA256 PILOT_DATASET_APPROVAL_ID \
  PILOT_INVITE_ALLOWLIST_VERSION PILOT_S3_ENDPOINT PILOT_S3_REGION PILOT_S3_BUCKET PILOT_OFFSITE_S3_URI \
  PILOT_DATABASE_URL_SECRET PILOT_REDIS_URL_SECRET \
  PILOT_S3_ACCESS_KEY_SECRET PILOT_S3_SECRET_KEY_SECRET PILOT_AUTH_JWT_SECRET \
  PILOT_AUTH_SESSION_SECRET PILOT_PROVIDER_TOKEN_SECRET PILOT_LLM_API_KEY_SECRET \
  PILOT_EMBEDDING_API_KEY_SECRET PILOT_INVITE_EMAIL_HASHES_SECRET \
  PILOT_BACKUP_ENCRYPTION_KEY_SECRET PILOT_TLS_CERTIFICATE_SECRET PILOT_TLS_PRIVATE_KEY_SECRET \
  PILOT_PROMETHEUS_VOLUME PILOT_BACKUP_VOLUME; do
  require "$key"
done

[[ "${PILOT_ENVIRONMENT_ID}" =~ ^pilot-[a-z0-9-]+$ ]] \
  || fail "environment_invalid" "PILOT_ENVIRONMENT_ID must start with pilot-"
[[ "${PILOT_DATASET_APPROVAL_ID}" =~ ^[A-Z0-9][A-Z0-9._-]{2,127}$ ]] \
  || fail "dataset_approval_invalid" "PILOT_DATASET_APPROVAL_ID is invalid"
[[ -r "${PILOT_DATASET_MANIFEST}" ]] \
  || fail "dataset_manifest_unavailable" "PILOT_DATASET_MANIFEST must be readable"

actual_sha256="$(sha256sum "${PILOT_DATASET_MANIFEST}" | awk '{print $1}')"
[[ "${actual_sha256}" == "${PILOT_DATASET_SHA256}" ]] \
  || fail "dataset_checksum_invalid" "PILOT_DATASET_SHA256 does not match"

secret_names=()
for key in \
  PILOT_DATABASE_URL_SECRET PILOT_REDIS_URL_SECRET PILOT_S3_ACCESS_KEY_SECRET \
  PILOT_S3_SECRET_KEY_SECRET PILOT_AUTH_JWT_SECRET PILOT_AUTH_SESSION_SECRET \
  PILOT_PROVIDER_TOKEN_SECRET PILOT_LLM_API_KEY_SECRET PILOT_EMBEDDING_API_KEY_SECRET \
  PILOT_INVITE_EMAIL_HASHES_SECRET PILOT_BACKUP_ENCRYPTION_KEY_SECRET \
  PILOT_TLS_CERTIFICATE_SECRET PILOT_TLS_PRIVATE_KEY_SECRET; do
  value="${!key}"
  [[ "${value}" =~ ^pilot-[a-z0-9-]+$ ]] \
    || fail "secret_namespace_invalid" "$key must name a pilot-* secret"
  secret_names+=("${value}")
done

unique_count="$(printf '%s\n' "${secret_names[@]}" | sort -u | wc -l | tr -d ' ')"
[[ "${unique_count}" -eq "${#secret_names[@]}" ]] \
  || fail "secret_namespace_invalid" "pilot secrets must be distinct"

printf 'pilot_environment_validated environment=%s dataset_approval=%s\n' \
  "${PILOT_ENVIRONMENT_ID}" "${PILOT_DATASET_APPROVAL_ID}"
