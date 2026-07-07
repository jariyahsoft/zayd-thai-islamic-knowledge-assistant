# Document Upload API

## Overview

The Document Upload API registers a new document ingestion attempt, validates source and
license eligibility, computes a SHA-256 content hash, and returns either an accepted upload
record or a safe duplicate result.

This task implements the initial registration step on `POST /documents`. Object storage,
malware scanning, and follow-on extraction stages remain deferred to later ingestion tasks.

## Authentication

The endpoint requires a Bearer access token with `documents.upload`.

Users holding privileged back-office roles must also satisfy the platform MFA requirement.

## Endpoint

```http
POST /documents
Authorization: Bearer <access_token>
Content-Type: application/json
```

## Request Body

```json
{
  "source_id": "550e8400-e29b-41d4-a716-446655440000",
  "source_license_id": "b67b6f44-b1e6-4c48-8ce0-7d7f2e0f0e56",
  "canonical_id": "fiqh-book-001",
  "document_type": "book",
  "title": "Thai Fiqh Reference",
  "language": "th",
  "filename": "fiqh-reference.pdf",
  "content_type": "application/pdf",
  "file_base64": "JVBERi0xLjcK...",
  "author": "Example Author",
  "translator": "Example Translator",
  "publisher": "Example Publisher",
  "edition": "2nd",
  "madhhab": "shafii"
}
```

## Supported File Types

The request is accepted only when both the declared content type and filename extension match
one of these supported types:

| Content Type | Extension |
|---|---|
| `application/pdf` | `.pdf` |
| `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | `.docx` |
| `text/plain` | `.txt` |
| `text/markdown` | `.md` |
| `text/html` | `.html` |
| `application/json` | `.json` |
| `text/csv` | `.csv` |

Maximum payload size: 25 MiB after base64 decoding.

## Success Response

**Response:** `201 Created`

```json
{
  "document_id": "4f9dbe0e-5cf7-4844-a29f-86e63e7dd6f4",
  "document_version_id": "9ea9eb59-f5a6-4d3d-94e6-16fc4f4d5f2c",
  "content_hash": "cf43513d33bbf7f1f57d0ec7d7864a14681245cbad1e98d106954c4f5c4faf15",
  "filename": "fiqh-reference.pdf",
  "content_type": "application/pdf",
  "byte_size": 1024,
  "duplicate": null,
  "upload_status": "accepted",
  "original_file_key": "uploads/quarantine/4f9dbe0e-5cf7-4844-a29f-86e63e7dd6f4/fiqh-reference.pdf",
  "policy_version": "document-upload-v1"
}
```

## Duplicate Response

Duplicate content does not raise a hard conflict. The endpoint returns a safe actionable result
that points to the existing document/version:

```json
{
  "document_id": "4f9dbe0e-5cf7-4844-a29f-86e63e7dd6f4",
  "document_version_id": "9ea9eb59-f5a6-4d3d-94e6-16fc4f4d5f2c",
  "content_hash": "cf43513d33bbf7f1f57d0ec7d7864a14681245cbad1e98d106954c4f5c4faf15",
  "filename": "fiqh-reference.pdf",
  "content_type": "application/pdf",
  "byte_size": 1024,
  "duplicate": {
    "document_id": "4f9dbe0e-5cf7-4844-a29f-86e63e7dd6f4",
    "document_version_id": "9ea9eb59-f5a6-4d3d-94e6-16fc4f4d5f2c",
    "canonical_id": "fiqh-book-001",
    "title": "Thai Fiqh Reference",
    "content_hash": "cf43513d33bbf7f1f57d0ec7d7864a14681245cbad1e98d106954c4f5c4faf15"
  },
  "upload_status": "duplicate",
  "original_file_key": "uploads/quarantine/9ea9eb59-f5a6-4d3d-94e6-16fc4f4d5f2c/fiqh-reference.pdf",
  "policy_version": "document-upload-v1"
}
```

## Stable Errors

| HTTP | Code | Meaning |
|---:|---|---|
| 400 | `DOCUMENT_FILENAME_REQUIRED` | Filename is empty |
| 400 | `DOCUMENT_UNSUPPORTED_FILE_TYPE` | File type or extension is unsupported |
| 400 | `DOCUMENT_INVALID_FILE_PAYLOAD` | `file_base64` is malformed |
| 400 | `DOCUMENT_CANONICAL_ID_REQUIRED` | Canonical ID is empty |
| 400 | `DOCUMENT_TITLE_REQUIRED` | Title is empty |
| 404 | `DOCUMENT_SOURCE_NOT_FOUND` | Source does not exist |
| 404 | `DOCUMENT_LICENSE_NOT_FOUND` | Source license does not exist |
| 409 | `DOCUMENT_SOURCE_INACTIVE` | Source is suspended/inactive |
| 409 | `DOCUMENT_LICENSE_SOURCE_MISMATCH` | License does not belong to the selected source |
| 409 | `DOCUMENT_LICENSE_INELIGIBLE` | License policy denied ingestion |
| 413 | `DOCUMENT_FILE_TOO_LARGE` | Decoded file exceeds 25 MiB |

## Security and Audit Behavior

- Uploads fail closed when the source is inactive or the source/license combination is not eligible
  for ingestion under the deterministic license policy engine.
- Uploaded bytes are treated as untrusted input.
- Accepted registrations emit `documents.upload.register` audit records.
- Duplicate detections emit `documents.upload.duplicate` audit records.
- The API returns placeholder quarantine object keys only; it does not expose signed URLs or file
  contents.
