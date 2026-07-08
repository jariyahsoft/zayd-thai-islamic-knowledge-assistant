# Review Queue API

## Overview

The Review Queue API provides paginated listing, filtering, assignment, claim, release, and escalation operations for document review tasks.  It enforces RBAC and reviewer-specialization visibility rules.

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/reviews/queue` | List review tasks with filters and pagination |
| `GET` | `/reviews/{review_task_id}` | Get detailed view of a single review task |
| `POST` | `/reviews/{review_task_id}/claim` | Claim a task for yourself |
| `POST` | `/reviews/{review_task_id}/release` | Release a claimed task back to the open pool |
| `POST` | `/reviews/{review_task_id}/assign` | Assign a task to a specific user (admin/senior-scholar only) |
| `POST` | `/reviews/{review_task_id}/escalate` | Create a scholar-level review task for escalation |

## Authentication

All endpoints require a valid Bearer access token obtained via `/auth/login` or `/auth/register`.

## Authorization

All endpoints require the `documents.review` permission.  Additionally:

- **Admin / Senior-scholar**: can see all tasks, assign tasks, and release any task.
- **Reviewer**: sees only tasks matching their preferred language and madhhab.  Scholar-level tasks are hidden.
- **Translator**: sees tasks matching their preferred language (madhhab filter is not applied).
- **Claim**: the caller must be the assigned reviewer (or the task must be unassigned).
- **Assign**: only admin and senior-scholar roles can assign tasks to other users.
- **Escalate**: the assigned reviewer or a privileged user can escalate.

## Filters (`GET /reviews/queue`)

| Parameter | Type | Description |
|---|---|---|
| `language` | `str` | Filter by task language |
| `madhhab` | `str` | Filter by task madhhab |
| `content_type` | `str` | Filter by document category |
| `status` | `str` | Filter by task status (`open`, `in_progress`, `completed`, `cancelled`) |
| `priority` | `str` | Filter by priority (`urgent`, `high`, `normal`, `low`) |
| `assigned_to` | `UUID` | Filter by assigned user |
| `review_level` | `str` | Filter by review level (`initial`, `scholar`) |
| `due_before` | `ISO-8601` | Tasks due on or before this datetime |
| `due_after` | `ISO-8601` | Tasks due on or after this datetime |
| `limit` | `int` | Max results (default 50, max 200) |
| `offset` | `int` | Pagination offset |

## Visibility Rules

The queue endpoint filters tasks based on the caller's role:

- **Admin / Senior-scholar**: all tasks are visible.
- **Reviewer**: only non-scholar tasks whose `language` matches the user's `preferred_language` and whose `madhhab` is either unset, `unknown`, `general`, `other`, or matches the user's `preferred_madhhab`.
- **Translator**: only non-scholar tasks whose `language` matches the user's `preferred_language` (no madhhab restriction).

## Response Models

### ReviewTaskSummaryResponse

| Field | Type | Description |
|---|---|---|
| `id` | `str` | Review task UUID |
| `document_version_id` | `str` | Associated document version |
| `document_id` | `str` | Associated document |
| `review_level` | `str` | `initial` or `scholar` |
| `status` | `str` | `open`, `in_progress`, `completed`, `cancelled` |
| `priority` | `str` | `urgent`, `high`, `normal`, `low` |
| `category` | `str \| None` | Document type category |
| `language` | `str \| None` | Document language |
| `madhhab` | `str \| None` | Document madhhab |
| `assigned_to` | `str \| None` | Assigned user UUID |
| `due_at` | `str \| None` | ISO-8601 due datetime |
| `created_at` | `str` | ISO-8601 creation datetime |
| `updated_at` | `str` | ISO-8601 last update datetime |
| `document_title` | `str \| None` | Document title from metadata |
| `document_type` | `str \| None` | Document type from metadata |

### ReviewTaskDetailResponse (extends Summary)

| Field | Type | Description |
|---|---|---|
| `created_by` | `str` | UUID of the user who created the task |
| `original_file_key` | `str \| None` | Object storage key for the original file |
| `extracted_text_preview` | `str \| None` | First 500 characters of extracted text |
| `filename` | `str \| None` | Original filename |
| `content_type` | `str \| None` | MIME content type |

### ReviewQueueListResponse

| Field | Type | Description |
|---|---|---|
| `tasks` | `list[ReviewTaskSummaryResponse]` | Task list |
| `total_count` | `int` | Total matching tasks |
| `limit` | `int` | Page size |
| `offset` | `int` | Current offset |
| `next_offset` | `int \| None` | Offset for next page or `null` |

### ReviewTaskActionResponse

| Field | Type | Description |
|---|---|---|
| `status` | `str` | `"ok"` |
| `task` | `ReviewTaskSummaryResponse` | Updated task |

## Error Codes

| Code | HTTP Status | Description |
|---|---|---|
| `REVIEW_TASK_NOT_FOUND` | 404 | Review task does not exist |
| `REVIEW_TASK_INVALID_STATUS` | 409 | Operation not allowed for current status |
| `REVIEW_TASK_NOT_ASSIGNED` | 403 | Task is not assigned to the caller |
| `REVIEW_QUEUE_ACCESS_DENIED` | 403 | Caller not authorized for this operation |
| `REVIEW_QUEUE_ESCALATION_EXISTS` | 409 | Scholar-level task already exists for this version |
| `REVIEW_USER_NOT_FOUND` | 404 | Assignee user does not exist or is inactive |
| `REVIEW_QUEUE_ALREADY_ASSIGNED` | 409 | Task is already assigned to another user |

## Examples

### List open high-priority tasks

```http
GET /reviews/queue?status=open&priority=high&limit=20
Authorization: Bearer <access-token>
```

### Claim a task

```http
POST /reviews/{review_task_id}/claim
Authorization: Bearer <access-token>
```

### Assign a task (admin only)

```http
POST /reviews/{review_task_id}/assign
Authorization: Bearer <access-token>
Content-Type: application/json

{
  "assignee_user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Escalate to scholar review

```http
POST /reviews/{review_task_id}/escalate
Authorization: Bearer <access-token>
```
