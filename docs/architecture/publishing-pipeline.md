# Document Publishing Pipeline

TASK-06-04 adds the first retrieval-visible document publishing service. The service is intentionally conservative: it freezes only a single scholar-approved version, records all policy and pipeline versions, and flips retrieval visibility only at the end of one database transaction.

## Gates

Publishing requires:

- `documents.publish` RBAC permission at the API layer.
- `admin` or `senior_scholar` role at the service layer.
- Non-empty publish reason.
- Document status `scholar_approved`.
- Active scholar approvals required by `content_risk`:
  - `routine`: `initial`
  - `sensitive`: `initial`, `scholar`
  - `restricted`: `initial`, `scholar`, `board`
- A source license that passes `evaluate_license_policy(..., workflow="retrieval")` immediately before publishing.
- Non-empty reviewed extracted text.

The service fails closed for missing document, missing version, missing license, missing approvals, unsupported status, denied license policy, and empty content.

## Atomic Visibility

Chunks are generated with `is_published=false`. The service records publishing metadata on the `document_versions.metadata_json["publishing"]` object before visibility changes, then sets:

- `document_versions.status = "published"`
- `document_versions.frozen_at`
- every generated chunk `is_published = true`
- `documents.review_status = "published"`
- `documents.published_version_id`

All changes are committed together. If the pipeline fails before the visibility flip, the unit of work rolls back and no published chunk is searchable.

## Idempotency

Retries for an already published version return the existing published chunks and mark the result `idempotent=true`. If a previous attempt created draft chunks but never committed a published document state, the service deletes chunks for that version and regenerates them deterministically before publishing. This prevents duplicate chunks on retry.

Chunk content hashes include version ID, chunk index, canonical reference, and normalized content. The database schema also enforces unique chunk index and content hash per version.

## Pipeline Versions

The current versions are:

- Publishing policy: `document-publish-v1`
- Chunking strategy: `publish-chunker-v1`
- Embedding record pipeline: `embedding-record-v1`
- Canonical citation pipeline: `canonical-citation-v1`
- License policy engine: `license-policy-engine-v1`
- Scholar approval policy: `scholar-approval-v1`

Embedding and citation provider integrations are not executed in this task. Instead, each chunk records deterministic embedding and citation metadata with the pipeline version, canonical reference, and `pending_provider` embedding status. Later retrieval and citation tasks can replace those placeholders with provider-backed records without changing the publishing gate.

## Audit

Successful and license-denied publish attempts create immutable audit records with sanitized metadata only. Audit summaries include IDs, status, policy versions, counts, and reason codes; they do not include document text, secrets, signed URLs, credentials, or raw review payloads.
