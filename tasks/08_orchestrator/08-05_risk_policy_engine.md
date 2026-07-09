# TASK-08-05 — Risk Policy Engine

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- FR-SAFE-001
- FR-SAFE-007

## Objective

Implement deterministic risk policies for divorce, inheritance, takfir, complex personal rulings, health danger and other restricted categories.

## Scope

### In Scope

- Implement deterministic risk policies for divorce, inheritance, takfir, complex personal rulings, health danger and other restricted categories.
- Version policy decisions and escalation messages.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-08-04

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

- [x] High-risk and restricted cases route according to policy.
- [x] Model output cannot downgrade deterministic restrictions.
- [x] Policy changes require approval and regression tests.

## Required Tests

### Unit and Contract Tests

- Risk decision-table tests
- Adversarial phrasing tests
- Policy-version trace tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/governance/answer-safety-policy.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/orchestrator/src/zayd_service_orchestrator/risk_policy_engine.py`
- `services/orchestrator/src/zayd_service_orchestrator/__init__.py`
- `services/orchestrator/tests/test_risk_policy_engine.py`
- `docs/governance/answer-safety-policy.md`
- `tasks/08_orchestrator/08-05_risk_policy_engine.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

```bash
uv run pytest services/orchestrator/tests/test_risk_policy_engine.py -q
# 26 passed

uv run pytest services/orchestrator/tests -q
# 77 passed

uv run ruff check services/orchestrator/src/zayd_service_orchestrator/risk_policy_engine.py services/orchestrator/src/zayd_service_orchestrator/__init__.py services/orchestrator/tests/test_risk_policy_engine.py
# All checks passed

uv run ruff format --check services/orchestrator/src/zayd_service_orchestrator/risk_policy_engine.py services/orchestrator/src/zayd_service_orchestrator/__init__.py services/orchestrator/tests/test_risk_policy_engine.py
# 3 files already formatted

uv run mypy services/orchestrator/src/zayd_service_orchestrator/risk_policy_engine.py services/orchestrator/tests/test_risk_policy_engine.py
# Success

uv run mypy services/orchestrator/src/zayd_service_orchestrator
# Success

git diff --check
# Passed
```

Note: full orchestrator lint and format checks surfaced pre-existing issues in
`test_question_classification.py`, `question_classification.py`, and
`test_provider_sdk.py`; focused TASK-08-05 files pass lint and format.

### Acceptance Criteria Result

- [x] High-risk and restricted cases route according to policy.
- [x] Model output cannot downgrade deterministic restrictions.
- [x] Policy changes require approval and regression tests.

### Security and License Review

The engine applies deterministic policy before model judgement, fails closed for
empty supplied question text and draft policy activation, and records only safe
rule IDs, classification metadata, actor, policy version/status, and matched
signal source names. It does not persist raw question text, hidden
chain-of-thought, provider secrets, production data, PHI, restricted datasets,
or third-party code.

### Known Limitations

- Scholar, medical, legal, and crisis-support routing is represented as
  structured `escalation_target` metadata; downstream workflow and user-facing
  routing are future tasks.
- Keyword rules are intentionally conservative and should be expanded only
  through reviewed policy versions and regression tests.

### Follow-up Tasks

- TASK-08-06 should consume `PolicyDecision` to enforce answer workflow routing.
- Future reviewer/admin workflows should expose approved policy-version changes.

### Commit

- Pending focused commit.
