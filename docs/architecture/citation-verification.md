# Citation Verification Engine

The citation verification engine checks whether generated claims are allowed to
cite specific registry tokens and whether those citations actually support the
claims. Deterministic checks always run before any optional model evaluation.

## Versioned Contract

| Contract | Version |
|---|---|
| Verification engine | `citation-verification-v1` |

Primary entry points:

- `CitationVerificationEngine.verify()`
- `CitationVerificationAnswerVerifier` for answer-orchestrator integration
- `load_evidence_packs()` for loading registry/chunk evidence through the UoW

## Policy Order

1. Token must be backend-allowed (`allowed_tokens`)
2. Citation must exist in the provided evidence packs / registry
3. Citation must be active (`verified` and not invalidated)
4. Chunk and document version must be published
5. Declared reference must match the canonical reference when provided
6. Quoted text must appear in source text when a quote is present
7. Claim text must have sufficient support overlap with evidence text
8. Declared or requested madhhab must be consistent with evidence madhhab

Optional LLM evaluator signals are non-authoritative. They cannot upgrade an
invalid, unpublished, or unsupported citation to a verified result.

## Claim-Level Machine-Readable Results

Every claim receives a structured result:

```json
{
  "claim_id": "c1",
  "claim_text_hash": "sha256...",
  "citation_tokens": ["CIT-..."],
  "support_status": "supported",
  "reason_codes": ["CLAIM_SUPPORTED"],
  "claim_support_score": 0.72,
  "checks": [
    {"name": "allowed_token", "outcome": "pass"},
    {"name": "existence", "outcome": "pass"},
    {"name": "active_status", "outcome": "pass"},
    {"name": "publication_status", "outcome": "pass"},
    {"name": "reference_correctness", "outcome": "pass"},
    {"name": "quote_fidelity", "outcome": "pass"},
    {"name": "claim_support", "outcome": "pass", "reason_code": "CLAIM_SUPPORTED"},
    {"name": "madhhab_consistency", "outcome": "pass"}
  ],
  "verification_version": "citation-verification-v1"
}
```

`support_status` values:

| Status | Meaning |
|---|---|
| `supported` | All required checks passed |
| `partial` | Some lexical support, below full-support threshold |
| `unsupported` | Registered/active citation does not support the claim |
| `invalid_citation` | Unregistered, not allowed, inactive, unpublished, or bad reference |
| `unverifiable` | No citation tokens attached to the claim |

## Quote Fidelity

When `quoted_text` is supplied, the engine compares the quote against:

- chunk content
- normalized chunk content
- citation Arabic text
- citation Thai translation

Matching uses NFC normalization, Thai/Arabic normalizers, and containment. This
implements deterministic quote fidelity for FR-CIT-011.

## Claim Support

Claim support is a deterministic lexical overlap score between claim tokens and
evidence tokens. Thai and Arabic text also use character n-grams so support
checks work without an external word segmenter.

Default thresholds:

| Threshold | Default |
|---|---:|
| Supported overlap | `0.25` |
| Partial overlap | `0.12` |

These thresholds are versioned behavior of `citation-verification-v1` and should
only change with tests and review.

## Fail-Closed Visibility Rules

The verifier never treats the following as valid support:

- tokens absent from `allowed_tokens`
- tokens not present in evidence packs / registry
- inactive or invalidated citations
- unpublished chunks
- non-published document versions

`load_evidence_packs()` still returns inactive or unpublished rows with status
flags set so the engine can fail closed with explicit reason codes rather than
silently dropping evidence.

## Answer Orchestration Integration

`CitationVerificationAnswerVerifier` implements the answer orchestrator
`AnswerVerifier` protocol:

- Failed verification returns `needs_revision` with claim-level results in the
  verification trace
- The orchestrator revises within `max_revision_attempts`
- Unrecovered failures abstain

When candidate metadata lacks full evidence packs, the adapter falls back to the
legacy allowed-token subset check so lightweight fixtures remain usable. Production
composition should supply `citation_token`, `citation_id`, and `chunk_content`
metadata on retrieval candidates or call `load_evidence_packs()` explicitly.

## Safe Trace Rules

Verification traces may include:

- claim IDs and claim text hashes
- citation tokens and IDs
- check names, outcomes, and reason codes
- overlap scores and threshold metadata
- verification version and trace IDs

They must not include hidden chain-of-thought, provider secrets, raw user
conversation payloads beyond the claim fields needed for verification, PHI, or
restricted datasets outside reviewed evidence already attached to the request.

## Current Boundaries

- The engine verifies claim support and citation integrity. It does not mint
  citation IDs; that remains `citation-registry-v1`.
- Semantic entailment beyond lexical/n-gram support is not claimed.
- Prompt version management and streaming chat remain later tasks.
