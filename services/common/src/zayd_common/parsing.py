"""Document parser plugin framework.

Defines the parser plugin interface and baseline parsers for supported file
types.  Parsers operate on raw bytes and return structured ``ParseResult``
objects that retain page/section locations and extraction warnings.

Plugins are selected through an explicit allow-list and are never loaded
dynamically.  Unsupported features produce warnings rather than silent data
loss.  Parser failures are isolated and retryable — a corrupt input raises
``ParserError`` without affecting other documents.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

PARSER_FRAMEWORK_VERSION = "parser-framework-v1"

ParserErrorCode = Literal[
    "PARSER_UNSUPPORTED_FORMAT",
    "PARSER_CORRUPT_INPUT",
    "PARSER_INTERNAL_ERROR",
    "PARSER_NOT_ALLOWED",
]


class ParserError(Exception):
    """Raised when a parser encounters an unrecoverable problem."""

    def __init__(
        self,
        code: ParserErrorCode,
        message: str,
        *,
        parser_name: str = "unknown",
        status_code: int = 422,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.parser_name = parser_name
        self.status_code = status_code


@dataclass(frozen=True)
class ParseWarning:
    """Non-fatal extraction issue surfaced to the caller."""

    category: str
    message: str
    location: str | None = None


@dataclass(frozen=True)
class ParsedSection:
    """A contiguous block of extracted content."""

    content: str
    heading: str | None = None
    page: int | None = None
    section_index: int = 0
    content_type: Literal["text", "table", "heading", "code", "metadata"] = "text"
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class ParseResult:
    """Successful parse output returned by every parser."""

    parser_name: str
    parser_version: str
    content_type: str
    sections: list[ParsedSection]
    warnings: list[ParseWarning] = field(default_factory=list)
    page_count: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    framework_version: str = PARSER_FRAMEWORK_VERSION


class DocumentParser(Protocol):
    """Protocol that every parser plugin must satisfy."""

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


# ---------------------------------------------------------------------------
# Baseline parsers
# ---------------------------------------------------------------------------


class PlainTextParser:
    """Baseline parser for ``text/plain`` files."""

    name = "zayd-text-parser"
    version = "1.0.0"
    supported_content_types = frozenset({"text/plain"})

    def parse(
        self,
        *,
        content: bytes,
        filename: str,
        content_type: str,
    ) -> ParseResult:
        warnings: list[ParseWarning] = []
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = content.decode("utf-8", errors="replace")
                warnings.append(
                    ParseWarning(
                        category="encoding",
                        message=(
                            "File contained invalid UTF-8 sequences;"
                            " replacement characters inserted."
                        ),
                    )
                )
            except Exception as exc:
                raise ParserError(
                    "PARSER_CORRUPT_INPUT",
                    "Unable to decode text file.",
                    parser_name=self.name,
                ) from exc

        sections: list[ParsedSection] = []
        for idx, line in enumerate(text.splitlines()):
            stripped = line.strip()
            if stripped:
                sections.append(
                    ParsedSection(
                        content=stripped,
                        section_index=idx,
                    )
                )

        if not sections:
            warnings.append(
                ParseWarning(
                    category="empty_content",
                    message="Text file contains no extractable content.",
                )
            )

        return ParseResult(
            parser_name=self.name,
            parser_version=self.version,
            content_type=content_type,
            sections=sections,
            warnings=warnings,
            metadata={"filename": filename, "byte_size": len(content)},
        )


class MarkdownParser:
    """Baseline parser for ``text/markdown`` files.

    Recognises ATX headings (``#`` through ``######``) and groups content
    under them.
    """

    name = "zayd-markdown-parser"
    version = "1.0.0"
    supported_content_types = frozenset({"text/markdown"})

    def parse(
        self,
        *,
        content: bytes,
        filename: str,
        content_type: str,
    ) -> ParseResult:
        warnings: list[ParseWarning] = []
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("utf-8", errors="replace")
            warnings.append(
                ParseWarning(
                    category="encoding",
                    message=(
                        "Markdown file contained invalid UTF-8;"
                        " replacement characters inserted."
                    ),
                )
            )

        sections: list[ParsedSection] = []
        current_heading: str | None = None
        current_lines: list[str] = []
        section_idx = 0

        def _flush() -> None:
            nonlocal section_idx
            body = "\n".join(current_lines).strip()
            if body or current_heading:
                if current_heading:
                    sections.append(
                        ParsedSection(
                            content=current_heading,
                            heading=current_heading,
                            section_index=section_idx,
                            content_type="heading",
                        )
                    )
                    section_idx += 1
                if body:
                    sections.append(
                        ParsedSection(
                            content=body,
                            heading=current_heading,
                            section_index=section_idx,
                        )
                    )
                    section_idx += 1

        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                _flush()
                current_heading = stripped.lstrip("#").strip()
                current_lines = []
            else:
                current_lines.append(line)

        _flush()

        if not sections:
            warnings.append(
                ParseWarning(
                    category="empty_content",
                    message="Markdown file contains no extractable content.",
                )
            )

        return ParseResult(
            parser_name=self.name,
            parser_version=self.version,
            content_type=content_type,
            sections=sections,
            warnings=warnings,
            metadata={"filename": filename, "byte_size": len(content)},
        )


class HtmlParser:
    """Baseline parser for ``text/html`` files.

    Strips HTML tags using a simple regex-free approach and extracts text
    content.  No external dependency is required.
    """

    name = "zayd-html-parser"
    version = "1.0.0"
    supported_content_types = frozenset({"text/html"})

    def parse(
        self,
        *,
        content: bytes,
        filename: str,
        content_type: str,
    ) -> ParseResult:
        warnings: list[ParseWarning] = []
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("utf-8", errors="replace")
            warnings.append(
                ParseWarning(
                    category="encoding",
                    message="HTML file contained invalid UTF-8; replacement characters inserted.",
                )
            )

        clean = _strip_html_tags(text)
        sections: list[ParsedSection] = []
        for idx, line in enumerate(clean.splitlines()):
            stripped = line.strip()
            if stripped:
                sections.append(
                    ParsedSection(content=stripped, section_index=idx)
                )

        if not sections:
            warnings.append(
                ParseWarning(
                    category="empty_content",
                    message="HTML file contains no extractable text content.",
                )
            )

        return ParseResult(
            parser_name=self.name,
            parser_version=self.version,
            content_type=content_type,
            sections=sections,
            warnings=warnings,
            metadata={"filename": filename, "byte_size": len(content)},
        )


class JsonParser:
    """Baseline parser for ``application/json`` files.

    Validates structure and returns the serialised JSON as a single metadata
    section.  Nested structures produce a flattened content summary.
    """

    name = "zayd-json-parser"
    version = "1.0.0"
    supported_content_types = frozenset({"application/json"})

    def parse(
        self,
        *,
        content: bytes,
        filename: str,
        content_type: str,
    ) -> ParseResult:
        warnings: list[ParseWarning] = []
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ParserError(
                "PARSER_CORRUPT_INPUT",
                "JSON file contains invalid encoding.",
                parser_name=self.name,
            ) from exc

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ParserError(
                "PARSER_CORRUPT_INPUT",
                f"JSON file is malformed: {exc.msg}",
                parser_name=self.name,
            ) from exc

        sections = [
            ParsedSection(
                content=json.dumps(data, ensure_ascii=False, indent=2),
                section_index=0,
                content_type="metadata",
                metadata={"json_type": type(data).__name__},
            )
        ]

        if isinstance(data, dict):
            for idx, key in enumerate(data, start=1):
                value_repr = _json_value_summary(data[key])
                sections.append(
                    ParsedSection(
                        content=f"{key}: {value_repr}",
                        heading=str(key),
                        section_index=idx,
                    )
                )

        return ParseResult(
            parser_name=self.name,
            parser_version=self.version,
            content_type=content_type,
            sections=sections,
            warnings=warnings,
            metadata={"filename": filename, "byte_size": len(content)},
        )


class CsvParser:
    """Baseline parser for ``text/csv`` files.

    Each row is extracted as a table-typed section with its column values.
    """

    name = "zayd-csv-parser"
    version = "1.0.0"
    supported_content_types = frozenset({"text/csv"})

    def parse(
        self,
        *,
        content: bytes,
        filename: str,
        content_type: str,
    ) -> ParseResult:
        warnings: list[ParseWarning] = []
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("utf-8", errors="replace")
            warnings.append(
                ParseWarning(
                    category="encoding",
                    message="CSV file contained invalid UTF-8; replacement characters inserted.",
                )
            )

        try:
            reader = csv.reader(io.StringIO(text))
            rows = list(reader)
        except csv.Error as exc:
            raise ParserError(
                "PARSER_CORRUPT_INPUT",
                f"CSV file is malformed: {exc}",
                parser_name=self.name,
            ) from exc

        headers: list[str] | None = None
        sections: list[ParsedSection] = []

        for idx, row in enumerate(rows):
            if idx == 0 and row:
                headers = row
                sections.append(
                    ParsedSection(
                        content=" | ".join(row),
                        heading="header",
                        section_index=idx,
                        content_type="table",
                    )
                )
            else:
                cell_text = " | ".join(row) if row else ""
                if cell_text.strip():
                    sections.append(
                        ParsedSection(
                            content=cell_text,
                            section_index=idx,
                            content_type="table",
                            metadata=(
                                {"columns": dict(zip(headers, row, strict=True))}
                                if headers and len(headers) == len(row)
                                else None
                            ),
                        )
                    )

        if not sections:
            warnings.append(
                ParseWarning(
                    category="empty_content",
                    message="CSV file contains no data rows.",
                )
            )

        return ParseResult(
            parser_name=self.name,
            parser_version=self.version,
            content_type=content_type,
            sections=sections,
            warnings=warnings,
            page_count=None,
            metadata={
                "filename": filename,
                "byte_size": len(content),
                "header_columns": headers or [],
                "row_count": max(len(rows) - 1, 0) if headers else len(rows),
            },
        )


class PdfStubParser:
    """Stub parser for ``application/pdf``.

    Real PDF parsing requires an external library (e.g. PyMuPDF, pdfplumber).
    This parser validates that the content looks like a PDF header but does
    not extract text.  It exists so that the allow-list accepts PDFs and
    returns an informational warning about the stub.
    """

    name = "zayd-pdf-stub-parser"
    version = "1.0.0"
    supported_content_types = frozenset({"application/pdf"})

    def parse(
        self,
        *,
        content: bytes,
        filename: str,
        content_type: str,
    ) -> ParseResult:
        warnings: list[ParseWarning] = []

        if not content.startswith(b"%PDF"):
            raise ParserError(
                "PARSER_CORRUPT_INPUT",
                "File does not appear to be a valid PDF.",
                parser_name=self.name,
            )

        warnings.append(
            ParseWarning(
                category="unsupported_feature",
                message="PDF text extraction requires a production parser adapter. "
                "Only structural validation is available.",
            )
        )

        return ParseResult(
            parser_name=self.name,
            parser_version=self.version,
            content_type=content_type,
            sections=[],
            warnings=warnings,
            metadata={"filename": filename, "byte_size": len(content)},
        )


class DocxStubParser:
    """Stub parser for DOCX files.

    Real DOCX parsing requires ``python-docx``.  This parser validates the
    DOCX magic bytes (PK zip header) and returns a warning about the stub.
    """

    name = "zayd-docx-stub-parser"
    version = "1.0.0"
    supported_content_types = frozenset(
        {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    )

    def parse(
        self,
        *,
        content: bytes,
        filename: str,
        content_type: str,
    ) -> ParseResult:
        warnings: list[ParseWarning] = []

        if not content.startswith(b"PK"):
            raise ParserError(
                "PARSER_CORRUPT_INPUT",
                "File does not appear to be a valid DOCX archive.",
                parser_name=self.name,
            )

        warnings.append(
            ParseWarning(
                category="unsupported_feature",
                message="DOCX text extraction requires a production parser adapter (python-docx). "
                "Only structural validation is available.",
            )
        )

        return ParseResult(
            parser_name=self.name,
            parser_version=self.version,
            content_type=content_type,
            sections=[],
            warnings=warnings,
            metadata={"filename": filename, "byte_size": len(content)},
        )


# ---------------------------------------------------------------------------
# Parser registry / allow-list
# ---------------------------------------------------------------------------

#: Default allow-list of parser instances.  The registry is explicit — no
#: dynamic plugin loading.  Add new parsers here via ``register_parser``.
_DEFAULT_PARSERS: list[DocumentParser] = [
    PlainTextParser(),
    MarkdownParser(),
    HtmlParser(),
    JsonParser(),
    CsvParser(),
    PdfStubParser(),
    DocxStubParser(),
]


class ParserRegistry:
    """Immutable allow-list of parser plugins selected by content type.

    The registry indexes parsers by their declared ``supported_content_types``
    and refuses to parse content types that are not on the allow-list.
    """

    def __init__(self, parsers: list[DocumentParser] | None = None) -> None:
        self._parsers: list[DocumentParser] = list(parsers or _DEFAULT_PARSERS)
        self._index: dict[str, DocumentParser] = {}
        for parser in self._parsers:
            for ct in parser.supported_content_types:
                self._index[ct] = parser

    @property
    def allowed_content_types(self) -> frozenset[str]:
        return frozenset(self._index.keys())

    def get_parser(self, content_type: str) -> DocumentParser | None:
        return self._index.get(content_type)

    def parse(
        self,
        *,
        content: bytes,
        filename: str,
        content_type: str,
    ) -> ParseResult:
        """Select a parser by content type and parse the content.

        Raises ``ParserError`` if the content type is not on the allow-list
        or the parser fails.
        """
        parser = self.get_parser(content_type)
        if parser is None:
            raise ParserError(
                "PARSER_NOT_ALLOWED",
                f"No parser registered for content type '{content_type}'.",
            )
        try:
            return parser.parse(
                content=content,
                filename=filename,
                content_type=content_type,
            )
        except ParserError:
            raise
        except Exception as exc:
            raise ParserError(
                "PARSER_INTERNAL_ERROR",
                f"Parser '{parser.name}' encountered an unexpected error.",
                parser_name=parser.name,
            ) from exc


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _strip_html_tags(html: str) -> str:
    """Remove HTML tags using a simple state machine (no regex dependency).

    Inserts a newline when closing block-level tags to separate content blocks.
    """
    _BLOCK_TAGS = frozenset({
        "p", "div", "h1", "h2", "h3", "h4", "h5", "h6",
        "li", "tr", "br", "hr", "blockquote", "pre", "section", "article",
        "header", "footer", "nav", "main", "aside", "table", "tbody", "thead",
    })
    result: list[str] = []
    in_tag = False
    tag_buf: list[str] = []
    for char in html:
        if char == "<":
            in_tag = True
            tag_buf = []
        elif char == ">":
            in_tag = False
            tag_name = "".join(tag_buf).strip().lstrip("/").split()[0].lower() if tag_buf else ""
            if tag_name in _BLOCK_TAGS:
                result.append("\n")
        elif in_tag:
            tag_buf.append(char)
        else:
            result.append(char)
    return "".join(result)


def _json_value_summary(value: Any, *, max_length: int = 200) -> str:
    """Create a short text summary of a JSON value."""
    if isinstance(value, str):
        return value[:max_length] + ("…" if len(value) > max_length else "")
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return f"[array of {len(value)} items]"
    if isinstance(value, dict):
        return f"{{object with {len(value)} keys}}"
    if value is None:
        return "null"
    return str(value)[:max_length]
