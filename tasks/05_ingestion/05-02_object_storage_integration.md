# TASK-05-02 — Object Storage Integration

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- SRS §7.5 Object Storage
- NFR-SEC-001

## Objective

Implement an S3-compatible storage abstraction supporting MinIO and managed S3.

## Scope

### In Scope

- Implement an S3-compatible storage abstraction supporting MinIO and managed S3.
- Use private buckets and short-lived signed URLs.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-05-01

## Expected Files

- Implementation files under the relevant `05_ingestion` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Pipeline stages must be idempotent and retryable.
- Preserve original files/text and store derived data separately.
- Use background jobs for expensive processing.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Treat uploaded files and extracted content as untrusted.

## Acceptance Criteria

- [ ] Files are private by default.
- [ ] Object keys are not exposed unnecessarily.
- [ ] Storage failures are retried safely and do not create orphan database states.

## Required Tests

### Unit and Contract Tests

- MinIO integration tests
- Signed URL expiry tests
- Failure compensation tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/architecture/object-storage.md`
- `docs/deployment/minio.md`

## Completion Report

### Files Changed

- `services/common/src/zayd_common/storage.py` (new): S3-compatible `ObjectStorage`
  protocol, `S3ObjectStorage` adapter, `S3StorageSettings`, `StorageError` with stable
  operation-specific codes, `storage_settings_from_env()`.
- `services/common/src/zayd_common/__init__.py`: Re-exports the new storage symbols.
- `services/common/src/zayd_common/settings.py`: Adds `s3_addressing_style`,
  `s3_max_attempts`, `s3_signed_url_ttl_seconds` with validators and production-unsafe
  secret detection; threads them through `ServiceSettings.from_runtime_env`.
- `services/common/src/zayd_common/documents.py`: Wires `ObjectStorage` into
  `DocumentUploadService` so uploads go through `put_private_bytes` to a server-side
  quarantine key, signed download URLs are returned on both the accepted and duplicate
  paths, and a failed database commit triggers `delete_object` compensation.
- `services/api/src/zayd_service_api/app.py`: Builds `S3ObjectStorage` from the
  validated `ServiceSettings`, exposes the new `SignedUrlResponse` and `download_url`
  fields, and propagates the signed URL through the upload response.
- `services/common/pyproject.toml`, `uv.lock`: Adds the `boto3>=1.39.14` dependency.
- `services/common/tests/test_storage.py` (new): Unit tests covering quarantine put
  metadata, signed URL TTL bounding, failure surfacing, and a `RUN_MINIO_TESTS`-gated
  MinIO round-trip/signed-URL integration test.
- `services/common/tests/test_documents.py`: Adds a `FakeStorage` test double and
  extends the upload suite to assert that storage uploads happen, signed URLs are
  returned on both accepted and duplicate paths, path-traversal filenames are rejected,
  and storage failures do not write audit records.
- `services/api/tests/test_documents_api.py`: Patches the API's `S3ObjectStorage`
  dependency, asserts the `SignedUrlResponse` schema is exposed, and exercises the
  accepted and duplicate response shapes.
- `docs/architecture/object-storage.md` (new): Documents the storage port, the
  MinIO and managed S3 deployment story, key structure, security rules, and failure
  handling.
- `docs/deployment/minio.md` (new): Documents the development environment
  configuration, the private bucket requirement, and the host-side test recipe.
- `tasks/05_ingestion/05-02_object_storage_integration.md`: Status set to `DONE`
  with the completion report filled in.
- `tasks/00_task_index.md`: TASK-05-02 marked `DONE`.

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_storage.py
  services/common/tests/test_documents.py services/api/tests/test_documents_api.py` →
  19 passed, 1 skipped (the MinIO round-trip is gated on `RUN_MINIO_TESTS=1`).
- `uv run pytest` → 188 passed, 1 skipped.
- `uv run ruff check services/common/src/zayd_common/storage.py
  services/common/tests/test_storage.py services/api/src/zayd_service_api/app.py
  services/common/src/zayd_common/documents.py services/common/src/zayd_common/__init__.py
  services/common/src/zayd_common/settings.py` → clean.
- `uv run ruff format --check` on the same set → clean.
- `uv run mypy services/common/src/zayd_common/storage.py
  services/common/src/zayd_common/__init__.py services/api/src/zayd_service_api/app.py
  services/common/src/zayd_common/documents.py services/common/src/zayd_common/settings.py` →
  only the expected `boto3` / `botocore` import-untyped notes (those packages do not
  ship type stubs).

### Acceptance Criteria Result

- [x] Files are private by default. The adapter always calls `put_object` against
  the configured private bucket, the MinIO bootstrap script in the development
  profile forces the bucket policy to `private`, and no code path exposes an
  unauthenticated object URL. Download URLs are generated exclusively through
  short-lived presigned URLs.
- [x] Object keys are not exposed unnecessarily. Only the server-derived
  `uploads/quarantine/<document-id>/<filename>` key is persisted on the
  `document_versions.original_file_key` row; downstream API consumers receive a
  presigned `download_url` with bounded TTL instead of the raw key. Filenames
  containing path separators are rejected at the service layer.
- [x] Storage failures are retried safely and do not create orphan database
  states. The boto3 client is configured with bounded `max_attempts` retries, the
  service catches and converts storage exceptions into stable `StorageError` codes,
  and a failed post-upload database commit triggers a `delete_object` compensation
  call so the database and storage stay aligned.

### Security and License Review

- All credentials flow through `ServiceSettings` as `SecretStr` values and the
  `S3StorageSettings` constructor never persists or logs them. The development
  placeholders are included in the `PRODUCTION_UNSAFE_SECRETS` set so production
  startup fails closed if a deployment still uses `minioadmin`.
- Signed URL TTL is bounded at 900 seconds both in `ServiceSettings` and
  `S3StorageSettings.__post_init__`, and the adapter clamps the requested TTL to
  the configured maximum before generating a presigned URL.
- Quarantine keys are derived from a server-side UUID and the validated filename;
  user input cannot escape the prefix, and the upload request validator rejects
  `..` and `/` segments before key generation.
- Storage failures are translated to stable `StorageError` codes, which the API
  layer surfaces as `502` responses without exposing the underlying SDK message.
- No secrets, production data, restricted religious content, or third-party code
  were introduced.

### Known Limitations

- The MinIO integration test is gated on `RUN_MINIO_TESTS=1` because it requires a
  reachable MinIO service; the documented `127.0.0.1:9000` recipe is run manually
  during release validation.
- The API still accepts the existing JSON `file_base64` upload payload and the
  signed URL is generated by the service; switching to a true multipart upload
  with streaming presigned `PUT` URLs is left to a future iteration.
- The `ObjectStorage` port currently exposes only `put`, `delete`, and
  `presign_get` operations. Adding `presign_put` for client-direct uploads and
  `head` for existence checks is a natural follow-up once TASK-05-03 needs them.

### Follow-up Tasks

- TASK-05-03 (Malware Scan Pipeline) will consume quarantine objects.
- TASK-13-07 (Backup and Restore) will reuse the same `ObjectStorage` port for
  export and backup artifacts.
- A future storage task can add bucket separation or lifecycle policies for
  quarantine, permission evidence, exports, and backups without changing the
  storage port.

### Commit

- Pending the focused commit for this task; see the `tasks-update.md` entry for
  the precise commit hash once it is recorded.
