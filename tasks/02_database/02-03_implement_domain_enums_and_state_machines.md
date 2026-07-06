# TASK-02-03 — Implement Domain Enums and State Machines

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- SRS §24 Document State Machine
- FR-REV-007
- FR-RET-014

## Objective

Implement typed enums for document status, review decision, storage permission, evidence status, risk level, incident severity and provider status.

## Scope

### In Scope

- Implement typed enums for document status, review decision, storage permission, evidence status, risk level, incident severity and provider status.
- Implement explicit state-transition guards for documents, reviews and incidents.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-02-02

## Expected Files

- Implementation files under the relevant `02_database` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Use PostgreSQL-compatible types and explicit constraints.
- Keep domain logic outside migration files.
- Design for versioning and auditability.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Protect referential integrity and sensitive fields.

## Acceptance Criteria

- [ ] Invalid transitions are rejected with stable error codes.
- [ ] Only PUBLISHED documents are eligible for production retrieval.
- [ ] Every transition records actor, timestamp and reason where required.
- [ ] Unit tests cover allowed and forbidden transitions.

## Required Tests

### Unit and Contract Tests

- Enum serialization tests
- State transition table tests
- Concurrency test for conflicting transitions

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/architecture/state-machines.md`

## Completion Report

### Files Changed

#### Python Implementation
- `services/common/src/zayd_common/enums.py` - Created all domain enums using Python 3.12 StrEnum
- `services/common/src/zayd_common/exceptions.py` - Created state transition exception hierarchy with stable error codes
- `services/common/src/zayd_common/state_machines.py` - Created state machine guards with PEP 695 type parameters
- `services/common/src/zayd_common/retrievability.py` - Created production retrieval eligibility helpers
- `services/common/src/zayd_common/__init__.py` - Updated exports for all new modules

#### TypeScript Implementation
- `packages/contracts/src/enums.ts` - Created TypeScript string enums matching database values
- `packages/contracts/src/state-machines.ts` - Created client-side transition validation
- `packages/contracts/src/retrievability.ts` - Created TypeScript retrievability helpers
- `packages/contracts/src/index.ts` - Updated exports for all new modules

#### Tests
- `services/common/tests/test_enums.py` - Enum serialization and Pydantic integration tests
- `services/common/tests/test_state_machines.py` - Comprehensive state transition validation tests (35 test cases)
- `services/common/tests/test_retrievability.py` - Production retrieval eligibility tests
- `services/common/tests/test_state_machines_concurrency.py` - Optimistic locking and race condition tests
- `packages/contracts/src/enums.test.ts` - TypeScript enum value tests
- `packages/contracts/src/state-machines.test.ts` - TypeScript transition validation tests
- `packages/contracts/src/retrievability.test.ts` - TypeScript retrievability tests

#### Documentation
- `docs/architecture/state-machines.md` - Comprehensive state machine documentation with Mermaid diagrams

### Commands and Tests Executed

```bash
# Python tests (52 tests passed)
uv run pytest

# Database tests (13 tests passed)
uv run pytest database/tests

# TypeScript tests (11 tests passed in contracts package)
npm run test

# Type checking
npm run typecheck  # Passed
uv run mypy .      # Passed (6 pre-existing errors in settings.py only)

# Code formatting and linting
uv run ruff check --fix .  # Auto-fixed 42 issues
uv run ruff format .       # Formatted all files
uv run ruff check .        # 1 pre-existing error in settings.py only
```

### Acceptance Criteria Result

- [x] Invalid transitions are rejected with stable error codes (`DOCUMENT_INVALID_TRANSITION`, `REVIEW_TASK_INVALID_TRANSITION`, `INCIDENT_INVALID_TRANSITION`)
- [x] Only PUBLISHED documents are eligible for production retrieval (enforced by `is_document_retrievable()`)
- [x] Every transition records actor, timestamp and reason where required (enforced by `TransitionMetadata` validation)
- [x] Unit tests cover allowed and forbidden transitions (35 parameterized test cases in `test_state_machines.py`)
- [x] Enum serialization tests verify Pydantic and JSON compatibility
- [x] State transition table tests verify all valid/invalid paths
- [x] Concurrency test simulates optimistic locking with 10 racing threads

### Security and License Review

- No secrets, production data, or restricted religious content committed
- All state transitions require authenticated actor_id in metadata
- Sensitive transitions (published, suspended, rejected) require non-empty reason field
- Production retrieval limited to published+frozen documents only
- Optimistic locking via row_version prevents concurrent update conflicts
- All exceptions include stable error codes for client error handling

### Known Limitations

- Evidence status enum (`EvidenceStatus`) defined but not yet integrated into database schema (will be added in Phase 6/7 retrieval tasks)
- Concurrency tests simulate optimistic locking but do not test against actual PostgreSQL row_version constraints (integration tests will cover this in service layer)
- State machine guards validate transitions but do not enforce database-level CHECK constraints (database migration already enforces enum values)

### Follow-up Tasks

- TASK-05-XX: Integrate document status transitions into ingestion pipeline
- TASK-06-XX: Integrate evidence status into retrieval sufficiency engine
- TASK-10-XX: Integrate review task status into reviewer dashboard workflows
- TASK-11-XX: Integrate incident status into incident management UI

### Commit

Ready to commit. Suggest commit message:

```
feat(database): implement domain enums and state transition guards

- Add typed enums for DocumentStatus, ReviewDecision, PermissionState,
  EvidenceStatus, RiskLevel, IncidentSeverity, IncidentStatus,
  ReviewTaskStatus, and ProviderStatus in Python and TypeScript
- Implement state machines with explicit transition rules for documents,
  review tasks, and incidents
- Add metadata validation requiring actor, timestamp, and reason for
  sensitive transitions (published, suspended, rejected)
- Add retrievability helpers enforcing only PUBLISHED+frozen documents
  for production retrieval
- Add comprehensive test coverage (52 Python tests, 11 TypeScript tests)
- Add concurrency conflict simulation for optimistic locking
- Document state machines with Mermaid diagrams in
  docs/architecture/state-machines.md

Resolves: TASK-02-03

Co-Authored-By: Claude <noreply@anthropic.com>
```
