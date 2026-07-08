# Scholar Approval Workflow

TASK-06-03 adds explicit approval records for senior-scholar and board review before later publishing tasks can make reviewed content searchable.

## Risk Matrix

| Content risk | Required active approvals |
|---|---|
| `routine` | `initial` |
| `sensitive` | `initial`, `scholar` |
| `restricted` | `initial`, `scholar`, `board` |

`GET /documents/{document_version_id}/approval-requirements?content_risk=...` returns the required, satisfied, and missing approval levels. Publishing code must treat `ready_for_publish: false` as a hard stop.

## Approval Rules

- `initial` approval can be created by a reviewer, translator, senior scholar, or admin with `documents.review`.
- `scholar` approval requires `senior_scholar` or `admin`.
- `board` approval requires `admin`.
- The uploader, review-task creator, and any actor who already approved the version at another level cannot satisfy another incompatible level.
- Active duplicate approvals for the same `document_version_id` and `approval_level` are rejected.

## Expiry and Revocation

Approvals have explicit lifecycle states:

- `active`: counts toward publishing requirements when not past `valid_until`.
- `expired`: no longer counts toward publishing requirements.
- `revoked`: no longer counts toward publishing requirements and records `revoked_at`, `revoked_by`, and `revoke_reason`.

Operators should expire approvals through the service workflow rather than manually editing database rows. Revocation requires a senior scholar or admin and records an immutable audit event.

## API Surface

- `POST /reviews/{review_task_id}/approvals` creates an approval record.
- `GET /documents/{document_version_id}/approval-requirements` checks whether a version satisfies the required approval matrix for a risk tier.
- `POST /review-approvals/{approval_id}/revoke` revokes an active approval.

All routes use the existing `documents.review` permission boundary and privileged MFA enforcement inherited from the API authorization layer.

## Audit and Privacy

Approval creation, expiry, and revocation write sanitized audit events with actor, trace ID, approval level, content risk, document version, and policy version. Audit summaries must not include religious text contents, private document payloads, credentials, signed URLs, or raw review notes beyond the short reason supplied by the actor.

## Publishing Boundary

This task does not publish documents. TASK-06-04 must call the approval requirement check before changing publish visibility, generating chunks, or making a version retrievable.
