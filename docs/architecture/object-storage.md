# Object Storage Architecture

## Overview

Zayd uses an S3-compatible object storage layer for private binary assets such as:

- original uploaded documents
- permission evidence files
- export bundles
- backup artifacts

The MVP uses MinIO in development and supports managed S3-compatible providers in later
environments through the same adapter boundary.

## Design Rules

- All buckets are private by default.
- Application code uses the shared `ObjectStorage` port instead of provider SDKs directly.
- Object keys are generated server-side and must not be derived from user-controlled paths.
- Client access is mediated through short-lived signed URLs.
- Database rows remain the source of truth for document metadata; object storage holds binary data.

## Current Adapter

`services/common/src/zayd_common/storage.py` provides:

- `ObjectStorage` protocol
- `S3StorageSettings`
- `S3ObjectStorage`
- stable `StorageError` codes for upload, delete, and signed-URL failures

The adapter is configured from the validated shared settings:

- `S3_ENDPOINT`
- `S3_REGION`
- `S3_ACCESS_KEY`
- `S3_SECRET_KEY`
- `S3_BUCKET`
- `S3_ADDRESSING_STYLE`
- `S3_MAX_ATTEMPTS`
- `S3_SIGNED_URL_TTL_SECONDS`

## Upload Flow

For document ingestion:

1. Validate source, license, file type, and file size.
2. Generate a server-side quarantine object key.
3. Upload bytes to private object storage.
4. Persist the object key in `document_versions.original_file_key`.
5. Generate a short-lived signed `GET` URL for controlled retrieval.

If database persistence fails after the object upload succeeds, the service deletes the object to
avoid orphaned storage state.

## Key Structure

Current quarantine keys:

```text
uploads/quarantine/<document-id>/<filename>
```

This keeps the path deterministic and namespaced while avoiding direct client control of storage
layout.

## Security Notes

- Signed URL TTL is capped at 900 seconds.
- Filenames containing path separators are rejected before key generation.
- The object key is stored for internal auditability and worker access; downstream APIs should
  expose signed URLs only when access is required.
- Storage credentials remain server-side and are validated/masked through `ServiceSettings`.

## Failure Handling

- S3 client retries are bounded through SDK configuration.
- Upload failures return stable storage errors and prevent any document/version row from being
  committed.
- Delete compensation runs when a post-upload database commit fails.

## Follow-on Work

- TASK-05-03 will consume quarantine objects for malware scanning.
- Later tasks can add bucket separation or lifecycle policies for quarantine, permission evidence,
  exports, and backups without changing the storage port.
