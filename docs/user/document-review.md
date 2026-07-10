# Document Review Workspace

## Purpose

The document review workspace is the reviewer-facing screen for one review task. It combines the immutable source reference, editable extracted text, editable metadata, chunk preview, comments, revision diff, and explicit review decisions.

## Access

The workspace uses the existing document review API:

- `GET /reviews/{review_task_id}/draft`
- `PATCH /reviews/{review_task_id}/draft`
- `POST /reviews/{review_task_id}/comments`
- `POST /reviews/{review_task_id}/decision`

All calls require `documents.review`. Server-side RBAC and the document-review service remain authoritative for assignment, role, self-approval, and scholar-level restrictions.

## Main Workflow

1. Open a task from the reviewer dashboard or review queue.
2. Inspect the original file key and document version in the read-only source pane.
3. Edit extracted text or metadata.
4. Use autosave or save to create an immutable revision.
5. Add anchored comments when needed.
6. Review the latest diff.
7. Submit `approve`, `request_changes`, or `reject` with a reason.

## Unsaved Changes

The workspace tracks dirty form state after text or metadata changes. If a reviewer tries to leave the browser tab with unsaved work, the browser unload guard is activated.

Autosave and save both submit the current `task_row_version`. A successful save clears the dirty state and advances the row version returned by the API.

## Concurrent Edits

Every edit and decision sends `base_task_row_version`. If another reviewer has changed the task first, the API returns `DOCUMENT_REVIEW_CONFLICT`. The workspace surfaces the conflict and prompts the reviewer to reload the latest draft before saving again.

## Source Immutability

The original source file is displayed only as a read-only reference. Edits are stored as review revisions and do not mutate the uploaded original file or `DocumentVersion.extracted_text`.

## Audit Behavior

The backend records audited events for:

- revision creation
- comments
- decisions

The workspace only sends reviewer-entered text, editable metadata, comments, decision, reason, and row-version metadata through the documented API. It does not expose provider secrets, hidden prompts, or internal model traces.

## Current Limitations

- The original file is represented by object key metadata; signed file preview/download is a later storage integration concern.
- Chunk preview is a local read-only preview derived from the editable text, not a final publishing chunk plan.
- Node-based frontend test/build verification requires a Node-enabled environment.
