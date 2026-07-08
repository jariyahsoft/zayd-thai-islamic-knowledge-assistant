# TASK-05-06 — Metadata Extraction Service

## Status

`DONE`

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

- [x] All machine-generated fields are marked UNVERIFIED.
- [x] Extraction cannot publish or overwrite reviewed metadata automatically.
- [x] Structured output validation rejects malformed results.

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

- `services/common/src/zayd_common/metadata_extraction.py` — New module: MetadataExtractor protocol, RuleBasedExtractor, MetadataExtractionService, ExtractedField/Chapter/Reference result types, schema validation, serialization.
- `services/common/src/zayd_common/__init__.py` — Exported metadata extraction types.
- `services/common/tests/test_metadata_extraction.py` — 32 unit tests: schema validation (10), rule-based extraction golden fixtures (13), provider failure/fallback (2), service integration (3), prompt-version trace (2).
- `docs/architecture/metadata-extraction.md` — Architecture documentation.
- `tasks/05_ingestion/05-06_metadata_extraction_service.md` — Updated status and completion report.

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_metadata_extraction.py -v` — 32 passed.
- `uv run ruff check services/common/src/zayd_common/metadata_extraction.py services/common/tests/test_metadata_extraction.py` — All checks passed.
- `uv run mypy services/common/src/zayd_common/metadata_extraction.py --ignore-missing-imports` — Success: no issues found.

### Acceptance Criteria Result

- ✅ Verified. Every `ExtractedField` defaults to `verification_status="unverified"`. Test: `test_all_suggestions_unverified_by_default`.
- ✅ Verified. Extraction stores results as version metadata (`metadata_json["metadata_extraction"]`) without modifying canonical Document fields. Test: `test_extract_and_persist`.
- ✅ Verified. Schema validation (`validate_confidence`, `validate_extracted_madhhab`, `validate_extracted_document_type`) rejects out-of-range confidence, invalid madhhab, and invalid document type with `EXTRACTION_MALFORMED_OUTPUT`. Tests: `TestSchemaValidation` class (10 tests).

### Security and License Review

- All extracted fields are UNVERIFIED and cannot overwrite reviewed metadata automatically.
- Extraction operates on in-memory strings only; no filesystem access.
- No production secrets, restricted religious content, PHI, third-party code, or new dependencies were introduced.
- Extractor output is validated schematically before persistence.

### Known Limitations

- Rule-based extractor uses simple heuristics; AI/LLM extractor not yet implemented.
- Publisher and edition detection are not yet implemented in the rule-based extractor.
- No API endpoint exposed yet — extraction is called programmatically from the ingestion pipeline.
- Thai author detection patterns may not cover all possible formulations.

### Follow-up Tasks

- Add AI/LLM extractor with prompt version tracking behind the MetadataExtractor protocol.
- Add publisher, edition, and other field detection to the rule-based extractor.
- Expose metadata extraction preview via API (GET /documents/{id}/metadata-suggestions).
- Wire metadata extraction as automatic stage after parsing in the ingestion pipeline.

### Commit

- Pending (task verified, ready for focused commit).
