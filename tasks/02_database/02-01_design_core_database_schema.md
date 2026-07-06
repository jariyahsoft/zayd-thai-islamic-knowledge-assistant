# TASK-02-01 — Design Core Database Schema

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- SRS §23 Data Model
- SRS §24 Document State Machine
- FR-RET-009
- FR-CIT-002

## Objective

Design relational entities for identity, sources, licenses, documents, reviews, conversations, retrieval, citations, feedback, incidents, providers, prompts, policies and evaluations.

## Scope

### In Scope

- Design relational entities for identity, sources, licenses, documents, reviews, conversations, retrieval, citations, feedback, incidents, providers, prompts, policies and evaluations.
- Define primary keys, foreign keys, uniqueness rules, indexes, soft-delete rules, timestamps and version fields.
- Document data ownership, retention and boundaries between source text, normalized text, chunks and embeddings.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- EPIC-01 complete

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

- [ ] Schema covers every core entity from the SRS.
- [ ] Foreign-key and uniqueness constraints prevent orphaned or ambiguous records.
- [ ] License records and document content remain separate entities.
- [ ] Embedding records always reference a published document version and chunk.
- [ ] Schema review identifies privacy, security and migration risks.

## Required Tests

### Unit and Contract Tests

- Schema consistency review
- ERD validation
- Index/query-plan review for primary access patterns

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/architecture/database.md`
- `database/schemas/core-domain.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `database/schemas/core-domain.schema.json` — machine-readable core domain schema design covering SRS §23 entities, fields, constraints, indexes, invariants, risks and access patterns.
- `database/schemas/core-domain.md` — human-readable schema design, ERD, ownership boundaries, content/license separation, retrieval invariants and migration risks.
- `docs/architecture/database.md` — database architecture, lifecycle, state/versioning model, retrieval boundary, sensitive data handling and migration guidance.
- `database/tests/test_core_domain_schema.py` — schema consistency, ERD reference, index/query-plan, embedding invariant and security-risk validation tests.
- `tasks/00_task_index.md`, `tasks/02_database/02-01_design_core_database_schema.md`, `tasks-update.md` — task status and completion records.

### Commands and Tests Executed

- `python3 -m json.tool database/schemas/core-domain.schema.json >/dev/null` — passed.
- `uv run pytest database/tests/test_core_domain_schema.py` — passed, 9 tests.
- `uv run pytest` — passed, 23 tests including services and database schema tests during verification before reverting the global `testpaths` change to keep the commit focused; focused schema tests remain runnable directly.
- `uv run ruff check database/tests/test_core_domain_schema.py` — passed.
- `uv run ruff format --check database/tests/test_core_domain_schema.py` — passed.
- `uv run mypy database/tests/test_core_domain_schema.py` — passed.
- `corepack pnpm test` — passed, all TypeScript workspace tests.
- Secret marker scan against TASK-02-01 files — passed; no Telegram/token markers found.

### Acceptance Criteria Result

- [x] Schema covers every core entity from the SRS.
- [x] Foreign-key and uniqueness constraints prevent orphaned or ambiguous records.
- [x] License records and document content remain separate entities.
- [x] Embedding records always reference a published document version and chunk through documented invariants and validation tests.
- [x] Schema review identifies privacy, security and migration risks.

### Security and License Review

- No secrets, credentials, production data or restricted religious content were introduced.
- Schema separates source/license metadata from document text, normalized chunks and embedding artifacts.
- Provider rows store `secret_ref` only and mark provider secret fields sensitive.
- Conversation, message, retrieval query, answer, feedback, incident and document text fields are marked sensitive in the schema design.
- Audit logs store summaries and trace metadata, not full passwords/tokens/private conversation bodies.
- License-critical states fail closed by design; embeddings require explicit embedding permission and published content invariants.
- No third-party code or new dependencies were added.

### Known Limitations

- This task produces design artifacts and validation tests, not executable SQL migrations; migrations are deferred to TASK-02-02.
- Cross-row invariants such as active embedding requiring published chunks and valid licenses must be enforced in TASK-02-02 via triggers/service transactions where PostgreSQL CHECK constraints cannot reference other rows.
- Runtime RBAC, audit hooks and state-machine enforcement are designed here but implemented in later API/domain tasks.
- pgvector dimensions are model-specific and must be finalized during migration/model configuration implementation.

### Follow-up Tasks

- TASK-02-02 — Create Initial Database Migration.
- TASK-02-03 — Implement Domain Enums and State Machines.
- TASK-02-04 — Add Repository and Unit-of-Work Layer.
- TASK-04-03 — License Policy Engine.
- TASK-07-04 — Vector Search with pgvector.

### Commit

- Focused TASK-02-01 commit created during finalization with message `feat(database): design core domain schema`.
