# Feedback Review Queue

The feedback review queue is available only to authenticated privileged reviewers. It supports
filtering by status, category, priority, severity, assignee, and assignment state.

Each queue item contains only the minimum triage metadata. The review detail exposes the answer,
citation, retrieval-run, model, prompt, and policy identifiers needed to reproduce the report; it
does not expose a reporter identity or conversation transcript.

Reviewers can assign an item, classify its root cause, record private reviewer notes, and resolve
or dismiss it with a corrective-action record. Priority orders the queue as critical, high,
normal, then low. Severity is recorded as `P0` through `P3`; P0/P1 escalation, incidents, and
source/document suspension are handled by the subsequent incident-management workflow.

All queue mutations require MFA-backed `feedback.manage` permission and write immutable,
privacy-safe audit events. Resolution and reviewer-note text are not copied into audit summaries.

## API

- `GET /admin/feedback` — list the queue
- `GET /admin/feedback/{feedback_id}/review` — load a review detail
- `PUT /admin/feedback/{feedback_id}/assign` — assign or unassign
- `PATCH /admin/feedback/{feedback_id}/classify` — add classification and reviewer notes
- `POST /admin/feedback/{feedback_id}/resolve` — resolve or dismiss with corrective action
