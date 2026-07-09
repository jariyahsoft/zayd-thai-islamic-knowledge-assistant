# TASK-08-06 — Answer Orchestration Workflow

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- FR-ANS-001
- FR-ANS-008
- SRS §6 High-level Architecture

## Objective

Implement a traceable state machine: classify, retrieve, evaluate sufficiency, expand/retrieve, generate, verify, revise/abstain and return.

## Scope

### In Scope

- Implement a traceable state machine: classify, retrieve, evaluate sufficiency, expand/retrieve, generate, verify, revise/abstain and return.
- Add timeout, cancellation and idempotency behavior.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-07-08
- TASK-08-05

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

- [x] Every step records status and safe trace metadata.
- [x] Retries do not create duplicate persisted answers.
- [x] Cancellation stops provider work where supported.
- [x] Insufficient/conflicting evidence follows policy.

## Required Tests

### Unit and Contract Tests

- State-machine unit tests
- Timeout/cancellation tests
- End-to-end orchestration fixtures
- Idempotency tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/architecture/answer-orchestrator.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/orchestrator/src/zayd_service_orchestrator/answer_orchestration.py`
- `services/orchestrator/src/zayd_service_orchestrator/__init__.py`
- `services/orchestrator/tests/test_answer_orchestration.py`
- `docs/architecture/answer-orchestrator.md`
- `tasks/08_orchestrator/08-06_answer_orchestration_workflow.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

```bash
uv run pytest services/orchestrator/tests/test_answer_orchestration.py -q
# 9 passed

uv run pytest services/orchestrator/tests/test_answer_orchestration.py services/orchestrator/tests/test_risk_policy_engine.py services/orchestrator/tests/test_orchestrator_imports.py -q
# 36 passed

uv run pytest services/orchestrator/tests -q
# 86 passed

uv run ruff check services/orchestrator/src/zayd_service_orchestrator/answer_orchestration.py services/orchestrator/src/zayd_service_orchestrator/__init__.py services/orchestrator/tests/test_answer_orchestration.py
# All checks passed

uv run ruff format --check services/orchestrator/src/zayd_service_orchestrator/answer_orchestration.py services/orchestrator/src/zayd_service_orchestrator/__init__.py services/orchestrator/tests/test_answer_orchestration.py
# 3 files already formatted

uv run mypy services/orchestrator/src/zayd_service_orchestrator/answer_orchestration.py services/orchestrator/src/zayd_service_orchestrator/__init__.py services/orchestrator/tests/test_answer_orchestration.py
# Success

git diff --check
# Passed
```

### Acceptance Criteria Result

- [x] Every step records status and safe trace metadata.
- [x] Retries do not create duplicate persisted answers.
- [x] Cancellation stops provider work where supported.
- [x] Insufficient/conflicting evidence follows policy.

### Security and License Review

The state machine applies deterministic risk policy and evidence sufficiency
before generation, returns restricted/escalated/abstained responses without
provider generation where required, and verifies draft citations before return.
Safe step traces omit raw questions, prompts, message payloads, answer text,
hidden chain-of-thought, secrets, tokens, credentials, production payloads, and
PHI. No restricted datasets, production data, or third-party code were added.

### Known Limitations

- Citation verification is a local deterministic allowed-citation check until
  TASK-08-07 and TASK-08-08 add the citation registry and claim-support verifier.
- The included in-memory idempotency store is for local/test composition; durable
  answer persistence belongs to later API and conversation-history tasks.
- The template generator is deterministic offline behavior; production model
  generation should use `LLMAnswerGenerator` through approved provider config.

### Follow-up Tasks

- TASK-08-07 should add citation registry persistence and canonical citation IDs.
- TASK-08-08 should replace local draft verification with full citation and
  claim-support verification.
- TASK-08-09 should move prompt versions into managed prompt configuration.

### Commit

- Pending focused commit.
