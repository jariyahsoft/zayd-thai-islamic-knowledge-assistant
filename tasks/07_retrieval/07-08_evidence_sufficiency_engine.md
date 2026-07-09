# TASK-07-08 — Evidence Sufficiency Engine

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- FR-RET-012
- FR-RET-014
- SRS §27 Evidence Sufficiency

## Objective

Implement deterministic sufficiency rules using result count, scores, source approval, madhhab consistency, citation completeness and conflict signals.

## Scope

### In Scope

- Implement deterministic sufficiency rules using result count, scores, source approval, madhhab consistency, citation completeness and conflict signals.
- Optionally support an LLM evaluator as a non-authoritative secondary signal.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-07-06
- TASK-07-07

## Expected Files

- Implementation files under the relevant `07_retrieval` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Record retrieval configuration and model/index versions.
- Enforce status/license filters inside data-access queries, not after retrieval.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Do not allow filters to be bypassed through query expansion or provider fallback.

## Acceptance Criteria

- [x] Returns SUFFICIENT, PARTIALLY_SUFFICIENT, INSUFFICIENT or CONFLICTING with reason codes.
- [x] Insufficient evidence cannot silently proceed as high-confidence answer.
- [x] Rules and thresholds are versioned.

## Required Tests

### Unit and Contract Tests

- Decision-table tests
- Conflicting-source cases
- Threshold regression tests
- LLM evaluator failure tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/architecture/evidence-sufficiency.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/retrieval/src/zayd_service_retrieval/evidence_sufficiency.py` (new)
- `services/retrieval/src/zayd_service_retrieval/__init__.py`
- `services/retrieval/tests/test_evidence_sufficiency.py` (new)
- `docs/architecture/evidence-sufficiency.md` (new)
- `tasks/07_retrieval/07-08_evidence_sufficiency_engine.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `uv run pytest services/retrieval/tests/test_evidence_sufficiency.py -v`
- `uv run pytest services/retrieval/tests/test_full_text_search.py services/retrieval/tests/test_vector_search.py services/retrieval/tests/test_hybrid_search.py services/retrieval/tests/test_query_expansion.py services/retrieval/tests/test_reranker.py services/retrieval/tests/test_evidence_sufficiency.py services/retrieval/tests/test_retrieval_imports.py -v`
- `uv run ruff check services/retrieval/src/zayd_service_retrieval/evidence_sufficiency.py services/retrieval/src/zayd_service_retrieval/__init__.py services/retrieval/tests/test_evidence_sufficiency.py`
- `uv run mypy services/retrieval/src/zayd_service_retrieval/evidence_sufficiency.py services/retrieval/src/zayd_service_retrieval/__init__.py --ignore-missing-imports`
- `python3 -m py_compile services/retrieval/src/zayd_service_retrieval/evidence_sufficiency.py services/retrieval/src/zayd_service_retrieval/__init__.py services/retrieval/tests/test_evidence_sufficiency.py && git diff --check`

### Acceptance Criteria Result

- Passed. The service returns all four canonical `EvidenceStatus` values with deterministic reason codes and trace metadata.
- Passed. `INSUFFICIENT`, `PARTIALLY_SUFFICIENT`, and `CONFLICTING` all set `allow_high_confidence_answer = false`; insufficient evidence also sets `should_abstain = true`.
- Passed. Rules and thresholds are configured through versioned `EvidenceSufficiencyThresholds`.

### Security and License Review

- No secrets, production data, PHI, restricted religious datasets, or third-party code were introduced.
- Evidence evaluation consumes retrieval/reranker candidates only and does not create new candidates or bypass publication/license filters.
- Optional LLM evaluator output is non-authoritative; evaluator failure is recorded without changing the rule-based decision.

### Known Limitations

- Conflict detection depends on explicit metadata signals (`conflict_signal`, `conflict_group`, `stance`) until citation and source-governance tasks add richer contradiction metadata.
- Freshness rules are represented by versioned thresholds but no time-sensitive source freshness policy exists yet.

### Follow-up Tasks

- TASK-08-06 Answer Orchestration Workflow should enforce `allow_high_confidence_answer`, `should_search_more`, and `should_abstain`.

### Commit

- Focused commit created for TASK-07-08.
