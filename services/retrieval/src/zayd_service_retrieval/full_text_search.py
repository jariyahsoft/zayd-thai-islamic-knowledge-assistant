"""Exact-reference and PostgreSQL full-text retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import Text, cast, func, literal, or_, select
from zayd_common.database.models import (
    Document,
    DocumentChunk,
    DocumentVersion,
    Source,
    SourceLicense,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.enums import DocumentStatus
from zayd_common.normalization import NORMALIZATION_FRAMEWORK_VERSION, normalize_text

FULL_TEXT_RETRIEVER_VERSION = "full-text-retriever-v1"
FULL_TEXT_REFERENCE_SCORE = 1_000.0
FULL_TEXT_PREFIX_SCORE = 150.0
FULL_TEXT_CONTENT_SCORE = 25.0

RetrievalLicenseStatus = Literal[
    "persistent_private",
    "persistent_redistributable",
]
_ELIGIBLE_LICENSE_STATUSES = frozenset({"persistent_private", "persistent_redistributable"})


class FullTextSearchError(Exception):
    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class FullTextSearchQuery:
    text: str
    language: str
    madhhab: str | None = None
    source_type: str | None = None
    license_status: RetrievalLicenseStatus | None = None
    source_language: str | None = None
    reliability_level_min: int | None = None
    limit: int = 10
    offset: int = 0


@dataclass(frozen=True)
class FullTextSearchResult:
    chunk_id: UUID
    document_version_id: UUID
    document_id: UUID
    source_id: UUID
    canonical_reference: str
    content: str
    content_normalized: str
    language: str
    madhhab: str
    source_type: str
    license_status: str
    score_exact: float | None
    score_full_text: float
    score_final: float
    rank: int
    metadata: dict[str, object]


@dataclass(frozen=True)
class FullTextSearchResponse:
    query_original: str
    query_normalized: str
    retriever_version: str
    normalization_framework_version: str
    results: tuple[FullTextSearchResult, ...]


class FullTextSearchService:
    """Search only published chunks with deterministic reference handling."""

    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self.uow = uow

    def search(self, query: FullTextSearchQuery) -> FullTextSearchResponse:
        normalized_text = query.text.strip()
        if not normalized_text:
            raise FullTextSearchError(
                "FULL_TEXT_QUERY_REQUIRED",
                "Search text is required.",
                status_code=400,
            )
        if query.limit < 1 or query.limit > 100:
            raise FullTextSearchError(
                "FULL_TEXT_INVALID_LIMIT",
                "limit must be between 1 and 100.",
                status_code=400,
            )
        if query.offset < 0:
            raise FullTextSearchError(
                "FULL_TEXT_INVALID_OFFSET",
                "offset must be non-negative.",
                status_code=400,
            )
        if query.reliability_level_min is not None and (
            query.reliability_level_min < 1 or query.reliability_level_min > 5
        ):
            raise FullTextSearchError(
                "FULL_TEXT_INVALID_RELIABILITY",
                "reliability_level_min must be between 1 and 5.",
                status_code=400,
            )

        normalized = normalize_text(normalized_text, language=query.language)
        reference_key = normalized.normalized.casefold()
        with self.uow:
            session = self._session()
            supports_postgres = (
                session.bind is not None
                and session.bind.dialect.name == "postgresql"
            )
            statement = self._base_statement(query=query)
            rows = session.execute(statement).all()
            results = self._rank_rows(
                rows,
                normalized_query=normalized.normalized,
                reference_key=reference_key,
                supports_postgres=supports_postgres,
            )
            paged = results[query.offset : query.offset + query.limit]
            self.uow.commit()
        return FullTextSearchResponse(
            query_original=query.text,
            query_normalized=normalized.normalized,
            retriever_version=FULL_TEXT_RETRIEVER_VERSION,
            normalization_framework_version=NORMALIZATION_FRAMEWORK_VERSION,
            results=tuple(paged),
        )

    def _base_statement(self, *, query: FullTextSearchQuery) -> Any:
        statement = (
            select(DocumentChunk, DocumentVersion, Document, Source, SourceLicense)
            .join(DocumentVersion, DocumentVersion.id == DocumentChunk.document_version_id)
            .join(Document, Document.id == DocumentVersion.document_id)
            .join(Source, Source.id == Document.source_id)
            .join(SourceLicense, SourceLicense.id == Document.source_license_id)
            .where(DocumentChunk.is_published.is_(True))
            .where(Document.review_status == DocumentStatus.PUBLISHED.value)
            .where(DocumentVersion.status == DocumentStatus.PUBLISHED.value)
            .where(DocumentVersion.frozen_at.is_not(None))
            .where(Source.is_active.is_(True))
            .where(SourceLicense.status.in_(_ELIGIBLE_LICENSE_STATUSES))
            .where(SourceLicense.embedding_permission == "allowed")
        )
        if query.madhhab is not None:
            statement = statement.where(Document.madhhab == query.madhhab.strip())
        if query.source_type is not None:
            statement = statement.where(Source.source_type == query.source_type.strip())
        if query.license_status is not None:
            statement = statement.where(SourceLicense.status == query.license_status)
        if query.source_language is not None:
            statement = statement.where(Source.language == query.source_language.strip())
        if query.reliability_level_min is not None:
            statement = statement.where(Source.reliability_level >= query.reliability_level_min)
        return statement.order_by(DocumentChunk.chunk_index.asc())

    def _rank_rows(
        self,
        rows: list[tuple[DocumentChunk, DocumentVersion, Document, Source, SourceLicense]],
        *,
        normalized_query: str,
        reference_key: str,
        supports_postgres: bool,
    ) -> list[FullTextSearchResult]:
        scored: list[tuple[float, float | None, float, FullTextSearchResult]] = []
        query_terms = tuple(term for term in normalized_query.split() if term)
        for chunk, version, document, source, license_record in rows:
            normalized_content = chunk.content_normalized.casefold()
            reference = (chunk.reference or "").casefold()
            exact_score: float | None = None
            full_text_score = 0.0
            if reference == reference_key:
                exact_score = FULL_TEXT_REFERENCE_SCORE
                full_text_score = FULL_TEXT_REFERENCE_SCORE
            elif reference.startswith(reference_key) and reference_key:
                exact_score = FULL_TEXT_PREFIX_SCORE
                full_text_score = FULL_TEXT_PREFIX_SCORE
            elif normalized_query and normalized_query.casefold() in normalized_content:
                full_text_score = FULL_TEXT_CONTENT_SCORE + (
                    len(query_terms) / max(1, len(normalized_content.split()))
                )
            else:
                term_hits = sum(1 for term in query_terms if term.casefold() in normalized_content)
                if term_hits == 0:
                    continue
                full_text_score = float(term_hits)
            result = FullTextSearchResult(
                chunk_id=chunk.id,
                document_version_id=version.id,
                document_id=document.id,
                source_id=source.id,
                canonical_reference=chunk.reference or "",
                content=chunk.content,
                content_normalized=chunk.content_normalized,
                language=document.language,
                madhhab=document.madhhab,
                source_type=source.source_type,
                license_status=license_record.status,
                score_exact=exact_score,
                score_full_text=full_text_score,
                score_final=(exact_score or 0.0) + full_text_score,
                rank=0,
                metadata={
                    "source_language": source.language,
                    "reliability_level": source.reliability_level,
                    "chunking_strategy_version": chunk.chunking_strategy_version,
                    "database_backend": "postgresql" if supports_postgres else "sqlite",
                },
            )
            scored.append((result.score_final, exact_score, full_text_score, result))
        scored.sort(
            key=lambda item: (
                item[0],
                item[1] or 0.0,
                item[2],
                item[3].canonical_reference,
            ),
            reverse=True,
        )
        ranked: list[FullTextSearchResult] = []
        for rank, (_final, _exact, _full_text, result) in enumerate(scored, start=1):
            ranked.append(
                FullTextSearchResult(
                    chunk_id=result.chunk_id,
                    document_version_id=result.document_version_id,
                    document_id=result.document_id,
                    source_id=result.source_id,
                    canonical_reference=result.canonical_reference,
                    content=result.content,
                    content_normalized=result.content_normalized,
                    language=result.language,
                    madhhab=result.madhhab,
                    source_type=result.source_type,
                    license_status=result.license_status,
                    score_exact=result.score_exact,
                    score_full_text=result.score_full_text,
                    score_final=result.score_final,
                    rank=rank,
                    metadata=result.metadata,
                )
            )
        return ranked

    def postgres_search_statement(self, query: FullTextSearchQuery) -> Any:
        """Expose the intended PostgreSQL search statement for verification and docs."""
        normalized = normalize_text(query.text.strip(), language=query.language)
        ts_vector = func.to_tsvector("simple", DocumentChunk.content_normalized)
        ts_query = func.websearch_to_tsquery("simple", normalized.normalized)
        exact_match = cast(DocumentChunk.reference, Text) == literal(normalized.normalized)
        prefix_match = cast(DocumentChunk.reference, Text).ilike(f"{normalized.normalized}%")
        statement = (
            select(
                DocumentChunk.id.label("chunk_id"),
                func.ts_rank_cd(ts_vector, ts_query).label("score_full_text"),
                exact_match.label("score_exact"),
            )
            .select_from(DocumentChunk)
            .join(DocumentVersion, DocumentVersion.id == DocumentChunk.document_version_id)
            .join(Document, Document.id == DocumentVersion.document_id)
            .join(Source, Source.id == Document.source_id)
            .join(SourceLicense, SourceLicense.id == Document.source_license_id)
            .where(DocumentChunk.is_published.is_(True))
            .where(Document.review_status == DocumentStatus.PUBLISHED.value)
            .where(DocumentVersion.status == DocumentStatus.PUBLISHED.value)
            .where(SourceLicense.status.in_(_ELIGIBLE_LICENSE_STATUSES))
            .where(
                or_(
                    exact_match,
                    prefix_match,
                    ts_vector.op("@@")(ts_query),
                )
            )
        )
        return statement

    def _session(self) -> Any:
        if self.uow.session is None:
            raise RuntimeError("Database session not initialised in UoW.")
        return self.uow.session
