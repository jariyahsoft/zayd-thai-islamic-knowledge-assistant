# MinIO Deployment Notes

## Development Profile

The development Compose stack runs MinIO as the local S3-compatible storage service.

Relevant services:

- `minio`
- `minio-bootstrap`

The bootstrap step creates the configured bucket and forces it to remain private.

## Default Environment

```text
S3_ENDPOINT=http://minio:9000
S3_REGION=us-east-1
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=zayd-private
S3_ADDRESSING_STYLE=auto
S3_MAX_ATTEMPTS=3
S3_SIGNED_URL_TTL_SECONDS=300
```

These values are development placeholders only. Production deployments must use non-placeholder
credentials and a private bucket policy.

## Private Bucket Requirement

MinIO is bootstrapped with:

- bucket creation if missing
- anonymous access explicitly set to `private`

This matches the storage security requirement that objects remain private by default and only be
accessed through short-lived signed URLs.

## Validation

Recommended validation steps for local development:

1. Start the stack with `docker compose up -d`.
2. Confirm `minio` and `minio-bootstrap` complete successfully.
3. Run the MinIO-backed storage integration test:

```bash
RUN_MINIO_TESTS=1 \
S3_ENDPOINT=http://127.0.0.1:9000 \
uv run pytest services/common/tests/test_storage.py
```

Use `127.0.0.1` for host-side tests so the signed URL is reachable from the local pytest process.

## Operational Notes

- Signed URL TTLs are capped to 900 seconds by application validation.
- Path-style addressing is selected automatically for local MinIO endpoints.
- Worker and API containers use the same validated storage configuration.
- Later environments may replace MinIO with managed S3-compatible storage without changing the
  application storage interface.
