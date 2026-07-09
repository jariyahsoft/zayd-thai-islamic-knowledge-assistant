# TASK-08-08 — Citation Verification Engine

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- FR-CIT-003
- FR-CIT-004
- FR-ANS-008

## Objective

Verify citation existence, reference correctness, quoted-text fidelity, claim support and madhhab consistency using deterministic checks before optional model evaluation.

## Scope

### In Scope

- Verify citation existence, reference correctness, quoted-text fidelity, claim support and madhhab consistency using deterministic checks before optional model evaluation.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-08-06
- TASK-08-07

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

- [x] Failed verification triggers revision or abstention.
- [x] Every cited claim has a machine-readable verification result.
- [x] Verifier cannot retrieve unpublished or invalidated evidence as valid.

## Required Tests

### Unit and Contract Tests

- Quote/reference exactness tests
- Claim-support benchmark fixtures
- Invalidated citation tests
- Revision path E2E

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/architecture/citation-verification.md`

## Completion Report

### Files Changed

- `services/orchestrator/src/zayd_service_orchestrator/citation_verification.py` (new)
- `services/orchestrator/src/zayd_service_orchestrator/__init__.py`
- `services/orchestrator/tests/test_citation_verification.py` (new)
- `docs/architecture/citation-verification.md` (new)
- `docs/architecture/answer-orchestrator.md`
- `docs/architecture/citation-registry.md`
- `tasks/08_orchestrator/08-08_citation_verification_engine.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `uv run pytest services/orchestrator/tests/test_citation_verification.py -q` — passed, 14 tests.
- `uv run pytest services/orchestrator/tests/test_citation_verification.py services/orchestrator/tests/test_citation_registry.py services/orchestrator/tests/test_answer_orchestration.py services/orchestrator/tests/test_orchestrator_imports.py -q` — passed, 31 tests.
- `uv run pytest services/orchestrator/tests -q` — passed, 107 tests.
- `uv run ruff check services/orchestrator/src/zayd_service_orchestrator/citation_verification.py services/orchestrator/src/zayd_service_orchestrator/__init__.py services/orchestrator/tests/test_citation_verification.py` — passed.
- `uv run ruff format --check ...` — passed.
- `uv run mypy services/orchestrator/src/zayd_service_orchestrator/citation_verification.py services/orchestrator/tests/test_citation_verification.py` — passed.
- `git diff --check` — passed.

### Acceptance Criteria Result

- Passed. Failed citation verification triggers orchestrator revision, then abstention when unrecovered (`test_revision_path_recovers_after_failed_verification`, `test_failed_verification_abstains_when_unrecovered`).
- Passed. Every claim result includes machine-readable status, reason codes, check outcomes, and claim text hash.
- Passed. Unpublished and invalidated citations fail closed with `CITATION_NOT_PUBLISHED` / `CITATION_INACTIVE` and cannot be treated as valid support.

### Security and License Review

- No secrets, production data, PHI, hidden chain-of-thought, restricted datasets, or third-party code were introduced.
- Allowed-token, registry existence, active status, and publication checks prevent citation fabrication and unpublished evidence use.
- Traces store claim hashes, IDs, tokens, scores, and reason codes rather than provider secrets or hidden reasoning.

### Known Limitations

- Claim support is deterministic lexical/n-gram overlap, not full semantic entailment.
- Production answer composition must supply citation token/content metadata or call `load_evidence_packs()`; lightweight fixtures still use the allowed-token fallback.
- Prompt version management and streaming chat remain later tasks.

### Follow-up Tasks

- TASK-08-09 Prompt Version Management (READY; depends only on TASK-08-06).
- TASK-08-10 Streaming Chat API (blocked until TASK-08-08 and TASK-08-09 are both complete; 08-08 now complete).

### Commit

- Focused commit `feat(orchestrator): add citation verification engine`.
