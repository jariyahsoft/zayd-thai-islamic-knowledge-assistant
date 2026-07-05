# TASK-05-06 — Metadata Extraction Service

## Status

`TODO`

## Model Tier

Tier A

## Related Requirements

- FR-ING-010
- FR-ING-011
- SRS §28 Prompt Management

## Objective

Use configurable AI/rule extractors to suggest title, author, translator, chapter, madhhab, document type and references.

## Scope

### In Scope

- Use configurable AI/rule extractors to suggest title, author, translator, chapter, madhhab, document type and references.
- Store extractor model, prompt version and confidence.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-05-05

## Expected Files

- Implementation files under the relevant `05_ingestion` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Pipeline stages must be idempotent and retryable.
- Preserve original files/text and store derived data separately.
- Use background jobs for expensive processing.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Treat uploaded files and extracted content as untrusted.

## Acceptance Criteria

- [ ] All machine-generated fields are marked UNVERIFIED.
- [ ] Extraction cannot publish or overwrite reviewed metadata automatically.
- [ ] Structured output validation rejects malformed results.

## Required Tests

### Unit and Contract Tests

- Schema validation tests
- Provider failure/fallback tests
- Prompt-version trace tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/architecture/metadata-extraction.md`

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
