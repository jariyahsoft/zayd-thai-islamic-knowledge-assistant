# TASK-08-07 — Citation Registry

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- FR-CIT-001
- FR-CIT-010

## Objective

Create canonical citation records linked to document version and chunk/reference.

## Scope

### In Scope

- Create canonical citation records linked to document version and chunk/reference.
- Support Quran, hadith, book and generic document citation metadata plus invalidation.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-06-04

## Expected Files

- Implementation files under the relevant `08_orchestrator` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Use typed provider contracts and structured outputs.
- Store only safe traces; never persist hidden chain-of-thought.
- Apply deterministic policy and verification before model judgement.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Prevent prompt injection and citation fabrication.

## Acceptance Criteria

- [x] Citation IDs are stable and unique.
- [x] LLM-visible citation tokens map only to registered records.
- [x] Invalidation preserves history and downstream impact.

## Required Tests

### Unit and Contract Tests

- Canonical ID tests
- Citation type schema tests
- Invalidation propagation tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/architecture/citation-registry.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/orchestrator/src/zayd_service_orchestrator/citation_registry.py`
- `services/orchestrator/src/zayd_service_orchestrator/__init__.py`
- `services/orchestrator/tests/test_citation_registry.py`
- `docs/architecture/citation-registry.md`
- `tasks/08_orchestrator/08-07_citation_registry.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `uv run pytest services/orchestrator/tests/test_citation_registry.py -q` — passed, 7 tests.
- `uv run pytest services/orchestrator/tests/test_citation_registry.py services/orchestrator/tests/test_answer_orchestration.py services/orchestrator/tests/test_orchestrator_imports.py -q` — passed, 17 tests.
- `uv run pytest services/orchestrator/tests -q` — passed, 93 tests.
- `uv run ruff check services/orchestrator/src/zayd_service_orchestrator/citation_registry.py services/orchestrator/src/zayd_service_orchestrator/__init__.py services/orchestrator/tests/test_citation_registry.py` — passed.
- `uv run ruff format --check services/orchestrator/src/zayd_service_orchestrator/citation_registry.py services/orchestrator/src/zayd_service_orchestrator/__init__.py services/orchestrator/tests/test_citation_registry.py` — passed.
- `uv run mypy services/orchestrator/src/zayd_service_orchestrator/citation_registry.py services/orchestrator/src/zayd_service_orchestrator/__init__.py services/orchestrator/tests/test_citation_registry.py` — passed.
- `git diff --check` — passed.

### Acceptance Criteria Result

- Passed. Citation IDs are deterministic UUIDv5 values scoped to document version and canonical reference, with database uniqueness and collision checks.
- Passed. LLM-visible `CIT-<uuid>` tokens are issued and resolved only through active registered citation rows.
- Passed. Citation invalidation keeps the original row, marks it inactive, annotates retrieval results, invalidates downstream answers, and writes audit impact counts.

### Security and License Review

- No secrets, production data, PHI, hidden chain-of-thought, restricted datasets, or third-party code were introduced.
- Registry traces and audit summaries store only safe IDs, status, metadata keys, reason codes, version data, and impact counts.
- The implementation prevents prompt-level citation fabrication by requiring token resolution against registered active rows.

### Known Limitations

- The registry records canonical citation identity and invalidation. Claim-level support verification remains TASK-08-08.
- RBAC enforcement is expected at the API/service boundary that invokes this registry; this task adds actor-aware audit records but no HTTP endpoint.

### Follow-up Tasks

- TASK-08-08 Citation Verification Engine.

### Commit

- Focused commit `feat(orchestrator): add citation registry`.
