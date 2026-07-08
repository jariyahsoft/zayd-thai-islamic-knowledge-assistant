# TASK-05-04 — Document Parser Framework

## Status

`DONE`

## Model Tier

Tier S

## Related Requirements

- FR-ING-001
- FR-ING-006
- FR-ING-008

## Objective

Define a parser plugin interface and implement baseline parsers for PDF, DOCX, TXT, Markdown, HTML, JSON and CSV where practical.

## Scope

### In Scope

- Define a parser plugin interface and implement baseline parsers for PDF, DOCX, TXT, Markdown, HTML, JSON and CSV where practical.
- Return structured pages, headings, tables and extraction warnings.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-05-03

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

- [x] Parser failures are isolated and retryable.
- [x] Page and section locations are retained.
- [x] Unsupported features produce warnings rather than silent data loss.
- [x] Plugins are selected through an allow-list.

## Required Tests

### Unit and Contract Tests

- Parser contract tests
- Format fixture tests
- Corrupt-file tests
- Plugin allow-list tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/development/parser-plugins.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/common/src/zayd_common/parsing.py` — New parser plugin framework: DocumentParser protocol, ParserRegistry allow-list, PlainTextParser, MarkdownParser, HtmlParser, JsonParser, CsvParser, PdfStubParser, DocxStubParser, ParseResult/ParsedSection/ParseWarning/ParserError types.
- `services/common/src/zayd_common/__init__.py` — Exported all parser types.
- `services/api/src/zayd_service_api/app.py` — Added `POST /documents/{document_version_id}/parse` route, ParserError exception handler, DocumentParseResponse/ParsedSectionResponse/ParseWarningResponse models.
- `services/common/tests/test_parsing.py` — 36 unit tests: parser contract tests (7 parametrized), format fixture tests, corrupt-file tests, plugin allow-list tests, idempotency test, Thai/Arabic content tests.
- `services/api/tests/test_documents_api.py` — Added parse route/OpenAPI assertions and integration tests for parse-after-scan success and parse-blocked-before-scan failure.
- `docs/development/parser-plugins.md` — Parser plugin documentation.
- `tasks/05_ingestion/05-04_document_parser_framework.md` — Updated task status and completion report.

### Commands and Tests Executed

- `uv run pytest services/common/tests/test_parsing.py services/api/tests/test_documents_api.py services/common/tests/test_documents.py services/common/tests/test_storage.py -v` — 65 passed, 1 skipped (MinIO round-trip requires Docker).
- `uv run ruff check` on all task files — All checks passed.
- `uv run mypy services/common/src/zayd_common/parsing.py services/api/src/zayd_service_api/app.py --ignore-missing-imports` — Success: no issues found in 2 source files.

### Acceptance Criteria Result

- ✅ Verified. Parser failures (corrupt input, unsupported format, unexpected exceptions) are isolated as `ParserError` and do not affect other documents. Tests: `test_pdf_stub_rejects_non_pdf`, `test_docx_stub_rejects_non_zip`, `test_json_malformed_raises`, `test_registry_isolates_parser_internal_error`.
- ✅ Verified. `ParsedSection` retains `page`, `heading`, `section_index`, and `content_type`. Tests: `test_markdown_heading_extraction`, `test_csv_with_header_and_rows`.
- ✅ Verified. Stub parsers (PDF, DOCX) return `unsupported_feature` warnings. Empty files return `empty_content` warnings. Invalid UTF-8 returns `encoding` warnings. Tests: `test_pdf_stub_accepts_valid_header`, `test_docx_stub_accepts_valid_header`, `test_plain_text_empty_file_warns`, `test_plain_text_invalid_utf8_warns`.
- ✅ Verified. `ParserRegistry` selects parsers by explicit content-type allow-list and rejects unlisted types with `PARSER_NOT_ALLOWED`. Tests: `test_registry_default_includes_all_formats`, `test_registry_rejects_unlisted_content_type`, `test_registry_custom_allow_list`.

### Security and License Review

- Parsers operate on bytes from object storage and do not expose filesystem paths, bucket names, or credentials in API responses.
- The parse API route requires `parser_eligible: true` (malware scan clean) before parsing.
- No production secrets, restricted religious content, PHI, third-party code, or new dependencies were introduced.
- All parsers are pure Python with no external library dependencies for baseline formats.

### Known Limitations

- PDF and DOCX parsers are stubs that validate structural integrity but do not extract text. Production adapters (PyMuPDF, python-docx) are follow-up integrations.
- The HTML parser uses a simple tag-stripping approach without full DOM parsing.
- Parse results are not yet persisted to the database — downstream tasks will store extracted text and metadata.

### Follow-up Tasks

- Add production PDF parser adapter (PyMuPDF or pdfplumber).
- Add production DOCX parser adapter (python-docx).
- Persist parse results to `DocumentVersion.extracted_text` and metadata.
- Integrate parser into the ingestion pipeline as an automatic post-scan stage.

### Commit

- Pending (task verified, ready for focused commit).
