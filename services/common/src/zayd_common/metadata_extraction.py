"""Metadata extraction service for document ingestion.

Uses configurable rule-based extractors to suggest title, author,
translator, chapter, madhhab, document type, and references from parsed
document text.

All suggested fields are marked UNVERIFIED so they cannot overwrite
reviewed metadata without explicit approval.  Extraction is idempotent:
re-running on the same version produces the same suggestions.

The service stores extractor name, version, prompt version, and a
confidence score (0.0–1.0) for every suggestion so downstream audit and
human-review workflows can trace provenance.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol
from uuid import UUID, uuid4

from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

METADATA_EXTRACTION_POLICY_VERSION = "metadata-extraction-v1"
DEFAULT_EXTRACTOR_NAME = "zayd-rule-extractor"
DEFAULT_EXTRACTOR_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Error types
# ---------------------------------------------------------------------------

MetadataExtractionErrorCode = Literal[
    "EXTRACTION_VERSION_NOT_FOUND",
    "EXTRACTION_VERSION_NOT_PARSED",
    "EXTRACTION_MALFORMED_OUTPUT",
    "EXTRACTION_PROVIDER_UNAVAILABLE",
]


class MetadataExtractionError(Exception):
    """Raised when a metadata extraction operation cannot complete."""

    def __init__(
        self,
        code: MetadataExtractionErrorCode,
        message: str,
        *,
        status_code: int = 422,
        provider: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.provider = provider


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

MetadataVerificationStatus = Literal["unverified", "verified", "overridden_by_reviewer"]


@dataclass(frozen=True)
class ExtractedField:
    """A single extracted metadata value with provenance."""

    name: str
    value: str | None
    confidence: float  # 0.0–1.0
    verification_status: MetadataVerificationStatus = "unverified"
    extractor_name: str = DEFAULT_EXTRACTOR_NAME
    extractor_version: str = DEFAULT_EXTRACTOR_VERSION
    prompt_version: str | None = None  # set when an AI provider is used
    reason: str | None = None


@dataclass(frozen=True)
class ExtractedChapter:
    """A single chapter or section reference found in the document."""

    index: int
    title: str | None
    page: int | None
    confidence: float
    verification_status: MetadataVerificationStatus = "unverified"


@dataclass(frozen=True)
class ExtractedReference:
    """A cross-reference to another document, verse, or authority."""

    reference_text: str
    confidence: float
    reference_type: str  # e.g. "quran", "hadith", "book", "authority"
    verification_status: MetadataVerificationStatus = "unverified"


@dataclass(frozen=True)
class MetadataExtractionResult:
    """All metadata suggestions derived from a parsed document version.

    Every field is UNVERIFIED by default.  A reviewer must explicitly
    promote suggestions to VERIFIED before they overwrite the canonical
    Document metadata.
    """

    document_id: UUID
    document_version_id: UUID
    extractor_name: str
    extractor_version: str
    policy_version: str = METADATA_EXTRACTION_POLICY_VERSION

    title: list[ExtractedField] = field(default_factory=list)
    author: list[ExtractedField] = field(default_factory=list)
    translator: list[ExtractedField] = field(default_factory=list)
    madhhab: list[ExtractedField] = field(default_factory=list)
    document_type: list[ExtractedField] = field(default_factory=list)
    publisher: list[ExtractedField] = field(default_factory=list)
    edition: list[ExtractedField] = field(default_factory=list)
    chapters: list[ExtractedChapter] = field(default_factory=list)
    references: list[ExtractedReference] = field(default_factory=list)

    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

VALID_MADHHAB = frozenset({
    "shafii", "hanafi", "maliki", "hanbali",
    "jafari", "unknown",
})

VALID_DOCUMENT_TYPES = frozenset({
    "book", "chapter", "article", "fatwa", "lecture",
    "letter", "commentary", "thesis", "unknown",
})


def validate_extracted_madhhab(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in VALID_MADHHAB:
        return normalized
    return "unknown"


def validate_extracted_document_type(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in VALID_DOCUMENT_TYPES:
        return normalized
    return "unknown"


def validate_confidence(value: float) -> float:
    if not 0.0 <= value <= 1.0:
        raise MetadataExtractionError(
            "EXTRACTION_MALFORMED_OUTPUT",
            f"Confidence must be between 0.0 and 1.0, got {value}.",
        )
    return value


# ---------------------------------------------------------------------------
# Extractor protocol and providers
# ---------------------------------------------------------------------------


class MetadataExtractor(Protocol):
    """Protocol for document metadata extraction providers."""

    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    @property
    def prompt_version(self) -> str | None: ...

    def extract(
        self,
        *,
        text: str,
        sections: list[dict[str, Any]],
        filename: str,
        content_type: str,
    ) -> MetadataExtractionResult: ...


class RuleBasedExtractor:
    """Deterministic rule-based metadata extractor.

    Uses simple heuristics over the first N lines of plain text:
    - Title is the first non-empty line.
    - Author is detected by searching for patterns like "โดย" (Thai "by"),
      "ผู้แต่ง", "เขียนโดย", or Arabic "تأليف".
    - Translator is detected by searching for "ผู้แปล", "แปลโดย",
      "ترجمة".
    - Madhhab is detected by searching for known madhhab names.
    - Document type is detected from keywords and filename extension.
    - Chapters are detected by ATX-like heading patterns.
    - References are detected by patterns like "Quran X:Y" or "หะดีษที่".
    """

    name = DEFAULT_EXTRACTOR_NAME
    version = DEFAULT_EXTRACTOR_VERSION
    prompt_version: str | None = None  # rule-based has no prompt

    # Thai author/translator markers
    _THAI_AUTHOR_MARKERS = re.compile(
        r"(?:โดย|ผู้แต่ง|เขียนโดย|แต่งโดย)",
        re.IGNORECASE,
    )
    _THAI_TRANSLATOR_MARKERS = re.compile(
        r"(?:ผู้แปล|แปลโดย|แปล|แปลจาก|แปลเป็น)",
        re.IGNORECASE,
    )
    _ENGLISH_AUTHOR_MARKERS = re.compile(
        r"(?:author|authored by|written by)[:：\s]",
        re.IGNORECASE,
    )
    _ENGLISH_TRANSLATOR_MARKERS = re.compile(
        r"(?:translation by|translated by|translator)[:：\s]",
        re.IGNORECASE,
    )
    _ARABIC_AUTHOR_MARKERS = re.compile(
        r"(?:تأليف|المؤلف)",
        re.IGNORECASE,
    )
    _ARABIC_TRANSLATOR_MARKERS = re.compile(
        r"(?:ترجمة|المترجم|مترجم)",
        re.IGNORECASE,
    )
    _MADHHAB_MARKERS = re.compile(
        r"(?:มัซฮับ|มัษฮับ|มัซฮาบ|school of thought"
        r"|شافعي|حنفي|مالكي|حنبل|جعفري"
        r"|shafi[′']?i|hanafi|maliki|hanbali|jafari)",
        re.IGNORECASE,
    )
    _KNOWN_MADHHAB = re.compile(
        r"(?:shafii|hanafi|maliki|hanbali|jafari"
        r"|شافعي|حنفي|مالكي|حنبل|جعفري)",
        re.IGNORECASE,
    )
    _CHAPTER_MARKER = re.compile(
        r"^(?:บทที่|ตอนที่|فصل|باب|chapter|section)\s*[\dIVXLivxl]+",
        re.IGNORECASE,
    )
    _QURAN_REF = re.compile(
        r"(?:อัลกุรอาน|quran|القرآن|qur[ᾱā]?n)\s*(?:\d+)[:\s]\s*\d+",
        re.IGNORECASE,
    )
    _HADITH_REF = re.compile(
        r"(?:หะดีษ|ฮะดีษ|hadith|حديث)\s*(?:ที่|หมายเลข|เลขที่|no[.:]?\s*)?\s*\d+",
        re.IGNORECASE,
    )

    def extract(
        self,
        *,
        text: str,
        sections: list[dict[str, Any]],
        filename: str,
        content_type: str,
    ) -> MetadataExtractionResult:
        document_id = uuid4()
        version_id = uuid4()
        warnings: list[str] = []
        title_suggestions: list[ExtractedField] = []
        author_suggestions: list[ExtractedField] = []
        translator_suggestions: list[ExtractedField] = []
        madhhab_suggestions: list[ExtractedField] = []
        doc_type_suggestions: list[ExtractedField] = []
        publisher_suggestions: list[ExtractedField] = []
        edition_suggestions: list[ExtractedField] = []
        chapter_suggestions: list[ExtractedChapter] = []
        reference_suggestions: list[ExtractedReference] = []

        # Lines of text for line-based heuristics
        lines = text.splitlines()
        non_empty_lines = [ln.strip() for ln in lines if ln.strip()]

        if not non_empty_lines:
            warnings.append("Document text is empty; no metadata could be extracted.")

        # --- Title: first non-empty line ---
        if non_empty_lines:
            title_suggestions.append(
                ExtractedField(
                    name="title",
                    value=non_empty_lines[0][:500],
                    confidence=0.5,
                    reason="Detected as first non-empty line of text.",
                )
            )

        # --- Author detection ---
        for line in non_empty_lines[:50]:
            m = self._THAI_AUTHOR_MARKERS.search(line)
            if m:
                after = line[m.end() :].strip().strip(":：")
                if after:
                    author_suggestions.append(
                        ExtractedField(
                            name="author",
                            value=after[:255],
                            confidence=0.7,
                            reason=f"Matched Thai author marker: {m.group().strip()}",
                        )
                    )
                    break
            m = self._ENGLISH_AUTHOR_MARKERS.search(line)
            if m:
                after = line[m.end() :].strip().strip(":：")
                if after:
                    author_suggestions.append(
                        ExtractedField(
                            name="author",
                            value=after[:255],
                            confidence=0.7,
                            reason=f"Matched English author marker: {m.group().strip()}",
                        )
                    )
                    break
            m = self._ARABIC_AUTHOR_MARKERS.search(line)
            if m:
                after = line[m.end() :].strip().strip(":：")
                if after:
                    author_suggestions.append(
                        ExtractedField(
                            name="author",
                            value=after[:255],
                            confidence=0.7,
                            reason=f"Matched Arabic author marker: {m.group().strip()}",
                        )
                    )
                    break

        # --- Translator detection ---
        for line in non_empty_lines[:50]:
            m = self._THAI_TRANSLATOR_MARKERS.search(line)
            if m:
                after = line[m.end() :].strip().strip(":：")
                if after:
                    translator_suggestions.append(
                        ExtractedField(
                            name="translator",
                            value=after[:255],
                            confidence=0.7,
                            reason=f"Matched Thai translator marker: {m.group().strip()}",
                        )
                    )
                    break
            m = self._ENGLISH_TRANSLATOR_MARKERS.search(line)
            if m:
                after = line[m.end() :].strip().strip(":：")
                if after:
                    translator_suggestions.append(
                        ExtractedField(
                            name="translator",
                            value=after[:255],
                            confidence=0.7,
                            reason=f"Matched English translator marker: {m.group().strip()}",
                        )
                    )
                    break
            m = self._ARABIC_TRANSLATOR_MARKERS.search(line)
            if m:
                after = line[m.end() :].strip().strip(":：")
                if after:
                    translator_suggestions.append(
                        ExtractedField(
                            name="translator",
                            value=after[:255],
                            confidence=0.7,
                            reason=f"Matched Arabic translator marker: {m.group().strip()}",
                        )
                    )
                    break

        # --- Madhhab detection ---
        for line in non_empty_lines:
            m = self._KNOWN_MADHHAB.search(line)
            if m:
                matched = m.group().lower()
                validated = validate_extracted_madhhab(matched)
                if validated != "unknown":
                    madhhab_suggestions.append(
                        ExtractedField(
                            name="madhhab",
                            value=validated,
                            confidence=0.6,
                            reason=f"Matched madhhab name: {matched}",
                        )
                    )
                    break

        # --- Document type from filename extension ---
        ext_doc_type = self._doc_type_from_filename(filename)
        if ext_doc_type:
            doc_type_suggestions.append(
                ExtractedField(
                    name="document_type",
                    value=ext_doc_type,
                    confidence=0.8,
                    reason=f"Inferred from filename extension: .{filename.rsplit('.', 1)[-1]}",
                )
            )

        # --- Chapter detection ---
        for i, line in enumerate(lines):  # noqa: B007
            if self._CHAPTER_MARKER.match(line.strip()):
                chapter_suggestions.append(
                    ExtractedChapter(
                        index=len(chapter_suggestions) + 1,
                        title=line.strip(),
                        page=None,
                        confidence=0.5,
                    )
                )

        # --- Reference detection ---
        for line in lines:
            m = self._QURAN_REF.search(line)
            if m:
                reference_suggestions.append(
                    ExtractedReference(
                        reference_text=m.group(),
                        confidence=0.6,
                        reference_type="quran",
                    )
                )
            m = self._HADITH_REF.search(line)
            if m:
                reference_suggestions.append(
                    ExtractedReference(
                        reference_text=m.group(),
                        confidence=0.6,
                        reference_type="hadith",
                    )
                )

        # If no author found, leave empty
        if not author_suggestions:
            warnings.append("No author detected in first 50 lines.")

        return MetadataExtractionResult(
            document_id=document_id,
            document_version_id=version_id,
            extractor_name=self.name,
            extractor_version=self.version,
            title=title_suggestions,
            author=author_suggestions,
            translator=translator_suggestions,
            madhhab=madhhab_suggestions,
            document_type=doc_type_suggestions,
            publisher=publisher_suggestions,
            edition=edition_suggestions,
            chapters=chapter_suggestions,
            references=reference_suggestions,
            warnings=warnings,
        )

    @staticmethod
    def _doc_type_from_filename(filename: str) -> str | None:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        mapping = {
            "pdf": "book",
            "docx": "book",
            "txt": "article",
            "md": "article",
            "html": "article",
            "json": "article",
            "csv": "article",
        }
        return mapping.get(ext)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class MetadataExtractionService:
    """Orchestrates metadata extraction for a document version and persists
    the result as unverified suggestions in version metadata."""

    def __init__(
        self,
        uow: SQLAlchemyUnitOfWork,
        extractor: MetadataExtractor | None = None,
    ) -> None:
        self.uow = uow
        self.extractor = extractor or RuleBasedExtractor()

    def extract(
        self,
        *,
        document_version_id: UUID,
        text: str | None = None,
        sections: list[dict[str, Any]] | None = None,
        filename: str = "",
        content_type: str = "",
    ) -> MetadataExtractionResult:
        """Run metadata extraction against a document version.

        If ``text`` is provided, it is used directly.  Otherwise the
        module reads ``extracted_text`` from the version record and the
        parse sections from ``metadata_json``.

        Returns a ``MetadataExtractionResult`` with all fields marked
        UNVERIFIED.  Does **not** overwrite canonical Document fields.
        """
        with self.uow:
            version = self.uow.documents.get_version_by_id(document_version_id)
            if version is None:
                raise MetadataExtractionError(
                    "EXTRACTION_VERSION_NOT_FOUND",
                    "Document version not found.",
                    status_code=404,
                )
            document = self.uow.documents.get_by_id(version.document_id)  # noqa: F841

            # Resolve text to extract from
            resolved_text = text or version.extracted_text or ""
            resolved_sections = sections or version.metadata_json.get("parsed_sections", [])
            resolved_filename = filename or version.metadata_json.get("filename", "uploaded-file")
            resolved_content_type = content_type or version.metadata_json.get(
                "content_type", "application/octet-stream"
            )

            if not resolved_text and not resolved_sections:
                raise MetadataExtractionError(
                    "EXTRACTION_VERSION_NOT_PARSED",
                    "Document version has no parsed text or sections. "
                    "Run the parser first.",
                )

            result = self.extractor.extract(
                text=resolved_text,
                sections=resolved_sections,
                filename=resolved_filename,
                content_type=resolved_content_type,
            )

            # Fix IDs to match the actual version
            result = MetadataExtractionResult(
                document_id=version.document_id,
                document_version_id=version.id,
                extractor_name=result.extractor_name,
                extractor_version=result.extractor_version,
                title=result.title,
                author=result.author,
                translator=result.translator,
                madhhab=result.madhhab or [],
                document_type=result.document_type,
                publisher=result.publisher,
                edition=result.edition,
                chapters=result.chapters,
                references=result.references,
                warnings=result.warnings,
            )

            # Persist the extraction result as version metadata (immutable/append-only)
            existing_meta = dict(version.metadata_json or {})
            existing_meta["metadata_extraction"] = self._extraction_to_dict(result)
            version.metadata_json = existing_meta
            self.uow.documents.add_version(version)
            self.uow.commit()

            return result

    def get_extraction(
        self,
        *,
        document_version_id: UUID,
    ) -> MetadataExtractionResult | None:
        """Retrieve a previously stored extraction result, if any."""
        with self.uow:
            version = self.uow.documents.get_version_by_id(document_version_id)
            if version is None:
                return None
            meta = version.metadata_json or {}
            stored = meta.get("metadata_extraction")
            if stored is None:
                return None
            return self._dict_to_extraction(stored)

    @staticmethod
    def _extraction_to_dict(result: MetadataExtractionResult) -> dict[str, Any]:
        return {
            "document_id": str(result.document_id),
            "document_version_id": str(result.document_version_id),
            "extractor_name": result.extractor_name,
            "extractor_version": result.extractor_version,
            "policy_version": result.policy_version,
            "title": [_serialize_field(f) for f in result.title],
            "author": [_serialize_field(f) for f in result.author],
            "translator": [_serialize_field(f) for f in result.translator],
            "madhhab": [_serialize_field(f) for f in (result.madhhab or [])],
            "document_type": [_serialize_field(f) for f in result.document_type],
            "publisher": [_serialize_field(f) for f in result.publisher],
            "edition": [_serialize_field(f) for f in result.edition],
            "chapters": [
                {
                    "index": c.index,
                    "title": c.title,
                    "page": c.page,
                    "confidence": c.confidence,
                    "verification_status": c.verification_status,
                }
                for c in result.chapters
            ],
            "references": [
                {
                    "reference_text": r.reference_text,
                    "confidence": r.confidence,
                    "reference_type": r.reference_type,
                    "verification_status": r.verification_status,
                }
                for r in result.references
            ],
            "warnings": list(result.warnings),
        }

    @staticmethod
    def _dict_to_extraction(data: dict[str, Any]) -> MetadataExtractionResult:
        def _parse_field_list(items: list[dict[str, Any]]) -> list[ExtractedField]:
            return [
                ExtractedField(
                    name=str(item.get("name", "")),
                    value=item.get("value"),
                    confidence=float(item.get("confidence", 0.0)),
                    verification_status=item.get("verification_status", "unverified"),
                    extractor_name=str(item.get("extractor_name", DEFAULT_EXTRACTOR_NAME)),
                    extractor_version=str(item.get("extractor_version", DEFAULT_EXTRACTOR_VERSION)),
                    prompt_version=item.get("prompt_version"),
                    reason=item.get("reason"),
                )
                for item in items
            ]

        return MetadataExtractionResult(
            document_id=UUID(data["document_id"]),
            document_version_id=UUID(data["document_version_id"]),
            extractor_name=str(data.get("extractor_name", DEFAULT_EXTRACTOR_NAME)),
            extractor_version=str(data.get("extractor_version", DEFAULT_EXTRACTOR_VERSION)),
            policy_version=str(data.get("policy_version", METADATA_EXTRACTION_POLICY_VERSION)),
            title=_parse_field_list(data.get("title", [])),
            author=_parse_field_list(data.get("author", [])),
            translator=_parse_field_list(data.get("translator", [])),
            madhhab=_parse_field_list(data.get("madhhab", [])),
            document_type=_parse_field_list(data.get("document_type", [])),
            publisher=_parse_field_list(data.get("publisher", [])),
            edition=_parse_field_list(data.get("edition", [])),
            chapters=[
                ExtractedChapter(
                    index=int(c["index"]),
                    title=c.get("title"),
                    page=c.get("page"),
                    confidence=float(c["confidence"]),
                    verification_status=c.get("verification_status", "unverified"),
                )
                for c in data.get("chapters", [])
            ],
            references=[
                ExtractedReference(
                    reference_text=str(r["reference_text"]),
                    confidence=float(r["confidence"]),
                    reference_type=str(r.get("reference_type", "book")),
                    verification_status=r.get("verification_status", "unverified"),
                )
                for r in data.get("references", [])
            ],
            warnings=list(data.get("warnings", [])),
        )


def _serialize_field(field: ExtractedField) -> dict[str, Any]:
    """Convert an ``ExtractedField`` to a serializable dict."""
    return _field_to_dict(field)


def _field_to_dict(field: ExtractedField) -> dict[str, Any]:
    return {
        "name": field.name,
        "value": field.value,
        "confidence": field.confidence,
        "verification_status": field.verification_status,
        "extractor_name": field.extractor_name,
        "extractor_version": field.extractor_version,
        "prompt_version": field.prompt_version,
        "reason": field.reason,
    }
