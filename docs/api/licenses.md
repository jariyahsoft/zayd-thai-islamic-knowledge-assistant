# Licenses API

## Overview

The Licenses API manages source license records for storage, embedding, commercial use,
redistribution, attribution, validity dates, and permission evidence.

License records are append-oriented. Replacement creates a new license record and keeps the
previous record available for audit and document-history references.

## Authentication

All endpoints require a Bearer access token.

- Read operations require `licenses.read`.
- Write operations require `licenses.manage`.
- Privileged users must satisfy the platform MFA requirement.

## Base Paths

- `/admin/sources/{source_id}/licenses`
- `/admin/licenses/{license_id}`

## License Fields

| Field | Type | Description |
|---|---|---|
| `id` | UUID | License record identifier |
| `source_id` | UUID | Source governed by the license |
| `license_name` | string | License or permission agreement name |
| `license_version` | string? | Version, publication date, or agreement identifier |
| `status` | string | `unknown`, `review_required`, `ephemeral_cache_only`, `persistent_private`, `persistent_redistributable`, `prohibited`, or `expired` |
| `storage_permission` | string | `unknown`, `allowed`, `prohibited`, or `conditional` |
| `embedding_permission` | string | `unknown`, `allowed`, `prohibited`, or `conditional` |
| `commercial_use` | string | `unknown`, `allowed`, `prohibited`, or `conditional` |
| `redistribution` | string | `unknown`, `allowed`, `prohibited`, or `conditional` |
| `attribution_required` | boolean | Whether citations or UI must include attribution |
| `attribution_template` | string? | Required attribution text or template |
| `permission_document_key` | string? | Private object-storage key for permission evidence |
| `valid_from` | date? | First date the permission is valid |
| `valid_until` | date? | Final date the permission is valid |
| `notes` | string? | Administrative notes |
| `row_version` | integer | Optimistic-locking/version marker for the row |

## Create License

```http
POST /admin/sources/{source_id}/licenses
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{
  "license_name": "Publisher Agreement",
  "license_version": "2026-01",
  "status": "persistent_redistributable",
  "storage_permission": "allowed",
  "embedding_permission": "allowed",
  "commercial_use": "conditional",
  "redistribution": "allowed",
  "attribution_required": true,
  "attribution_template": "Courtesy of the publisher.",
  "permission_document_key": "private/licenses/publisher-agreement.pdf",
  "valid_from": "2026-01-01",
  "valid_until": "2027-01-01",
  "notes": "Approved for Zayd publication."
}
```

**Response:** `201 Created` with `LicenseResponse`.

## List Source Licenses

```http
GET /admin/sources/{source_id}/licenses
Authorization: Bearer <access_token>
```

Returns all license records for the source, newest first.

## Get License

```http
GET /admin/licenses/{license_id}
Authorization: Bearer <access_token>
```

Returns one license record.

## Replace License

```http
POST /admin/licenses/{license_id}/replace
Authorization: Bearer <access_token>
Content-Type: application/json
```

Creates a new license row for the same source. The previous row is not overwritten.

## Permission Document Access

```http
GET /admin/licenses/{license_id}/permission-document
Authorization: Bearer <access_token>
```

Returns metadata for the private permission-evidence object key and records an immutable audit
event. The API does not return file contents or public signed URLs.

## Publication Authorization Check

```http
POST /admin/licenses/{license_id}/publication-authorization
Authorization: Bearer <access_token>
```

Returns a deterministic authorization decision under `license-registry-v1`.

Fail-closed conditions include:

- `unknown`, `prohibited`, or `expired` status.
- `valid_until` before the evaluation date.
- Status other than `persistent_private` or `persistent_redistributable`.
- Storage or embedding permission not set to `allowed` or `conditional`.
- Redistributable publication without allowed or conditional redistribution permission.

## Stable Errors

| HTTP | Code | Meaning |
|---:|---|---|
| 400 | `LICENSE_NAME_REQUIRED` | License name is empty |
| 400 | `LICENSE_INVALID_STATUS` | Unsupported license status |
| 400 | `LICENSE_INVALID_PERMISSION` | Unsupported permission value |
| 400 | `LICENSE_INVALID_DATE_RANGE` | `valid_until` precedes `valid_from` |
| 404 | `LICENSE_NOT_FOUND` | License ID does not exist |
| 404 | `LICENSE_SOURCE_NOT_FOUND` | Source ID does not exist |
| 409 | `LICENSE_PERMISSION_DOCUMENT_REQUIRED` | No permission document key is registered |
| 409 | `LICENSE_PUBLICATION_BLOCKED` | Fail-closed publication policy denied use |
