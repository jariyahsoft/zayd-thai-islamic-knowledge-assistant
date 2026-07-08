# Document Parser Plugins

## Overview

Zayd uses a **parser plugin framework** to extract structured content from uploaded documents. Parsers operate on raw bytes after malware scanning and return structured `ParseResult` objects that retain page/section locations and extraction warnings.

## Architecture

```
Upload → Quarantine → Malware Scan → Parser (this stage) → Normalization → Metadata Extraction
```

### Allow-List Selection

Parsers are selected through an **explicit allow-list** (`ParserRegistry`). There is no dynamic plugin loading. To add a new parser:

1. Define a class that satisfies the `DocumentParser` protocol.
2. Add an instance to `_DEFAULT_PARSERS` in `services/common/src/zayd_common/parsing.py`.
3. Add tests for the new format.

### Key Design Principles

- **Failures are isolated and retryable.** A corrupt input raises `ParserError` without affecting other documents.
- **Page and section locations are retained.** Each `ParsedSection` includes `page`, `heading`, and `section_index`.
- **Unsupported features produce warnings, not silent data loss.** Stub parsers (PDF, DOCX) return `ParseWarning` items with category `unsupported_feature`.
- **Original files are preserved.** Parsers operate on a copy from object storage; the original is never modified.

## Supported Formats

| Content Type | Parser | Status |
|---|---|---|
| `text/plain` | `PlainTextParser` | Full extraction |
| `text/markdown` | `MarkdownParser` | Full extraction with heading recognition |
| `text/html` | `HtmlParser` | Tag stripping and text extraction |
| `application/json` | `JsonParser` | Structure validation and key-value extraction |
| `text/csv` | `CsvParser` | Header and row extraction with column metadata |
| `application/pdf` | `PdfStubParser` | Header validation only (stub) |
| `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | `DocxStubParser` | Archive validation only (stub) |

## Parser Protocol

Every parser must satisfy the `DocumentParser` protocol:

```python
class DocumentParser(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    @property
    def supported_content_types(self) -> frozenset[str]: ...

    def parse(
        self,
        *,
        content: bytes,
        filename: str,
        content_type: str,
    ) -> ParseResult: ...
```

## Parse Result Structure

```python
@dataclass(frozen=True)
class ParseResult:
    parser_name: str
    parser_version: str
    content_type: str
    sections: list[ParsedSection]
    warnings: list[ParseWarning]
    page_count: int | None
    metadata: dict[str, Any]
    framework_version: str
```

### ParsedSection

Each section represents a contiguous block of extracted content:

- `content` — the extracted text
- `heading` — the section heading, if any
- `page` — the page number (1-indexed), if applicable
- `section_index` — sequential index within the document
- `content_type` — one of `text`, `table`, `heading`, `code`, `metadata`
- `metadata` — optional format-specific metadata (e.g., column names for CSV rows)

### ParseWarning

Non-fatal issues that should be surfaced to operators:

- `category` — `encoding`, `empty_content`, `unsupported_feature`
- `message` — human-readable description
- `location` — optional location reference (page, line, section)

## Error Handling

| Error Code | Meaning |
|---|---|
| `PARSER_UNSUPPORTED_FORMAT` | The content type has no registered parser |
| `PARSER_CORRUPT_INPUT` | The file is malformed or cannot be decoded |
| `PARSER_INTERNAL_ERROR` | The parser encountered an unexpected exception |
| `PARSER_NOT_ALLOWED` | The content type is not on the allow-list |

All errors are returned as `ParserError` with a stable error code and safe message.

## API Endpoint

### `POST /documents/{document_version_id}/parse`

Parses a document version that has passed malware scanning.

**Prerequisites:** The document version must have `parser_eligible: true` (i.e., a clean malware scan).

**Request:** No body required. The document content is read from object storage.

**Response:**
```json
{
  "document_version_id": "...",
  "parser_name": "zayd-text-parser",
  "parser_version": "1.0.0",
  "framework_version": "parser-framework-v1",
  "content_type": "text/plain",
  "sections": [
    {
      "content": "Line one",
      "heading": null,
      "page": null,
      "section_index": 0,
      "content_type": "text",
      "metadata": null
    }
  ],
  "warnings": [],
  "page_count": null,
  "metadata": {"filename": "test.txt", "byte_size": 8}
}
```

## Stub Parsers

PDF and DOCX parsers are **stubs** that validate structural integrity (PDF header, ZIP magic bytes) but do not extract text. They return an `unsupported_feature` warning. To enable full extraction:

1. Add `PyMuPDF` or `pdfplumber` as a dependency for PDF support.
2. Add `python-docx` as a dependency for DOCX support.
3. Replace the stub parsers with implementations that extract text, headings, tables, and page numbers.

## Adding a New Parser

1. Create a class implementing `DocumentParser` in `parsing.py`.
2. Register it in `_DEFAULT_PARSERS`.
3. Add the content type to `SUPPORTED_FILE_TYPES` in `documents.py` if not already present.
4. Write parser contract tests, format fixture tests, and corrupt-file tests.
5. Update this documentation.

## Thai and Arabic Text Support

All text-based parsers handle UTF-8 encoded Thai (ภาษาไทย) and Arabic (العربية) text natively. Invalid UTF-8 sequences trigger an `encoding` warning and are replaced with Unicode replacement characters rather than causing a parse failure.
