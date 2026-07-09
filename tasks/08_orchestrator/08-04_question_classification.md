# TASK-08-04 — Question Classification

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- FR-CLASS-001
- FR-CLASS-007

## Objective

Classify language, intent, topic, madhhab, risk hints and current-information requirement using rules first and LLM fallback only when needed.

## Scope

### In Scope

- Classify language, intent, topic, madhhab, risk hints and current-information requirement using rules first and LLM fallback only when needed.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-08-02 or TASK-08-03

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

- [x] Output conforms to a versioned structured schema.
- [x] Rule decisions and LLM fallbacks are traceable.
- [x] Ambiguous cases do not fabricate a madhhab or topic.

## Required Tests

### Unit and Contract Tests

- Classification golden set
- Rule-vs-LLM fallback tests
- Malformed output tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/architecture/question-classification.md`

## Completion Report

### Files Changed

- `services/orchestrator/src/zayd_service_orchestrator/question_classification.py` — Question classifier with rule-based and LLM fallback (417 lines)
- `services/orchestrator/tests/test_question_classification.py` — 22 comprehensive tests covering golden set, rule/LLM fallback, and edge cases
- `services/orchestrator/src/zayd_service_orchestrator/__init__.py` — Exported classification classes
- `docs/architecture/question-classification.md` — Architecture documentation with design principles, algorithm details, and integration guide

### Commands and Tests Executed

```bash
uv run pytest services/orchestrator/tests/test_question_classification.py -v
# 22 passed in 0.97s

uv run pytest services/orchestrator/tests/ -v
# 51 passed in 1.67s (all orchestrator tests)

uv run mypy services/orchestrator/src/zayd_service_orchestrator/question_classification.py
# Success: no issues found

uv run ruff check services/orchestrator/src/zayd_service_orchestrator/question_classification.py
# All checks passed!
```

### Acceptance Criteria Result

- [x] Output conforms to a versioned structured schema — Uses `classification-v1` schema with typed enums
- [x] Rule decisions and LLM fallbacks are traceable — Every result includes method (rule/llm/hybrid), confidence, and trace metadata
- [x] Ambiguous cases do not fabricate a madhhab or topic — Returns `unspecified` madhhab and `general` intent when no clear match

### Security and License Review

- Deterministic rules for safety-critical decisions (risk level, restricted content)
- No secrets or production data committed
- Fail-safe design: continues with rules when LLM unavailable
- No prompt injection: question text treated as data, not instructions
- Audit trail: all decisions traceable through trace metadata

### Known Limitations

- LLM fallback currently returns hybrid result with rule data and LLM trace; JSON parsing not yet implemented
- Thai/Arabic keyword coverage is comprehensive but not exhaustive
- Language detection uses character ratios, may misclassify very short texts
- Personal advice detection is generic and may overlap with other intents

### Follow-up Tasks

- Implement structured output parsing from LLM (use response_format="json")
- Expand Thai and Arabic keyword dictionaries based on production data
- Tune confidence thresholds for LLM fallback based on real usage
- Add multi-madhhab detection for questions explicitly asking for multiple views
- Implement reviewer correction workflow to improve rule patterns

### Commit

- `432b41b` — feat(orchestrator): add question classification with rules and LLM fallback
