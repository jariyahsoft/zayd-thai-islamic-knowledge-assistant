# License Policy Engine

## Purpose

The License Policy Engine converts source license records into deterministic workflow decisions for
ingestion, retrieval, and export. It is ordinary application code, not prompt text, and LLM output
cannot override it.

## Policy Version

Current version: `license-policy-engine-v1`

Every decision includes:

- `policy_version`
- `source_license_version`
- `reason_codes`
- `llm_override_allowed: false`
- action-level decisions for storage, cache, embedding, commercial use, redistribution, and attribution

## Workflows

| Workflow | Required actions |
|---|---|
| `ingestion` | persistent storage and attribution |
| `retrieval` | persistent storage, embedding, and attribution |
| `export` | redistribution, commercial use, and attribution |

Unsupported workflows fail closed with `WORKFLOW_INVALID`.

## Actions

The engine always evaluates all actions:

- `persistent_storage`
- `cache`
- `embedding`
- `commercial_use`
- `redistribution`
- `attribution`

This lets downstream services inspect the exact reason a workflow was denied while still receiving a
single `workflow_allowed` result.

## Fail-Closed Rules

The engine denies operational workflows when any required action is denied.

Global blockers:

- `LICENSE_STATUS_UNKNOWN`
- `LICENSE_STATUS_PROHIBITED`
- `LICENSE_STATUS_EXPIRED`
- `LICENSE_DATE_EXPIRED`
- `LICENSE_NOT_YET_VALID`

Boundary behavior:

- `ephemeral_cache_only` can allow bounded cache only, not persistent storage or embedding.
- `review_required` can allow limited cache but not production retrieval or export.
- `persistent_private` can allow ingestion/retrieval when storage and embedding permissions allow it, but it cannot authorize export redistribution.
- `persistent_redistributable` can authorize export only when redistribution and commercial-use permissions allow it.
- Required attribution without a template denies workflows that require attribution.

## Reason Codes

Reason codes are stable machine-readable strings. Examples:

- `WORKFLOW_ALLOWED`
- `WORKFLOW_RETRIEVAL_DENIED`
- `STATUS_DOES_NOT_ALLOW_PERSISTENT_STORAGE`
- `STORAGE_PERMISSION_DENIED`
- `EMBEDDING_PERMISSION_DENIED`
- `REDISTRIBUTION_PERMISSION_ALLOWED`
- `ATTRIBUTION_TEMPLATE_MISSING`

Consumers should store the full decision object or at least the policy version, source license version,
workflow result, and reason codes for auditability.

## API

The admin API exposes:

```http
GET /admin/licenses/{license_id}/policy-decision?workflow=retrieval
```

The endpoint requires `licenses.read`, inherits privileged MFA enforcement, and writes an immutable
audit event for every decision.

The older publication authorization endpoint remains for compatibility, but delegates to the policy
engine retrieval workflow.

## Security

- The engine does not read prompts, model output, or natural-language override instructions.
- Permission evidence remains private; decisions use registry metadata only.
- Missing, ambiguous, invalid, expired, or prohibited permissions fail closed.
- Decisions are audited with sanitized metadata and do not include document contents or permission file
  contents.
