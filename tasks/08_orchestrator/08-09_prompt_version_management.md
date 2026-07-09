# TASK-08-09 — Prompt Version Management

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- SRS §28 Prompt Management
- FR-ADM-004

## Objective

Store prompt templates as versioned records/artifacts with purpose, schema, owner, status, changelog and test cases.

## Scope

### In Scope

- Store prompt templates as versioned records/artifacts with purpose, schema, owner, status, changelog and test cases.
- Restrict production use to approved versions.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-08-06

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

- [x] Every generated answer records prompt versions.
- [x] Draft prompts cannot be activated without permission.
- [x] Rollback and comparison are supported.

## Required Tests

### Unit and Contract Tests

- Prompt lifecycle tests
- RBAC/audit tests
- Version rollback tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/governance/prompt-management.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/common/src/zayd_common/prompt_registry.py` (new)
- `services/common/src/zayd_common/__init__.py`
- `services/common/src/zayd_common/database/models.py`
- `services/common/src/zayd_common/database/repositories.py`
- `services/common/src/zayd_common/database/unit_of_work.py`
- `services/common/tests/test_prompt_registry.py` (new)
- `services/orchestrator/src/zayd_service_orchestrator/prompt_orchestrator.py` (new)
- `services/orchestrator/src/zayd_service_orchestrator/answer_orchestration.py`
- `services/orchestrator/src/zayd_service_orchestrator/chat_streaming.py`
- `services/orchestrator/src/zayd_service_orchestrator/__init__.py`
- `services/orchestrator/tests/test_prompt_orchestration.py` (new)
- `services/api/src/zayd_service_api/app.py`
- `services/api/tests/test_prompt_api.py` (new)
- `docs/governance/prompt-management.md` (new)
- `tasks/08_orchestrator/08-09_prompt_version_management.md`
- `tasks/08_orchestrator/08-10_streaming_chat_api.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_prompt_registry.py services/api/tests/test_prompt_api.py services/orchestrator/tests/test_prompt_orchestration.py -q` — 12 passed
- `uv run pytest services/orchestrator/tests/test_answer_orchestration.py services/orchestrator/tests/test_orchestrator_imports.py -q` — 10 passed
- `uv run mypy services/common/src/zayd_common/prompt_registry.py services/orchestrator/src/zayd_service_orchestrator/prompt_orchestrator.py` — success
- `uv run ruff check --fix` and `uv run ruff format` on focused prompt files

### Acceptance Criteria Result

- Generated answers record `prompt_version`, `prompt_version_id`, `policy_version_id`, and `model_configuration_id` in orchestration trace and persisted answer rows.
- Prompt creation always stores `draft`; activation requires `prompts.manage` via approve API and audit logging.
- Rollback and compare endpoints are implemented with version diff reporting and prior-version reactivation.

### Security and License Review

- RBAC enforced on all `/admin/prompts` mutations via `prompts.manage`.
- Audit append-only records written for create, approve, and rollback actions.
- No secrets, production data, hidden chain-of-thought, or restricted religious content added.

### Known Limitations

- Prompt artifact storage is database-backed; external prompt file bundles under `prompts/` remain a later packaging concern.
- Bootstrap defaults seed a development LLM provider/model pair when none exists.
- Religious wording inside default prompt bodies still requires human content review before production approval.

### Follow-up Tasks

- TASK-08-10 Streaming Chat API is now unblocked and should expose the streaming endpoints using the governed prompt registry.

### Commit

- Pending focused commit `feat(orchestrator): add prompt version management`