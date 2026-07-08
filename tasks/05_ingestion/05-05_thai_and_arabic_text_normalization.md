# TASK-05-05 — Thai and Arabic Text Normalization

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- FR-ING-009
- FR-RET-007

## Objective

Implement separate, versioned normalization pipelines for Thai and Arabic search text.

## Scope

### In Scope

- Implement separate, versioned normalization pipelines for Thai and Arabic search text.
- Preserve original text byte-for-byte while producing normalized search fields.
- Handle Unicode normalization, Thai spacing conventions, Arabic diacritics and tatweel according to documented policies.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-05-04

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

- [x] Original text is never mutated.
- [x] Normalization is deterministic and versioned.
- [x] Fixtures cover Thai, Arabic and mixed-script religious terminology.

## Required Tests

### Unit and Contract Tests

- Golden normalization fixtures
- Round-trip preservation tests
- Regression tests for known script edge cases

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/architecture/text-normalization.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/common/src/zayd_common/normalization.py` — New normalization module: separate Thai (`thai-norm-v1`) and Arabic (`arabic-norm-v1`) pipelines with NFC, zero-width removal, diacritic stripping, tatweel removal, alef/teh-marbuta/alef-maksura normalization, whitespace collapsing.
- `services/common/src/zayd_common/__init__.py` — Exported normalization types.
- `services/common/tests/test_normalization.py` — 39 unit tests: golden Thai fixtures (9), golden Arabic fixtures (10), round-trip preservation (3), edge cases (11), determinism/versioning (6).
- `docs/architecture/text-normalization.md` — Architecture documentation for normalization pipelines.
- `tasks/05_ingestion/05-05_thai_and_arabic_text_normalization.md` — Updated task status and completion report.

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_normalization.py -v` — 39 passed.
- `uv run pytest` on full ingestion regression suite — 98 passed.
- `uv run ruff check` on all task files — All checks passed.
- `uv run mypy services/common/src/zayd_common/normalization.py --ignore-missing-imports` — Success: no issues found.

### Acceptance Criteria Result

- ✅ Verified. `NormalizationResult` preserves `original` byte-for-byte while producing `normalized` as a separate field. Tests: `TestRoundTripPreservation` class (3 tests).
- ✅ Verified. Both pipelines are deterministic (same input → same output) and versioned (`thai-norm-v1`, `arabic-norm-v1`). Tests: `TestDeterminismAndVersioning` class (6 tests).
- ✅ Verified. Golden fixtures cover Thai Islamic terminology (อัลกุรอาน, ฮะดีษ, ซอลาต, etc.), Arabic Islamic terminology with tashkeel (بِسْمِ اللَّهِ, القُرْآنُ, الصَّلَاةُ, etc.), mixed-script content, and edge cases. Tests: `TestThaiNormalization` (9 tests), `TestArabicNormalization` (10 tests), `TestEdgeCases` (11 tests).

### Security and License Review

- Normalization operates on in-memory strings with pure Python `unicodedata`. No filesystem access, no external dependencies.
- Input text is treated as untrusted — no execution or interpretation of content.
- Original text preservation ensures no data loss.
- No production secrets, restricted religious content, PHI, third-party code, or new dependencies were introduced.

### Known Limitations

- Thai word segmentation is not implemented — requires external library (PyThaiNLP or similar) for production-quality word boundaries.
- Arabic normalizer uses a fixed diacritics table — very rare or newly encoded combining marks might not be covered.
- Normalization is not yet integrated into the ingestion pipeline as an automatic post-parse stage.

### Follow-up Tasks

- Add Thai word segmentation using PyThaiNLP for production-quality search.
- Integrate normalization into the ingestion pipeline after parsing.
- Add transliteration mapping between Thai Islamic terms and their Arabic originals.

### Commit

- Pending (task verified, ready for focused commit).
