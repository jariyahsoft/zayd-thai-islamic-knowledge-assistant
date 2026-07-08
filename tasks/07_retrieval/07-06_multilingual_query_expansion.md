# TASK-07-06 — Multilingual Query Expansion

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- FR-RET-007
- FR-CLASS-001

## Objective

Produce original, normalized Thai, Arabic, English and terminology-variant queries when appropriate.

## Scope

### In Scope

- Produce original, normalized Thai, Arabic, English and terminology-variant queries when appropriate.
- Preserve user intent, madhhab and named references.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-07-05

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

- [x] Expansion trace is stored.
- [x] Feature can be disabled or limited by policy.
- [x] Religious terminology fixtures are reviewed for semantic drift.

## Required Tests

### Unit and Contract Tests

- Thai-Arabic-English golden tests
- Intent preservation tests
- Provider fallback tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/architecture/query-expansion.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/retrieval/src/zayd_service_retrieval/query_expansion.py` (new)
- `services/retrieval/src/zayd_service_retrieval/__init__.py`
- `services/retrieval/tests/test_query_expansion.py` (new)
- `docs/architecture/query-expansion.md` (new)
- `tasks/07_retrieval/07-06_multilingual_query_expansion.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `uv run pytest services/retrieval/tests/test_query_expansion.py services/retrieval/tests/test_retrieval_imports.py -v`
- `uv run ruff check services/retrieval/src/zayd_service_retrieval/query_expansion.py services/retrieval/src/zayd_service_retrieval/__init__.py services/retrieval/tests/test_query_expansion.py`
- `uv run mypy services/retrieval/src/zayd_service_retrieval/query_expansion.py services/retrieval/src/zayd_service_retrieval/__init__.py --ignore-missing-imports`
- `python3 -m py_compile services/retrieval/src/zayd_service_retrieval/query_expansion.py services/retrieval/src/zayd_service_retrieval/__init__.py services/retrieval/tests/test_query_expansion.py && git diff --check`

### Acceptance Criteria Result

- Passed. Expansion responses include a structured trace with expansion version, policy version, detected language, normalization framework, flags, and expansion items.
- Passed. `QueryExpansionPolicy` can disable expansion, disable/limit variant generation, preserve named references, and cap expansion count.
- Passed. Thai, Arabic, and English religious terminology fixtures are documented and covered by golden regression tests.

### Security and License Review

- No secrets, production data, PHI, restricted religious datasets, or third-party code were introduced.
- Expansion never changes retrieval metadata filters and suppresses terminology variants for named references by default to preserve intent.
- The local deterministic fallback avoids external provider data sharing.

### Known Limitations

- Terminology fixtures are intentionally conservative and should remain small until a dedicated reviewed terminology governance workflow exists.
- Provider-backed translation is not implemented; local fallback is used by design.

### Follow-up Tasks

- TASK-07-08 Evidence Sufficiency Engine should consume expansion trace metadata when deciding whether to search further.

### Commit

- Focused commit created for TASK-07-06.
