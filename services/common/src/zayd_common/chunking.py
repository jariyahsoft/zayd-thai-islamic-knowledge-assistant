"""Versioned retrieval chunking framework.

The framework turns reviewed document text or parser sections into chunk
drafts that preserve semantic boundaries where possible and record strategy
versions for re-indexing and auditability.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal, Protocol
from uuid import UUID

from zayd_common.normalization import NORMALIZATION_FRAMEWORK_VERSION, normalize_text

CHUNKING_FRAMEWORK_VERSION = "retrieval-chunking-v1"
QURAN_VERSE_STRATEGY_VERSION = "quran-verse-v1"
HADITH_STRATEGY_VERSION = "hadith-record-v1"
FIQH_ISSUE_STRATEGY_VERSION = "fiqh-issue-v1"
HEADING_SECTION_STRATEGY_VERSION = "heading-section-v1"
TABLE_STRATEGY_VERSION = "table-block-v1"
PARAGRAPH_STRATEGY_VERSION = "paragraph-v1"
FIXED_WINDOW_STRATEGY_VERSION = "fixed-window-v1"
DEFAULT_FIXED_WINDOW_TOKENS = 180
DEFAULT_FIXED_WINDOW_OVERLAP = 30

ChunkStrategyName = Literal[
    "quran_verse",
    "hadith_record",
    "fiqh_issue",
    "heading_section",
    "table",
    "paragraph",
    "fixed_window",
]

_QURAN_REFERENCE_RE = re.compile(
    r"(?:qur'?an|อัลกุรอาน|กุรอาน|القرآن)\s*(?P<sura>\d{1,3})\s*[:：]\s*(?P<ayah>\d{1,3})",
    re.IGNORECASE,
)
_HADITH_REFERENCE_RE = re.compile(
    r"(?:hadith|หะดีษ|ฮะดีษ|حديث)\s*(?:no\.?|number|หมายเลข|เลขที่|ที่)?\s*"
    r"(?P<number>[A-Za-z0-9][A-Za-z0-9/_:-]*)",
    re.IGNORECASE,
)
_FIQH_ISSUE_RE = re.compile(
    r"^(?:#{1,6}\s*)?(?:issue|masalah|مسألة|ประเด็น|ปัญหา)\s*[:：#-]?\s*(?P<title>.+)$",
    re.IGNORECASE,
)
_MARKDOWN_HEADING_RE = re.compile(r"^(?P<marks>#{1,6})\s+(?P<title>.+)$")


class ChunkingError(Exception):
    """Raised when text cannot be chunked safely."""

    def __init__(self, code: str, message: str, *, status_code: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class ChunkSourceSection:
    """Input block from parser output or reviewed extracted text."""

    content: str
    heading: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    section: str | None = None
    content_type: str = "text"
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ChunkDraft:
    """A not-yet-persisted retrieval chunk."""

    document_version_id: UUID
    chunk_index: int
    content: str
    content_normalized: str
    token_count: int
    page_start: int | None
    page_end: int | None
    section: str | None
    reference: str
    strategy_name: ChunkStrategyName
    strategy_version: str
    framework_version: str
    metadata: dict[str, object]


@dataclass(frozen=True)
class ChunkingResult:
    document_version_id: UUID
    framework_version: str
    strategy_name: ChunkStrategyName
    strategy_version: str
    chunks: tuple[ChunkDraft, ...]


@dataclass(frozen=True)
class ChunkingRequest:
    document_version_id: UUID
    canonical_id: str
    version_number: int
    language: str
    document_type: str
    sections: tuple[ChunkSourceSection, ...]
    max_tokens: int = DEFAULT_FIXED_WINDOW_TOKENS
    overlap_tokens: int = DEFAULT_FIXED_WINDOW_OVERLAP


class ChunkingStrategy(Protocol):
    name: ChunkStrategyName
    version: str

    def applies(self, request: ChunkingRequest) -> bool: ...

    def chunk(self, request: ChunkingRequest) -> tuple[_RawChunk, ...]: ...


@dataclass(frozen=True)
class _RawChunk:
    content: str
    page_start: int | None = None
    page_end: int | None = None
    section: str | None = None
    reference_suffix: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


def chunk_text_for_retrieval(
    *,
    document_version_id: UUID,
    canonical_id: str,
    version_number: int,
    text: str,
    language: str,
    document_type: str,
    max_tokens: int = DEFAULT_FIXED_WINDOW_TOKENS,
    overlap_tokens: int = DEFAULT_FIXED_WINDOW_OVERLAP,
) -> ChunkingResult:
    """Chunk reviewed text using semantic strategies when possible."""
    return chunk_sections_for_retrieval(
        document_version_id=document_version_id,
        canonical_id=canonical_id,
        version_number=version_number,
        sections=(ChunkSourceSection(content=text),),
        language=language,
        document_type=document_type,
        max_tokens=max_tokens,
        overlap_tokens=overlap_tokens,
    )


def chunk_sections_for_retrieval(
    *,
    document_version_id: UUID,
    canonical_id: str,
    version_number: int,
    sections: tuple[ChunkSourceSection, ...],
    language: str,
    document_type: str,
    max_tokens: int = DEFAULT_FIXED_WINDOW_TOKENS,
    overlap_tokens: int = DEFAULT_FIXED_WINDOW_OVERLAP,
) -> ChunkingResult:
    """Chunk parser sections for retrieval."""
    normalized_sections = tuple(
        section for section in sections if section.content and section.content.strip()
    )
    if not normalized_sections:
        raise ChunkingError("CHUNKING_EMPTY_CONTENT", "No chunkable content was provided.")
    if max_tokens < 20:
        raise ChunkingError("CHUNKING_INVALID_WINDOW", "max_tokens must be at least 20.")
    if overlap_tokens < 0 or overlap_tokens >= max_tokens:
        raise ChunkingError(
            "CHUNKING_INVALID_OVERLAP",
            "overlap_tokens must be non-negative and smaller than max_tokens.",
        )
    request = ChunkingRequest(
        document_version_id=document_version_id,
        canonical_id=canonical_id,
        version_number=version_number,
        language=language,
        document_type=document_type.strip().lower(),
        sections=normalized_sections,
        max_tokens=max_tokens,
        overlap_tokens=overlap_tokens,
    )
    strategy = _select_strategy(request)
    raw_chunks = strategy.chunk(request)
    if not raw_chunks:
        strategy = FixedWindowStrategy()
        raw_chunks = strategy.chunk(request)
    drafts = _finalize_chunks(request, raw_chunks, strategy)
    return ChunkingResult(
        document_version_id=document_version_id,
        framework_version=CHUNKING_FRAMEWORK_VERSION,
        strategy_name=strategy.name,
        strategy_version=strategy.version,
        chunks=drafts,
    )


class QuranVerseStrategy:
    name: ChunkStrategyName = "quran_verse"
    version = QURAN_VERSE_STRATEGY_VERSION

    def applies(self, request: ChunkingRequest) -> bool:
        text = _joined_text(request.sections)
        return request.document_type == "quran" or bool(_QURAN_REFERENCE_RE.search(text))

    def chunk(self, request: ChunkingRequest) -> tuple[_RawChunk, ...]:
        chunks: list[_RawChunk] = []
        for section in request.sections:
            for line in section.content.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                match = _QURAN_REFERENCE_RE.search(stripped)
                if match is None and request.document_type != "quran":
                    continue
                suffix = (
                    f"quran-{match.group('sura')}-{match.group('ayah')}"
                    if match is not None
                    else f"quran-line-{len(chunks) + 1}"
                )
                chunks.append(
                    _RawChunk(
                        content=stripped,
                        page_start=section.page_start,
                        page_end=section.page_end,
                        section=section.section or section.heading,
                        reference_suffix=suffix,
                        metadata={"semantic_unit": "quran_verse"},
                    )
                )
        return tuple(chunks)


class HadithStrategy:
    name: ChunkStrategyName = "hadith_record"
    version = HADITH_STRATEGY_VERSION

    def applies(self, request: ChunkingRequest) -> bool:
        return request.document_type == "hadith" or bool(
            _HADITH_REFERENCE_RE.search(_joined_text(request.sections))
        )

    def chunk(self, request: ChunkingRequest) -> tuple[_RawChunk, ...]:
        return _chunk_by_boundary_pattern(
            request,
            pattern=_HADITH_REFERENCE_RE,
            semantic_unit="hadith",
            default_prefix="hadith",
        )


class FiqhIssueStrategy:
    name: ChunkStrategyName = "fiqh_issue"
    version = FIQH_ISSUE_STRATEGY_VERSION

    def applies(self, request: ChunkingRequest) -> bool:
        return request.document_type == "fiqh" or any(
            _FIQH_ISSUE_RE.match(line.strip())
            for section in request.sections
            for line in section.content.splitlines()
        )

    def chunk(self, request: ChunkingRequest) -> tuple[_RawChunk, ...]:
        return _chunk_by_boundary_pattern(
            request,
            pattern=_FIQH_ISSUE_RE,
            semantic_unit="fiqh_issue",
            default_prefix="fiqh-issue",
        )


class HeadingSectionStrategy:
    name: ChunkStrategyName = "heading_section"
    version = HEADING_SECTION_STRATEGY_VERSION

    def applies(self, request: ChunkingRequest) -> bool:
        has_section_headings = any(
            (section.heading and section.content_type != "table")
            or section.content_type == "heading"
            for section in request.sections
        )
        has_markdown_headings = any(
            _MARKDOWN_HEADING_RE.match(line.strip())
            for section in request.sections
            for line in section.content.splitlines()
        )
        return has_section_headings or has_markdown_headings

    def chunk(self, request: ChunkingRequest) -> tuple[_RawChunk, ...]:
        chunks: list[_RawChunk] = []
        current_heading: str | None = None
        current_lines: list[str] = []
        current_page: tuple[int | None, int | None] = (None, None)

        def flush() -> None:
            nonlocal current_lines
            body = "\n".join(current_lines).strip()
            if body:
                chunks.append(
                    _RawChunk(
                        content=body,
                        page_start=current_page[0],
                        page_end=current_page[1],
                        section=current_heading,
                        reference_suffix=_slug(current_heading or f"section-{len(chunks) + 1}"),
                        metadata={"semantic_unit": "heading_section", "heading": current_heading},
                    )
                )
            current_lines = []

        for section in request.sections:
            if section.heading or section.content_type == "heading":
                flush()
                current_heading = section.heading or section.content.strip()
                current_page = (section.page_start, section.page_end)
                if section.content_type != "heading":
                    current_lines.append(section.content)
                continue
            for line in section.content.splitlines():
                match = _MARKDOWN_HEADING_RE.match(line.strip())
                if match is not None:
                    flush()
                    current_heading = match.group("title").strip()
                    current_page = (section.page_start, section.page_end)
                else:
                    current_lines.append(line)
            if section.page_start is not None or section.page_end is not None:
                current_page = (section.page_start, section.page_end)
        flush()
        return tuple(chunks)


class TableStrategy:
    name: ChunkStrategyName = "table"
    version = TABLE_STRATEGY_VERSION

    def applies(self, request: ChunkingRequest) -> bool:
        return any(
            section.content_type == "table" or _looks_like_table(section.content)
            for section in request.sections
        )

    def chunk(self, request: ChunkingRequest) -> tuple[_RawChunk, ...]:
        chunks: list[_RawChunk] = []
        for index, section in enumerate(request.sections, start=1):
            if section.content_type != "table" and not _looks_like_table(section.content):
                continue
            chunks.append(
                _RawChunk(
                    content=section.content.strip(),
                    page_start=section.page_start,
                    page_end=section.page_end,
                    section=section.section or section.heading,
                    reference_suffix=f"table-{index}",
                    metadata={"semantic_unit": "table"},
                )
            )
        return tuple(chunks)


class ParagraphStrategy:
    name: ChunkStrategyName = "paragraph"
    version = PARAGRAPH_STRATEGY_VERSION

    def applies(self, request: ChunkingRequest) -> bool:
        paragraphs = _paragraphs(request.sections)
        return len(paragraphs) > 1 or any(
            len(paragraph.split()) <= request.max_tokens for paragraph, _section in paragraphs
        )

    def chunk(self, request: ChunkingRequest) -> tuple[_RawChunk, ...]:
        chunks: list[_RawChunk] = []
        for paragraph_index, (paragraph, section) in enumerate(
            _paragraphs(request.sections), start=1
        ):
            words = paragraph.split()
            if len(words) > request.max_tokens:
                chunks.extend(
                    _window_chunks(
                        request,
                        paragraph,
                        section=section,
                        prefix=f"paragraph-{paragraph_index}",
                        semantic_unit="paragraph_window",
                    )
                )
                continue
            chunks.append(
                _RawChunk(
                    content=paragraph,
                    page_start=section.page_start,
                    page_end=section.page_end,
                    section=section.section or section.heading,
                    reference_suffix=f"paragraph-{paragraph_index}",
                    metadata={"semantic_unit": "paragraph"},
                )
            )
        return tuple(chunks)


class FixedWindowStrategy:
    name: ChunkStrategyName = "fixed_window"
    version = FIXED_WINDOW_STRATEGY_VERSION

    def applies(self, request: ChunkingRequest) -> bool:
        return True

    def chunk(self, request: ChunkingRequest) -> tuple[_RawChunk, ...]:
        chunks: list[_RawChunk] = []
        for index, section in enumerate(request.sections, start=1):
            chunks.extend(
                _window_chunks(
                    request,
                    section.content,
                    section=section,
                    prefix=f"window-{index}",
                    semantic_unit="fixed_window",
                )
            )
        return tuple(chunks)


def _select_strategy(request: ChunkingRequest) -> ChunkingStrategy:
    strategies: tuple[ChunkingStrategy, ...] = (
        QuranVerseStrategy(),
        HadithStrategy(),
        FiqhIssueStrategy(),
        HeadingSectionStrategy(),
        TableStrategy(),
        ParagraphStrategy(),
        FixedWindowStrategy(),
    )
    for strategy in strategies:
        if strategy.applies(request):
            return strategy
    return FixedWindowStrategy()


def chunking_strategy_versions() -> tuple[str, ...]:
    """Return all semantic strategy versions in selection order."""
    return (
        QURAN_VERSE_STRATEGY_VERSION,
        HADITH_STRATEGY_VERSION,
        FIQH_ISSUE_STRATEGY_VERSION,
        HEADING_SECTION_STRATEGY_VERSION,
        TABLE_STRATEGY_VERSION,
        PARAGRAPH_STRATEGY_VERSION,
        FIXED_WINDOW_STRATEGY_VERSION,
    )


def _finalize_chunks(
    request: ChunkingRequest,
    raw_chunks: tuple[_RawChunk, ...],
    strategy: ChunkingStrategy,
) -> tuple[ChunkDraft, ...]:
    drafts: list[ChunkDraft] = []
    for index, raw in enumerate(raw_chunks):
        normalized = normalize_text(raw.content, language=request.language)
        reference_suffix = raw.reference_suffix or f"chunk-{index + 1}"
        reference = f"{request.canonical_id}:v{request.version_number}:{reference_suffix}"
        metadata: dict[str, object] = {
            **raw.metadata,
            "chunking_framework_version": CHUNKING_FRAMEWORK_VERSION,
            "chunking_strategy": strategy.name,
            "chunking_strategy_version": strategy.version,
            "normalization_framework_version": NORMALIZATION_FRAMEWORK_VERSION,
            "normalizer_version": normalized.normalizer_version,
            "normalization_steps": list(normalized.steps_applied),
            "context_before": _context(raw_chunks[index - 1].content) if index > 0 else None,
            "context_after": _context(raw_chunks[index + 1].content)
            if index + 1 < len(raw_chunks)
            else None,
        }
        drafts.append(
            ChunkDraft(
                document_version_id=request.document_version_id,
                chunk_index=index,
                content=raw.content,
                content_normalized=normalized.normalized,
                token_count=max(1, len(raw.content.split())),
                page_start=raw.page_start,
                page_end=raw.page_end,
                section=raw.section,
                reference=reference,
                strategy_name=strategy.name,
                strategy_version=strategy.version,
                framework_version=CHUNKING_FRAMEWORK_VERSION,
                metadata=metadata,
            )
        )
    return tuple(drafts)


def _chunk_by_boundary_pattern(
    request: ChunkingRequest,
    *,
    pattern: re.Pattern[str],
    semantic_unit: str,
    default_prefix: str,
) -> tuple[_RawChunk, ...]:
    chunks: list[_RawChunk] = []
    current_lines: list[str] = []
    current_ref: str | None = None
    current_section: ChunkSourceSection | None = None

    def flush() -> None:
        nonlocal current_lines, current_ref, current_section
        body = "\n".join(current_lines).strip()
        if body:
            suffix = current_ref or f"{default_prefix}-{len(chunks) + 1}"
            chunks.append(
                _RawChunk(
                    content=body,
                    page_start=current_section.page_start if current_section else None,
                    page_end=current_section.page_end if current_section else None,
                    section=current_section.section or current_section.heading
                    if current_section
                    else None,
                    reference_suffix=_slug(suffix),
                    metadata={"semantic_unit": semantic_unit},
                )
            )
        current_lines = []
        current_ref = None
        current_section = None

    for section in request.sections:
        for line in section.content.splitlines():
            stripped = line.strip()
            if not stripped:
                if current_lines:
                    current_lines.append("")
                continue
            match = pattern.search(stripped)
            if match is not None and current_lines:
                flush()
            if match is not None:
                current_ref = (
                    match.groupdict().get("number")
                    or match.groupdict().get("title")
                    or stripped
                )
                current_section = section
            elif current_section is None:
                current_section = section
            current_lines.append(stripped)
    flush()
    return tuple(chunks)


def _window_chunks(
    request: ChunkingRequest,
    text: str,
    *,
    section: ChunkSourceSection,
    prefix: str,
    semantic_unit: str,
) -> list[_RawChunk]:
    words = text.split()
    if not words:
        return []
    chunks: list[_RawChunk] = []
    step = max(1, request.max_tokens - request.overlap_tokens)
    for start in range(0, len(words), step):
        end = min(len(words), start + request.max_tokens)
        if start >= end:
            break
        chunks.append(
            _RawChunk(
                content=" ".join(words[start:end]),
                page_start=section.page_start,
                page_end=section.page_end,
                section=section.section or section.heading,
                reference_suffix=f"{prefix}-window-{len(chunks) + 1}",
                metadata={
                    "semantic_unit": semantic_unit,
                    "window_start_token": start,
                    "window_end_token": end,
                    "window_overlap_tokens": request.overlap_tokens,
                },
            )
        )
        if end == len(words):
            break
    return chunks


def _paragraphs(
    sections: tuple[ChunkSourceSection, ...],
) -> list[tuple[str, ChunkSourceSection]]:
    paragraphs: list[tuple[str, ChunkSourceSection]] = []
    for section in sections:
        for paragraph in re.split(r"\n\s*\n", section.content):
            stripped = paragraph.strip()
            if stripped:
                paragraphs.append((stripped, section))
    return paragraphs


def _joined_text(sections: tuple[ChunkSourceSection, ...]) -> str:
    return "\n".join(section.content for section in sections)


def _looks_like_table(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    pipe_rows = [line for line in lines if line.count("|") >= 2]
    return len(pipe_rows) >= 2


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9ก-๙؀-ۿ]+", "-", value.strip()).strip("-")
    return slug.lower()[:80] or "chunk"


def _context(text: str) -> str:
    return " ".join(text.split())[:240]
