# TASK-02-01 — Design Core Database Schema

## Status

`TODO`

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

- Pending

### Commands and Tests Executed

- Pending

### Acceptance Criteria Result

- Pending

### Security and License Review

- Pending

### Known Limitations

- Pending

### Follow-up Tasks

- Pending

### Commit

- Pending
