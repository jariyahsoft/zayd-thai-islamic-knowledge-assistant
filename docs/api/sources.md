# Sources API

## Overview

The Sources API provides endpoints for managing knowledge sources in the Zayd platform. Sources represent the origin of Islamic knowledge documents, such as hadith collections, Quran translations, fiqh books, and scholarly works.

## Authentication

All endpoints require authentication via Bearer token and appropriate RBAC permissions:

- **Read operations**: `licenses.read` permission
- **Write operations**: `licenses.manage` permission

Privileged operations additionally require MFA enrollment and verification.

## Base Path

All endpoints are prefixed with `/admin/sources`

## Data Model

### Source

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Unique identifier |
| `name` | string | Source name (1-500 chars) |
| `source_type` | string | Type of source (e.g., "hadith", "quran", "fiqh", "tafsir") |
| `owner` | string? | Owner or publisher name |
| `website` | string? | Source website URL |
| `language` | string | ISO 639-1 language code (2-10 chars) |
| `country` | string? | ISO 3166-1 country code |
| `reliability_level` | integer | Reliability rating from 1 (lowest) to 5 (highest) |
| `is_active` | boolean | Whether the source is active and can be assigned to new documents |
| `created_by` | UUID | User who created the source |
| `updated_by` | UUID? | User who last updated the source |
| `created_at` | ISO-8601 | Creation timestamp |
| `updated_at` | ISO-8601 | Last update timestamp |

## Endpoints

### Create Source

Create a new knowledge source.

```http
POST /admin/sources
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "name": "Sahih Bukhari Thai Translation",
  "source_type": "hadith",
  "language": "th",
  "reliability_level": 5,
  "owner": "Islamic Foundation of Thailand",
  "website": "https://example.com",
  "country": "TH",
  "is_active": true
}
```

**Response** `201 Created`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Sahih Bukhari Thai Translation",
  "source_type": "hadith",
  "language": "th",
  "reliability_level": 5,
  "owner": "Islamic Foundation of Thailand",
  "website": "https://example.com",
  "country": "TH",
  "is_active": true,
  "created_by": "user-uuid",
  "updated_by": null,
  "created_at": "2026-07-06T12:00:00Z",
  "updated_at": "2026-07-06T12:00:00Z"
}
```

**Errors**

- `400 SOURCE_NAME_REQUIRED` - Source name is empty or whitespace
- `400 SOURCE_INVALID_RELIABILITY` - Reliability level not between 1-5
- `401 AUTH_UNAUTHENTICATED` - Missing or invalid authentication
- `403 RBAC_FORBIDDEN` - Missing `licenses.manage` permission

### Get Source

Retrieve a source by ID.

```http
GET /admin/sources/{source_id}
Authorization: Bearer <access_token>
```

**Response** `200 OK`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Sahih Bukhari Thai Translation",
  "source_type": "hadith",
  "language": "th",
  "reliability_level": 5,
  "owner": "Islamic Foundation of Thailand",
  "website": "https://example.com",
  "country": "TH",
  "is_active": true,
  "created_by": "user-uuid",
  "updated_by": null,
  "created_at": "2026-07-06T12:00:00Z",
  "updated_at": "2026-07-06T12:00:00Z"
}
```

**Errors**

- `404 SOURCE_NOT_FOUND` - Source does not exist or was deleted

### Update Source

Update source fields. Only provided fields are updated.

```http
PATCH /admin/sources/{source_id}
Content-Type: application/json
Authorization: Bearer <access_token>

{
  "name": "Updated Name",
  "reliability_level": 4
}
```

**Response** `200 OK`

Returns updated source object.

**Errors**

- `400 SOURCE_NAME_REQUIRED` - Source name is empty or whitespace
- `400 SOURCE_INVALID_RELIABILITY` - Reliability level not between 1-5
- `404 SOURCE_NOT_FOUND` - Source does not exist or was deleted

### Suspend Source

Mark a source as inactive. Inactive sources cannot be assigned to new documents, and existing document assignments should be reviewed.

```http
POST /admin/sources/{source_id}/suspend
Authorization: Bearer <access_token>
```

**Response** `200 OK`

Returns source object with `is_active: false`.

**Behavior**

- Idempotent: suspending an already suspended source succeeds
- Downstream services are notified to exclude this source from new document workflows
- Suspension is audited with actor, timestamp, and source metadata

**Errors**

- `404 SOURCE_NOT_FOUND` - Source does not exist or was deleted

### Search Sources

Search and filter sources with pagination.

```http
GET /admin/sources?name=Bukhari&language=th&is_active=true&limit=20&offset=0
Authorization: Bearer <access_token>
```

**Query Parameters**

| Parameter | Type | Description |
|---|---|---|
| `name` | string | Filter by name (case-insensitive partial match) |
| `source_type` | string | Filter by exact source type |
| `language` | string | Filter by exact language code |
| `country` | string | Filter by exact country code |
| `is_active` | boolean | Filter by active status |
| `reliability_level_min` | integer | Minimum reliability level (1-5) |
| `reliability_level_max` | integer | Maximum reliability level (1-5) |
| `limit` | integer | Page size (1-100, default 100) |
| `offset` | integer | Number of records to skip (default 0) |

**Response** `200 OK`

```json
{
  "sources": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Sahih Bukhari Thai Translation",
      "source_type": "hadith",
      "language": "th",
      "reliability_level": 5,
      "is_active": true,
      "created_by": "user-uuid",
      "updated_by": null,
      "created_at": "2026-07-06T12:00:00Z",
      "updated_at": "2026-07-06T12:00:00Z"
    }
  ]
}
```

**Behavior**

- Results are ordered by creation time (newest first)
- Soft-deleted sources are excluded from results
- Empty query returns all active sources

## Audit Trail

All source mutations (create, update, suspend) are recorded in the immutable audit log with:

- Actor user ID
- Action (`sources.create`, `sources.update`, `sources.suspend`)
- Resource ID (source UUID)
- Before/after summaries (name, reliability level, active status)
- Request ID and trace ID for correlation
- Timestamp

Audit records can be queried via `/admin/audit-logs` with appropriate permissions.

## Downstream Impact

### Source Suspension

When a source is suspended:

1. **Document ingestion** must reject new document uploads referencing the suspended source
2. **Published documents** remain retrievable until explicitly archived
3. **Admin UI** should display a warning when viewing documents from suspended sources
4. **Audit trail** records the suspension event with actor and reason

Future tasks (TASK-05-01 and beyond) must enforce this constraint server-side.

## Common Patterns

### Creating a High-Reliability Hadith Source

```bash
curl -X POST https://api.zayd.example.com/admin/sources \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sahih Muslim Thai Translation",
    "source_type": "hadith",
    "language": "th",
    "reliability_level": 5,
    "owner": "Islamic Center of Thailand",
    "country": "TH",
    "is_active": true
  }'
```

### Searching Active Sources by Type

```bash
curl "https://api.zayd.example.com/admin/sources?source_type=hadith&is_active=true&limit=50" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### Suspending a Source

```bash
curl -X POST "https://api.zayd.example.com/admin/sources/$SOURCE_ID/suspend" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

## Related Documentation

- [RBAC Documentation](../security/rbac.md) - Permission model
- [Audit Logging](../security/audit-logging.md) - Audit trail details
- [Source Policy](../governance/source-policy.md) - Reliability and licensing rules
- [SRS §23.2](../02_requirements/SRS.md#232-source) - Source schema specification
