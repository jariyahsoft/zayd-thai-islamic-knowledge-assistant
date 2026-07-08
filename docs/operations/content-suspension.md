# Content Suspension and Rollback

Published document lifecycle controls exist for urgent content, citation, license, or review issues discovered after publication.

## Actions

- Suspend: hides the current published version from new retrieval while keeping the document restorable.
- Archive: hides the current published version and clears the document's published version pointer.
- Rollback: hides the current published version and restores a previously approved or published version that already has retrieval chunks.

All actions require `documents.archive` plus a service-side `admin` or `senior_scholar` role check. Every action requires a non-empty reason and optionally accepts a base row version for optimistic concurrency.

## Retrieval Visibility

Suspension and archival set all chunks for the affected published version to `is_published=false`. Rollback also hides chunks from the superseded version and sets chunks for the target version to `is_published=true`. Retrieval services must filter on published chunks only.

## Historical Answers

The lifecycle service discovers historical answers through `retrieval_results` that referenced affected chunks. Each affected answer receives:

- `invalidated_at`
- `answer_json["invalidation_warning"]`
- an entry in `answer_json["warnings"]`

This makes old answers visibly stale without deleting conversation history.

## Citations

Citations attached to affected chunks are marked unverified and receive `invalidated_at`. Later citation registry and verification tasks can re-verify or replace these records.

## Audit

Each mutation writes an immutable audit log with:

- previous and current published version IDs
- lifecycle action
- affected chunk, citation, and answer counts
- actor, reason, trace/request ID
- policy version `document-lifecycle-v1`

Audit summaries must not include document text, answer bodies, user message bodies, signed URLs, credentials, or production payloads.
