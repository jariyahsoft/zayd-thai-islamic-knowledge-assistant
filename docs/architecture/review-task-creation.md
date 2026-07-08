# Review Task Creation Architecture

## Overview

The **Review Task Creation Service** automatically creates review tasks after
successful document parsing and metadata extraction.  Each reviewable document
version gets one active review task per review level.  Failed or quarantined
documents are excluded from review.

```
Upload → Malware Scan → Parse → Normalize → Metadata Extract → Review Task Creation
                                                                        ↓
                                                         Review Queue (TASK-06-01)
```

## Design Principles

1. **One active task per version + level.**  A unique constraint prevents
   duplicate open review tasks for the same document version and review level.

2. **Failed documents never enter review.**  Version status must be
   `scanned_clean` or `parsed`.  Document review status must be `draft` or
   `revision_requested`.  Infected, rejected, or cancelled documents are
   rejected.

3. **Idempotent creation.**  Creating a review task for the same version and
   level twice raises `REVIEW_TASK_ALREADY_EXISTS` but does not create
   duplicate tasks or audit events.

4. **Configurable assignment rules.**  Priority, review level, and due date
   are determined from document metadata using configurable mappings.

## Assignment Rules

### Priority Resolution

| Madhhab | Priority | Due Date |
|---|---|---|
| shafii | high | 7 days |
| hanafi | high | 7 days |
| maliki | normal | 14 days |
| hanbali | normal | 14 days |
| jafari | normal | 14 days |
| unknown | normal | 14 days |

Priority and due date can be customized by extending the `_PRIORITY_MAP` and
`_DUE_DAYS_BY_PRIORITY` dictionaries.

### Review Level

Default review level is `initial`.  A custom level can be specified by the
caller (e.g., `scholar` for second-level review).

### Category, Language, Madhhab

These fields are copied from the Document to the ReviewTask to enable
reviewer matching in downstream queue processing.

## Eligibility Checks

### Document Version Status

Eligible: `scanned_clean`, `parsed`
Ineligible: `uploaded`, `rejected`, any other status

### Document Review Status

Eligible: `draft`, `revision_requested`
Ineligible: `rejected`, `published`, `suspended`

## API

The service is called programmatically during ingestion:

```python
from zayd_common.review_tasks import ReviewTaskService

service = ReviewTaskService(uow)
task = service.create_review_task(
    document_version_id=version_id,
    actor_user_id=actor_id,
    review_level="initial",  # optional, defaults to "initial"
    trace_id="req-123",
)
```

## Error Codes

| Code | Meaning |
|---|---|
| `REVIEW_VERSION_NOT_FOUND` | Document version or document not found |
| `REVIEW_VERSION_NOT_ELIGIBLE` | Version/review status is not eligible |
| `REVIEW_TASK_ALREADY_EXISTS` | Active task already exists for this version+level |

## Security

- Creation requires an authenticated `actor_user_id`.
- Every creation is audited via `AuditLog` with action `review_task.created`.
- Audit summaries include document/version IDs, review level, priority, and
  policy version.
- RBAC enforcement is delegated to the API layer.
