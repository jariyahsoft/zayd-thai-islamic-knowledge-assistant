# Answer Orchestrator

`AnswerOrchestrator` implements the TASK-08-06 answer workflow as a traceable
state machine. It coordinates classification, deterministic risk policy,
retrieval, evidence sufficiency, optional expanded retrieval, generation,
verification, revision, abstention, and terminal response construction.

## Versioned Contracts

| Contract | Version |
|---|---|
| Orchestrator | `answer-orchestrator-v1` |
| Answer schema | `answer-response-v1` |
| Default prompt | `answer-generation-prompt-v1` |

Every terminal result records the orchestrator version, prompt version,
classification schema version, risk policy version, evidence rules version when
available, terminal status, and safe step traces.

## State Machine

```text
validate
  -> idempotency
  -> classify
  -> policy
  -> retrieve
  -> evidence
  -> expand_retrieve when evidence says search more
  -> evidence
  -> generate when evidence permits an answer
  -> verify
  -> revise when verification fails and retry budget remains
  -> return
```

Terminal states:

- `completed`
- `abstained`
- `escalated`
- `restricted`
- `failed`
- `cancelled`

## Policy and Evidence Gates

The workflow fails closed:

- restricted policy decisions return before retrieval or generation
- scholar escalation returns a limited response instead of deciding a personal case
- insufficient evidence triggers expanded retrieval and then abstention if still insufficient
- conflicting evidence escalates instead of forcing a single conclusion
- generated answers must pass deterministic verification before return
- citation verification failure triggers revision, then abstention if unrecovered

The LLM generator is never authoritative over deterministic policy,
evidence-sufficiency, or citation verification.

## Idempotency

When `idempotency_key` is supplied, terminal results are stored through
`AnswerOrchestrationStore`. Repeating the same key returns the cached result and
does not call retrieval or generation again. The in-memory store is suitable only
for tests and local composition; production persistence belongs in later API and
conversation-history tasks.

## Timeout and Cancellation

The public `answer()` method wraps provider work in `asyncio.wait_for` using
`timeout_seconds`. Timeout cancels the running provider task and returns
`ANSWER_TIMEOUT`. External cancellation propagates as `CancelledError` so the API
layer can stop downstream work where supported.

## Safe Trace Rules

Step traces may include:

- step name and status
- schema and policy versions
- retrieval candidate counts
- evidence status and reason codes
- policy action and escalation target
- provider name, finish reason, and token counts

Step traces must not include raw question text, full prompts, message payloads,
answer text, hidden chain-of-thought, secrets, tokens, credentials, production
payloads, or PHI.

## Citation Verification

Production answer composition should inject
`CitationVerificationAnswerVerifier` so claim-level checks from
`citation-verification-v1` run during the verify/revise loop. Failed
verification triggers revision, then abstention if unrecovered.

Retrieval candidates used with the claim-level verifier should carry:

- `citation_token`
- `citation_id`
- `chunk_content`
- publication and active status flags when available

When that metadata is absent, the verifier falls back to the lightweight
allowed-token subset check used by offline fixtures.

## Current Limitations

- The default template generator is deterministic for offline tests. Production
  model behavior should use the provider SDK through `LLMAnswerGenerator`.
- The in-memory idempotency store is not durable and must be replaced by
  persistence in later API/conversation tasks.
- Prompt version management remains TASK-08-09.
