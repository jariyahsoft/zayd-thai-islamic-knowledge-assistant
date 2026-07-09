# Feedback API

All responses use JSON. Error responses use:

```json
{"error":{"code":"FEEDBACK_INPUT_INVALID","message":"category is not supported."}}
```

## Authorization

- Requires bearer authentication.
- Requires permission `feedback.create` (default `user` role).

## Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/feedback` | Submit feedback linked to an answer |
| `GET` | `/feedback/{feedback_id}` | Read the submitter's own feedback receipt |

## Submit Feedback

`POST /feedback`

Request body:

```json
{
  "answer_id": "uuid",
  "category": "incorrect_answer",
  "notes": "optional free text",
  "citation_id": "uuid"
}
```

Supported categories:

- `incorrect_answer`
- `citation_error`
- `incomplete_answer`
- `inappropriate_content`
- `other`

`notes` is optional and limited to 2000 characters. `citation_id` is optional.

Success response (`201`):

```json
{
  "id": "uuid",
  "category": "incorrect_answer",
  "status": "open",
  "answer_id": "uuid",
  "citation_id": null,
  "created_at": "2026-07-09T10:00:00+00:00",
  "receipt_message": "ได้รับรายงานของคุณแล้ว ทีมตรวจสอบจะดำเนินการต่อไป"
}
```

Public responses do not include internal trace IDs, retrieval payloads, or reviewer workflow data.

## Get Feedback

`GET /feedback/{feedback_id}`

Returns the same public shape for the authenticated submitter only.

## Error Codes

| Code | HTTP | Meaning |
|---|---|---|
| `FEEDBACK_INPUT_INVALID` | 400 | Unsupported category or notes too long |
| `FEEDBACK_FORBIDDEN` | 404 | Answer not found for this user |
| `FEEDBACK_NOT_FOUND` | 404 | Feedback not found or not owned by caller |
| `FEEDBACK_RATE_LIMITED` | 429 | More than 10 submissions per hour |

## Rate Limiting

- 10 submissions per user per hour (in-memory limiter in the API process).
- Clients should show the stable error message and ask the user to retry later.

## Audit

Successful submissions write `feedback.submit` audit events with:

- `feedback_id`, `category`, `answer_id`
- `retrieval_run_id`, `model_configuration_id`, `prompt_version_id`, `policy_version_id`
- `notes_length` (not note body)

Optional request header `x-request-id` is stored as `request_id` / `trace_id` for operator correlation and is not returned to end users.