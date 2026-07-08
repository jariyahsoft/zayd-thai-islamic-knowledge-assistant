"""Unit tests for the document parser framework."""

from __future__ import annotations

import json

import pytest
from zayd_common.parsing import (
    PARSER_FRAMEWORK_VERSION,
    CsvParser,
    DocxStubParser,
    HtmlParser,
    JsonParser,
    MarkdownParser,
    ParserError,
    ParseResult,
    ParserRegistry,
    PdfStubParser,
    PlainTextParser,
)

# ---------------------------------------------------------------------------
# Parser contract tests — every parser satisfies the DocumentParser protocol
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "parser_cls",
    [
        PlainTextParser, MarkdownParser, HtmlParser,
        JsonParser, CsvParser, PdfStubParser, DocxStubParser,
    ],
)
def test_parser_has_required_attributes(parser_cls):
    parser = parser_cls()
    assert isinstance(parser.name, str) and parser.name
    assert isinstance(parser.version, str) and parser.version
    assert isinstance(parser.supported_content_types, frozenset)
    assert len(parser.supported_content_types) >= 1


@pytest.mark.parametrize(
    "parser_cls",
    [PlainTextParser, MarkdownParser, HtmlParser, JsonParser, CsvParser],
)
def test_parser_returns_parse_result(parser_cls):
    parser = parser_cls()
    ct = next(iter(parser.supported_content_types))

    # Build minimal valid content for each type
    content_map = {
        "text/plain": b"hello world",
        "text/markdown": b"# Title\nBody text",
        "text/html": b"<p>Hello</p>",
        "application/json": b'{"key": "value"}',
        "text/csv": b"a,b\n1,2\n",
    }
    content = content_map[ct]

    result = parser.parse(content=content, filename="test.txt", content_type=ct)
    assert isinstance(result, ParseResult)
    assert result.parser_name == parser.name
    assert result.parser_version == parser.version
    assert result.framework_version == PARSER_FRAMEWORK_VERSION


# ---------------------------------------------------------------------------
# Format fixture tests
# ---------------------------------------------------------------------------


def test_plain_text_extraction():
    parser = PlainTextParser()
    text = "Line one\n\nLine two\nLine three"
    result = parser.parse(content=text.encode(), filename="doc.txt", content_type="text/plain")

    assert len(result.sections) == 3
    assert result.sections[0].content == "Line one"
    assert result.sections[1].content == "Line two"
    assert result.sections[2].content == "Line three"
    assert result.warnings == []


def test_plain_text_empty_file_warns():
    parser = PlainTextParser()
    result = parser.parse(content=b"", filename="empty.txt", content_type="text/plain")

    assert len(result.sections) == 0
    assert any(w.category == "empty_content" for w in result.warnings)


def test_plain_text_invalid_utf8_warns():
    parser = PlainTextParser()
    content = b"valid text \xff\xfe invalid bytes"
    result = parser.parse(content=content, filename="bad.txt", content_type="text/plain")

    assert any(w.category == "encoding" for w in result.warnings)
    assert len(result.sections) > 0


def test_markdown_heading_extraction():
    parser = MarkdownParser()
    md = "# Title\n\nParagraph one.\n\n## Section\n\nParagraph two."
    result = parser.parse(content=md.encode(), filename="doc.md", content_type="text/markdown")

    headings = [s for s in result.sections if s.content_type == "heading"]
    assert len(headings) == 2
    assert headings[0].content == "Title"
    assert headings[1].content == "Section"

    body_sections = [s for s in result.sections if s.content_type == "text"]
    assert len(body_sections) == 2


def test_markdown_empty_file_warns():
    parser = MarkdownParser()
    result = parser.parse(content=b"", filename="empty.md", content_type="text/markdown")

    assert any(w.category == "empty_content" for w in result.warnings)


def test_html_tag_stripping():
    parser = HtmlParser()
    html = b"<html><body><h1>Title</h1><p>Content here</p></body></html>"
    result = parser.parse(content=html, filename="page.html", content_type="text/html")

    texts = [s.content for s in result.sections]
    assert "Title" in texts
    assert "Content here" in texts


def test_html_empty_content_warns():
    parser = HtmlParser()
    result = parser.parse(content=b"<html></html>", filename="e.html", content_type="text/html")

    assert any(w.category == "empty_content" for w in result.warnings)


def test_json_valid_object():
    parser = JsonParser()
    data = {"title": "Test", "count": 42}
    content = json.dumps(data).encode()
    result = parser.parse(content=content, filename="data.json", content_type="application/json")

    # First section is full JSON, subsequent sections are key summaries
    assert len(result.sections) >= 3
    assert result.sections[0].content_type == "metadata"
    assert "title: Test" in result.sections[1].content
    assert "count: 42" in result.sections[2].content


def test_json_malformed_raises():
    parser = JsonParser()
    with pytest.raises(ParserError) as exc_info:
        parser.parse(content=b"{invalid", filename="bad.json", content_type="application/json")

    assert exc_info.value.code == "PARSER_CORRUPT_INPUT"
    assert exc_info.value.parser_name == parser.name


def test_csv_with_header_and_rows():
    parser = CsvParser()
    content = b"name,age\nAli,30\nFatima,25\n"
    result = parser.parse(content=content, filename="data.csv", content_type="text/csv")

    assert result.metadata["header_columns"] == ["name", "age"]
    assert result.metadata["row_count"] == 2
    header_sections = [s for s in result.sections if s.heading == "header"]
    assert len(header_sections) == 1
    data_sections = [
        s for s in result.sections
        if s.content_type == "table" and s.heading != "header"
    ]
    assert len(data_sections) == 2
    # Verify column metadata on data rows
    assert data_sections[0].metadata == {"columns": {"name": "Ali", "age": "30"}}


def test_csv_empty_warns():
    parser = CsvParser()
    result = parser.parse(content=b"", filename="empty.csv", content_type="text/csv")

    assert any(w.category == "empty_content" for w in result.warnings)


# ---------------------------------------------------------------------------
# Corrupt-file tests
# ---------------------------------------------------------------------------


def test_pdf_stub_rejects_non_pdf():
    parser = PdfStubParser()
    with pytest.raises(ParserError) as exc_info:
        parser.parse(
            content=b"not a pdf file",
            filename="fake.pdf",
            content_type="application/pdf",
        )
    assert exc_info.value.code == "PARSER_CORRUPT_INPUT"


def test_pdf_stub_accepts_valid_header():
    parser = PdfStubParser()
    result = parser.parse(
        content=b"%PDF-1.7 some pdf content",
        filename="doc.pdf",
        content_type="application/pdf",
    )
    assert any(w.category == "unsupported_feature" for w in result.warnings)
    assert result.sections == []


def test_docx_stub_rejects_non_zip():
    parser = DocxStubParser()
    ct = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    with pytest.raises(ParserError) as exc_info:
        parser.parse(content=b"not a zip", filename="fake.docx", content_type=ct)
    assert exc_info.value.code == "PARSER_CORRUPT_INPUT"


def test_docx_stub_accepts_valid_header():
    parser = DocxStubParser()
    ct = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    result = parser.parse(content=b"PK\x03\x04 docx content", filename="doc.docx", content_type=ct)
    assert any(w.category == "unsupported_feature" for w in result.warnings)


def test_json_invalid_encoding_raises():
    parser = JsonParser()
    with pytest.raises(ParserError) as exc_info:
        parser.parse(
            content=b"\xff\xfe{\"key\":\"bad\"}",
            filename="bad.json",
            content_type="application/json",
        )
    assert exc_info.value.code == "PARSER_CORRUPT_INPUT"


# ---------------------------------------------------------------------------
# Plugin allow-list tests
# ---------------------------------------------------------------------------


def test_registry_default_includes_all_formats():
    registry = ParserRegistry()
    expected = {
        "text/plain",
        "text/markdown",
        "text/html",
        "application/json",
        "text/csv",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    assert registry.allowed_content_types == expected


def test_registry_rejects_unlisted_content_type():
    registry = ParserRegistry()
    with pytest.raises(ParserError) as exc_info:
        registry.parse(
            content=b"binary data",
            filename="file.bin",
            content_type="application/octet-stream",
        )
    assert exc_info.value.code == "PARSER_NOT_ALLOWED"


def test_registry_selects_correct_parser():
    registry = ParserRegistry()
    result = registry.parse(
        content=b"hello",
        filename="test.txt",
        content_type="text/plain",
    )
    assert result.parser_name == "zayd-text-parser"


def test_registry_custom_allow_list():
    """A registry with only a text parser refuses JSON."""
    registry = ParserRegistry(parsers=[PlainTextParser()])
    assert "application/json" not in registry.allowed_content_types

    with pytest.raises(ParserError) as exc_info:
        registry.parse(
            content=b'{"key":"value"}',
            filename="data.json",
            content_type="application/json",
        )
    assert exc_info.value.code == "PARSER_NOT_ALLOWED"


def test_registry_isolates_parser_internal_error():
    """If a parser raises an unexpected exception, registry wraps it."""

    class BrokenParser:
        name = "broken-parser"
        version = "0.0.0"
        supported_content_types = frozenset({"text/plain"})

        def parse(self, *, content, filename, content_type):
            raise RuntimeError("Unexpected failure")

    registry = ParserRegistry(parsers=[BrokenParser()])
    with pytest.raises(ParserError) as exc_info:
        registry.parse(
            content=b"hello",
            filename="test.txt",
            content_type="text/plain",
        )
    assert exc_info.value.code == "PARSER_INTERNAL_ERROR"
    assert exc_info.value.parser_name == "broken-parser"


# ---------------------------------------------------------------------------
# Idempotency / retryability
# ---------------------------------------------------------------------------


def test_parser_is_idempotent():
    """Parsing the same input twice returns identical results."""
    registry = ParserRegistry()
    kwargs = dict(content=b"hello world", filename="test.txt", content_type="text/plain")
    first = registry.parse(**kwargs)
    second = registry.parse(**kwargs)
    assert first == second


# ---------------------------------------------------------------------------
# Thai and Arabic content
# ---------------------------------------------------------------------------


def test_plain_text_handles_thai():
    parser = PlainTextParser()
    content = "บิสมิลลาฮิรเราะห์มานิรเราะฮีม\nสวัสดีครับ".encode()
    result = parser.parse(content=content, filename="thai.txt", content_type="text/plain")
    assert len(result.sections) == 2
    assert "บิสมิลลาฮิรเราะห์มานิรเราะฮีม" in result.sections[0].content


def test_plain_text_handles_arabic():
    parser = PlainTextParser()
    content = "بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ\nالحمد لله رب العالمين".encode()
    result = parser.parse(content=content, filename="arabic.txt", content_type="text/plain")
    assert len(result.sections) == 2
    assert "بِسْمِ" in result.sections[0].content
