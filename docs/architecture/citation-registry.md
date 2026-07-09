# Citation Registry

The citation registry is the canonical source for references that may be shown
to a user or exposed to an LLM as citation handles. It links each citation to an
immutable `document_versions` row and one reviewed `document_chunks` row.

## Versioned Contract

| Contract | Version |
|---|---|
| Registry | `citation-registry-v1` |
| LLM-visible token prefix | `CIT` |

LLM-visible handles use the form `CIT-<uuid>`. The UUID payload is a registry
record ID, not a free-form reference string. Callers must resolve tokens through
`CitationRegistryService.resolve_llm_token()` or request tokens through
`llm_tokens_for_citations()`.

## Stable IDs

`CitationRegistryService.register_citation()` creates deterministic UUIDv5 IDs
from:

```text
zayd:citation:<document_version_id>:<canonical_reference>
```

The database also enforces uniqueness for
`(canonical_reference, document_version_id)`. Re-registering the same canonical
reference for the same chunk is idempotent. Reusing that canonical reference for
a different chunk in the same document version fails with
`CITATION_CANONICAL_COLLISION`.

## Supported Metadata Families

Citation metadata is intentionally structured so retrieval and answer
verification can reject fabricated or incomplete references.

| Type | Required metadata |
|---|---|
| `quran` | `arabic_text` or `thai_translation` |
| `hadith` | `hadith_grade` |
| `book` | `volume` or `page` |
| `document` | canonical reference and display title |

All types require:

- `document_version_id`
- `chunk_id`
- `canonical_reference`
- `display_title`

`register_from_chunk()` reads `metadata_json["citation"]` from a reviewed chunk
and can carry type-specific fields such as `page`, `volume`, `hadith_grade`,
`arabic_text`, and `thai_translation` into the canonical row.

## Token Resolution

The registry prevents citation fabrication by only issuing tokens for active
rows already present in `citations`.

- malformed tokens fail with `CITATION_INPUT_INVALID`
- unknown UUID payloads fail with `CITATION_NOT_REGISTERED`
- invalidated or unverified records fail with `CITATION_INACTIVE` unless the
  caller explicitly requests historical lookup using `require_active=False`

LLM prompts should receive only tokens returned by
`llm_tokens_for_citations()`. They should not receive raw canonical reference
strings as authoritative citation handles.

## Invalidation and History

`invalidate_citation()` preserves the original citation row and records
invalidation metadata instead of deleting history:

- sets `citations.invalidated_at`
- sets `citations.verified = false`
- annotates linked `retrieval_results.metadata_json`
- invalidates answers that used retrieval runs containing the citation
- appends a warning into affected `answers.answer_json`
- writes an append-only audit record with impact counts

This makes downstream impact explicit while keeping enough history to audit why
an answer or retrieval result became stale.

## Safe Trace and Audit Rules

Registry traces and audit summaries may include IDs, tokens, status, type,
canonical reference, registry version, actor ID, trace ID, reason code, and
impact counts.

They must not include hidden chain-of-thought, provider prompts, raw user
conversation payloads, secrets, credentials, PHI, or restricted datasets. Text
fields stored in the canonical citation row must come from reviewed document
metadata or caller-supplied structured metadata, not model invention.

## Current Boundaries

The registry owns citation identity, token mapping, and invalidation
propagation. It does not decide whether a generated claim is supported by a
registered citation; that belongs to the later citation verification engine.
