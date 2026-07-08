# Document Review API Reference

Describes endpoints and contracts to manage review drafts, text and metadata edits, comments, and decision transitions.

## Overview

Reviews are tracked using optimistic locks via task `row_version` values. Every edit generates an immutable revision mapping exact text and metadata changes.

## Authentication and Scopes

All routes are gated by the `documents.review` permission boundary. Privileged operations require MFA verification. Uploader-approval separation is enforced to prevent self-approvals.

## API Contracts

### GET /reviews/{review_task_id}/draft

Fetch the current writable draft version of a review task.

**Response** (200 OK)
```json
{
  "review_task_id": "8b51d7b3-6cfc-4cc3-92f7-2dcf1fcd6999",
  "document_version_id": "c1f77d4c-be88-4f1b-a59f-2da9e763ebd2",
  "task_status": "in_progress",
  "task_row_version": 2,
  "document_review_status": "in_review",
  "original_file_key": "uploads/original-file.txt",
  "editable_text": "Updated text content of version",
  "editable_metadata": {
    "title": "Document Title",
    "author": "Author Name Address"
  },
  "latest_revision_number": 1,
  "comments": [
    {
      "id": "e458e0a1-77b3-4f9d-83b6-200762ea1111",
      "review_task_id": "8b51d7b3-6cfc-4cc3-92f7-2dcf1fcd6999",
      "author_id": "22ffef9a-4c28-4ce6-a7fe-4fa2c6ebdb6a",
      "body": "Need to clarify spelling",
      "anchor": {
        "line": 4
      },
      "created_at": "2026-07-08T16:00:00Z"
    }
  ]
}
```

### PATCH /reviews/{review_task_id}/draft

Submits text and/or metadata edits. Edits require the current loaded `base_task_row_version` to prevent write collisions.

**Request**
```json
{
  "base_task_row_version": 2,
  "text": "Corrected text content of version",
  "metadata_updates": {
    "title": "Validated Document Title"
  }
}
```

**Response** (200 OK)
```json
{
  "status": "ok",
  "task_row_version": 3,
  "revision": {
    "id": "f8a011de-3e3d-4958-8b9a-7a5f6e80b2a1",
    "review_task_id": "8b51d7b3-6cfc-4cc3-92f7-2dcf1fcd6999",
    "document_version_id": "c1f77d4c-be88-4f1b-a59f-2da9e763ebd2",
    "actor_user_id": "22ffef9a-4c28-4ce6-a7fe-4fa2c6ebdb6a",
    "revision_number": 2,
    "base_task_row_version": 2,
    "text_changed": true,
    "metadata_changed_fields": ["title"],
    "diff_text": "@@ -1,3 +1,3 @@\n-Updated text content of version\n+Corrected text content of version",
    "created_at": "2026-07-08T16:05:00Z"
  },
  "editable_text": "Corrected text content of version",
  "editable_metadata": {
    "title": "Validated Document Title",
    "author": "Author Name Address"
  }
}
```

### POST /reviews/{review_task_id}/comments

Appends a comment anchored to the draft.

**Request**
```json
{
  "body": "Spelling corrected according to dictionary",
  "anchor": {
    "line": 1
  }
}
```

**Response** (200 OK)
```json
{
  "id": "a6b1c7d2-ee1d-45db-b27b-3ef1a1be2e6c",
  "review_task_id": "8b51d7b3-6cfc-4cc3-92f7-2dcf1fcd6999",
  "author_id": "22ffef9a-4c28-4ce6-a7fe-4fa2c6ebdb6a",
  "body": "Spelling corrected according to dictionary",
  "anchor": {
    "line": 1
  },
  "created_at": "2026-07-08T16:07:00Z"
}
```

### POST /reviews/{review_task_id}/decision

Approve, reject, or request changes on a review task.

**Request**
```json
{
  "decision": "approve",
  "reason": "Draft has spelling mistakes resolved.",
  "base_task_row_version": 3
}
```

**Response** (200 OK)
```json
{
  "status": "ok",
  "task_row_version": 4,
  "decision": {
    "id": "e5cda92d-94c6-4b9d-a4e3-6aa1de8efd23",
    "review_task_id": "8b51d7b3-6cfc-4cc3-92f7-2dcf1fcd6999",
    "document_version_id": "c1f77d4c-be88-4f1b-a59f-2da9e763ebd2",
    "actor_user_id": "22ffef9a-4c28-4ce6-a7fe-4fa2c6ebdb6a",
    "decision": "approve",
    "reason": "Draft has spelling mistakes resolved.",
    "resulting_task_status": "completed",
    "resulting_document_status": "scholar_review",
    "created_at": "2026-07-08T16:10:00Z"
  }
}
```

## Error Codes

| Status Code | Error Code | Reason |
|---|---|---|
| `404` | `DOCUMENT_REVIEW_TASK_NOT_FOUND` | Task ID does not map to any database entity. |
| `403` | `DOCUMENT_REVIEW_ACCESS_DENIED` | Actor is not assigned, lacks reviewer scopes, or accesses a scholar task without a senior role. |
| `409` | `DOCUMENT_REVIEW_CONFLICT` | Task version has been updated concurrently. |
| `400` | `DOCUMENT_REVIEW_EMPTY_EDIT` | Update fields match existing values. |
| `403` | `DOCUMENT_REVIEW_SELF_APPROVAL_DENIED` | Approving uploader's or task creator's own document is prohibited. |
