"""Filtered vector retrieval backed by pgvector in PostgreSQL."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import literal, select, text
from zayd_common.database.models import (
    Document,
    DocumentChunk,
    DocumentVersion,
    EmbeddingRecord,
    ModelConfiguration,
    Provider,
    Source,
    SourceLicense,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.enums import DocumentStatus, ProviderStatus

VECTOR_RETRIEVER_VERSION = "pgvector-retriever-v1"
DEFAULT_VECTOR_TIMEOUT_MS = 500
MAX_VECTOR_TIMEOUT_MS = 5_000

RetrievalLicenseStatus = Literal[
    "persistent_private",
    "persistent_redistributable",
]
_ELIGIBLE_LICENSE_STATUSES = frozenset({"persistent_private", "persistent_redistributable"})


class VectorSearchError(Exception):
    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class VectorSearchQuery:
    embedding: tuple[float, ...]
    model_configuration_id: UUID
    provider_id: UUID | None = None
    language: str | None = None
    madhhab: str | None = None
    source_type: str | None = None
    license_status: RetrievalLicenseStatus | None = None
    source_language: str | None = None
    reliability_level_min: int | None = None
    limit: int = 10
    offset: int = 0
    timeout_ms: int = DEFAULT_VECTOR_TIMEOUT_MS


@dataclass(frozen=True)
class VectorSearchResult:
    chunk_id: UUID
    document_version_id: UUID
    document_id: UUID
    source_id: UUID
    embedding_record_id: UUID
    model_configuration_id: UUID
    provider_id: UUID
    canonical_reference: str
    content: str
    content_normalized: str
    language: str
    madhhab: str
    source_type: str
    license_status: str
    score_vector: float
    score_final: float
    rank: int
    metadata: dict[str, object]


@dataclass(frozen=True)
class VectorSearchResponse:
    retriever_version: str
    embedding_space: dict[str, object]
    timeout_ms: int
    results: tuple[VectorSearchResult, ...]


class VectorSearchService:
    """Search only active embeddings in the requested embedding space."""

    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self.uow = uow

    def search(self, query: VectorSearchQuery) -> VectorSearchResponse:
        self._validate_query(query)
        with self.uow:
            session = self._session()
            model, provider = self._load_embedding_space(query)
            expected_dimension = self._expected_dimension(model)
            if expected_dimension is not None and expected_dimension != len(query.embedding):
                raise VectorSearchError(
                    "VECTOR_DIMENSION_MISMATCH",
                    "Query embedding dimension does not match the model configuration.",
                    status_code=400,
                )
            if session.bind is not None and session.bind.dialect.name == "postgresql":
                session.execute(
                    text("SET LOCAL statement_timeout = :timeout_ms"),
                    {"timeout_ms": query.timeout_ms},
                )

            supports_postgres = (
                session.bind is not None
                and session.bind.dialect.name == "postgresql"
            )
            if supports_postgres:
                rows = self._postgres_rows(
                    query=query,
                    expected_dimension=expected_dimension,
                    provider_id=provider.id,
                )
                paged = self._rank_postgres_rows(
                    rows,
                    timeout_ms=query.timeout_ms,
                    model=model,
                )
            else:
                statement = self._base_statement(
                    query=query,
                    expected_dimension=expected_dimension,
                    provider_id=provider.id,
                )
                rows = session.execute(statement).all()
                results = self._rank_rows(
                    rows,
                    query_embedding=query.embedding,
                    supports_postgres=supports_postgres,
                    timeout_ms=query.timeout_ms,
                    model=model,
                )
                paged = results[query.offset : query.offset + query.limit]
            self.uow.commit()
        return VectorSearchResponse(
            retriever_version=VECTOR_RETRIEVER_VERSION,
            embedding_space={
                "model_configuration_id": str(model.id),
                "provider_id": str(provider.id),
                "model_name": model.model_name,
                "model_revision": model.configuration_json.get("revision"),
                "dimension": len(query.embedding),
            },
            timeout_ms=query.timeout_ms,
            results=tuple(paged),
        )

    def _validate_query(self, query: VectorSearchQuery) -> None:
        if not query.embedding:
            raise VectorSearchError(
                "VECTOR_QUERY_REQUIRED",
                "Query embedding is required.",
                status_code=400,
            )
        if any(not isinstance(value, int | float) for value in query.embedding):
            raise VectorSearchError(
                "VECTOR_QUERY_INVALID",
                "Query embedding must contain only numeric values.",
                status_code=400,
            )
        if query.limit < 1 or query.limit > 100:
            raise VectorSearchError(
                "VECTOR_INVALID_LIMIT",
                "limit must be between 1 and 100.",
                status_code=400,
            )
        if query.offset < 0:
            raise VectorSearchError(
                "VECTOR_INVALID_OFFSET",
                "offset must be non-negative.",
                status_code=400,
            )
        if query.timeout_ms < 1 or query.timeout_ms > MAX_VECTOR_TIMEOUT_MS:
            raise VectorSearchError(
                "VECTOR_INVALID_TIMEOUT",
                f"timeout_ms must be between 1 and {MAX_VECTOR_TIMEOUT_MS}.",
                status_code=400,
            )
        if query.reliability_level_min is not None and (
            query.reliability_level_min < 1 or query.reliability_level_min > 5
        ):
            raise VectorSearchError(
                "VECTOR_INVALID_RELIABILITY",
                "reliability_level_min must be between 1 and 5.",
                status_code=400,
            )

    def _load_embedding_space(
        self, query: VectorSearchQuery
    ) -> tuple[ModelConfiguration, Provider]:
        session = self._session()
        row = session.execute(
            select(ModelConfiguration, Provider)
            .join(Provider, Provider.id == ModelConfiguration.provider_id)
            .where(ModelConfiguration.id == query.model_configuration_id)
            .where(ModelConfiguration.model_type == "embedding")
            .where(ModelConfiguration.status == ProviderStatus.ENABLED.value)
            .where(ModelConfiguration.deleted_at.is_(None))
            .where(Provider.provider_type == "embedding")
            .where(Provider.status == ProviderStatus.ENABLED.value)
            .where(Provider.deleted_at.is_(None))
        ).one_or_none()
        if row is None:
            raise VectorSearchError(
                "VECTOR_EMBEDDING_SPACE_UNAVAILABLE",
                "Embedding model configuration is not available for vector search.",
                status_code=404,
            )
        model, provider = row
        if query.provider_id is not None and query.provider_id != provider.id:
            raise VectorSearchError(
                "VECTOR_PROVIDER_MISMATCH",
                "Query provider does not match the model configuration provider.",
                status_code=400,
            )
        return model, provider

    def _base_statement(
        self,
        *,
        query: VectorSearchQuery,
        expected_dimension: int | None,
        provider_id: UUID,
    ) -> Any:
        statement = (
            select(
                EmbeddingRecord,
                DocumentChunk,
                DocumentVersion,
                Document,
                Source,
                SourceLicense,
            )
            .join(DocumentChunk, DocumentChunk.id == EmbeddingRecord.chunk_id)
            .join(DocumentVersion, DocumentVersion.id == EmbeddingRecord.document_version_id)
            .join(Document, Document.id == DocumentVersion.document_id)
            .join(Source, Source.id == Document.source_id)
            .join(SourceLicense, SourceLicense.id == Document.source_license_id)
            .where(EmbeddingRecord.model_configuration_id == query.model_configuration_id)
            .where(EmbeddingRecord.provider_id == provider_id)
            .where(EmbeddingRecord.status == "active")
            .where(EmbeddingRecord.dimension == len(query.embedding))
            .where(DocumentChunk.is_published.is_(True))
            .where(Document.review_status == DocumentStatus.PUBLISHED.value)
            .where(Document.published_version_id == DocumentVersion.id)
            .where(DocumentVersion.status == DocumentStatus.PUBLISHED.value)
            .where(DocumentVersion.frozen_at.is_not(None))
            .where(Source.is_active.is_(True))
            .where(Source.deleted_at.is_(None))
            .where(SourceLicense.status.in_(_ELIGIBLE_LICENSE_STATUSES))
            .where(SourceLicense.embedding_permission == "allowed")
        )
        if expected_dimension is not None:
            statement = statement.where(EmbeddingRecord.dimension == expected_dimension)
        if query.language is not None:
            statement = statement.where(Document.language == query.language.strip())
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
        return statement

    def _postgres_rows(
        self,
        *,
        query: VectorSearchQuery,
        expected_dimension: int | None,
        provider_id: UUID,
    ) -> list[Any]:
        params: dict[str, object] = {
            "query_embedding": _pgvector_literal(query.embedding),
            "model_configuration_id": query.model_configuration_id,
            "provider_id": provider_id,
            "dimension": expected_dimension or len(query.embedding),
            "limit": query.limit,
            "offset": query.offset,
        }
        optional_clauses: list[str] = []
        if query.language is not None:
            optional_clauses.append("AND d.language = :language")
            params["language"] = query.language.strip()
        if query.madhhab is not None:
            optional_clauses.append("AND d.madhhab = :madhhab")
            params["madhhab"] = query.madhhab.strip()
        if query.source_type is not None:
            optional_clauses.append("AND s.source_type = :source_type")
            params["source_type"] = query.source_type.strip()
        if query.license_status is not None:
            optional_clauses.append("AND sl.status = :license_status")
            params["license_status"] = query.license_status
        if query.source_language is not None:
            optional_clauses.append("AND s.language = :source_language")
            params["source_language"] = query.source_language.strip()
        if query.reliability_level_min is not None:
            optional_clauses.append("AND s.reliability_level >= :reliability_level_min")
            params["reliability_level_min"] = query.reliability_level_min

        sql = f"""
            SELECT
              er.id AS embedding_record_id,
              er.model_configuration_id AS model_configuration_id,
              er.provider_id AS provider_id,
              er.embedding_hash AS embedding_hash,
              er.dimension AS embedding_dimension,
              dc.id AS chunk_id,
              dc.reference AS canonical_reference,
              dc.content AS content,
              dc.content_normalized AS content_normalized,
              dc.chunking_strategy_version AS chunking_strategy_version,
              dv.id AS document_version_id,
              d.id AS document_id,
              d.language AS language,
              d.madhhab AS madhhab,
              s.id AS source_id,
              s.source_type AS source_type,
              s.language AS source_language,
              s.reliability_level AS reliability_level,
              sl.status AS license_status,
              1.0 - (er.embedding <=> CAST(:query_embedding AS vector)) AS score_vector
            FROM embedding_records er
            JOIN document_chunks dc ON dc.id = er.chunk_id
            JOIN document_versions dv ON dv.id = er.document_version_id
            JOIN documents d ON d.id = dv.document_id
            JOIN sources s ON s.id = d.source_id
            JOIN source_licenses sl ON sl.id = d.source_license_id
            WHERE er.model_configuration_id = :model_configuration_id
              AND er.provider_id = :provider_id
              AND er.status = 'active'
              AND er.dimension = :dimension
              AND dc.is_published = true
              AND d.review_status = 'published'
              AND d.published_version_id = dv.id
              AND d.deleted_at IS NULL
              AND dv.status = 'published'
              AND dv.frozen_at IS NOT NULL
              AND s.is_active = true
              AND s.deleted_at IS NULL
              AND sl.status IN ('persistent_private', 'persistent_redistributable')
              AND sl.embedding_permission = 'allowed'
              {" ".join(optional_clauses)}
            ORDER BY er.embedding <=> CAST(:query_embedding AS vector), dc.id
            LIMIT :limit OFFSET :offset
        """
        return list(self._session().execute(text(sql), params).mappings().all())

    def _rank_postgres_rows(
        self,
        rows: list[Any],
        *,
        timeout_ms: int,
        model: ModelConfiguration,
    ) -> list[VectorSearchResult]:
        ranked: list[VectorSearchResult] = []
        for rank, row in enumerate(rows, start=1):
            score_vector = float(row["score_vector"])
            ranked.append(
                VectorSearchResult(
                    chunk_id=row["chunk_id"],
                    document_version_id=row["document_version_id"],
                    document_id=row["document_id"],
                    source_id=row["source_id"],
                    embedding_record_id=row["embedding_record_id"],
                    model_configuration_id=row["model_configuration_id"],
                    provider_id=row["provider_id"],
                    canonical_reference=row["canonical_reference"] or "",
                    content=row["content"],
                    content_normalized=row["content_normalized"],
                    language=row["language"],
                    madhhab=row["madhhab"],
                    source_type=row["source_type"],
                    license_status=row["license_status"],
                    score_vector=score_vector,
                    score_final=score_vector,
                    rank=rank,
                    metadata={
                        "database_backend": "postgresql",
                        "distance_metric": "cosine",
                        "index_family": "hnsw",
                        "timeout_ms": timeout_ms,
                        "embedding_hash": row["embedding_hash"],
                        "embedding_dimension": row["embedding_dimension"],
                        "model_name": model.model_name,
                        "model_revision": model.configuration_json.get("revision"),
                        "chunking_strategy_version": row["chunking_strategy_version"],
                        "source_language": row["source_language"],
                        "reliability_level": row["reliability_level"],
                    },
                )
            )
        return ranked

    def _rank_rows(
        self,
        rows: list[
            tuple[
                EmbeddingRecord,
                DocumentChunk,
                DocumentVersion,
                Document,
                Source,
                SourceLicense,
            ]
        ],
        *,
        query_embedding: tuple[float, ...],
        supports_postgres: bool,
        timeout_ms: int,
        model: ModelConfiguration,
    ) -> list[VectorSearchResult]:
        scored: list[tuple[float, VectorSearchResult]] = []
        for embedding, chunk, version, document, source, license_record in rows:
            score_vector = _cosine_similarity(query_embedding, tuple(embedding.embedding))
            result = VectorSearchResult(
                chunk_id=chunk.id,
                document_version_id=version.id,
                document_id=document.id,
                source_id=source.id,
                embedding_record_id=embedding.id,
                model_configuration_id=embedding.model_configuration_id,
                provider_id=embedding.provider_id,
                canonical_reference=chunk.reference or "",
                content=chunk.content,
                content_normalized=chunk.content_normalized,
                language=document.language,
                madhhab=document.madhhab,
                source_type=source.source_type,
                license_status=license_record.status,
                score_vector=score_vector,
                score_final=score_vector,
                rank=0,
                metadata={
                    "database_backend": "postgresql" if supports_postgres else "sqlite",
                    "distance_metric": "cosine",
                    "index_family": "hnsw",
                    "timeout_ms": timeout_ms,
                    "embedding_hash": embedding.embedding_hash,
                    "embedding_dimension": embedding.dimension,
                    "model_name": model.model_name,
                    "model_revision": model.configuration_json.get("revision"),
                    "chunking_strategy_version": chunk.chunking_strategy_version,
                    "source_language": source.language,
                    "reliability_level": source.reliability_level,
                },
            )
            scored.append((result.score_final, result))
        scored.sort(
            key=lambda item: (
                item[0],
                item[1].canonical_reference,
                str(item[1].chunk_id),
            ),
            reverse=True,
        )
        ranked: list[VectorSearchResult] = []
        for rank, (_score, result) in enumerate(scored, start=1):
            ranked.append(
                VectorSearchResult(
                    chunk_id=result.chunk_id,
                    document_version_id=result.document_version_id,
                    document_id=result.document_id,
                    source_id=result.source_id,
                    embedding_record_id=result.embedding_record_id,
                    model_configuration_id=result.model_configuration_id,
                    provider_id=result.provider_id,
                    canonical_reference=result.canonical_reference,
                    content=result.content,
                    content_normalized=result.content_normalized,
                    language=result.language,
                    madhhab=result.madhhab,
                    source_type=result.source_type,
                    license_status=result.license_status,
                    score_vector=result.score_vector,
                    score_final=result.score_final,
                    rank=rank,
                    metadata=result.metadata,
                )
            )
        return ranked

    def postgres_search_statement(self, query: VectorSearchQuery) -> Any:
        """Expose the intended pgvector query shape for verification and docs."""
        self._validate_query(query)
        distance = EmbeddingRecord.embedding.op("<=>")(literal(_pgvector_literal(query.embedding)))
        statement = (
            select(
                EmbeddingRecord.id.label("embedding_record_id"),
                DocumentChunk.id.label("chunk_id"),
                (literal(1.0) - distance).label("score_vector"),
            )
            .select_from(EmbeddingRecord)
            .join(DocumentChunk, DocumentChunk.id == EmbeddingRecord.chunk_id)
            .join(DocumentVersion, DocumentVersion.id == EmbeddingRecord.document_version_id)
            .join(Document, Document.id == DocumentVersion.document_id)
            .join(Source, Source.id == Document.source_id)
            .join(SourceLicense, SourceLicense.id == Document.source_license_id)
            .where(EmbeddingRecord.model_configuration_id == query.model_configuration_id)
            .where(EmbeddingRecord.status == "active")
            .where(EmbeddingRecord.dimension == len(query.embedding))
            .where(DocumentChunk.is_published.is_(True))
            .where(Document.review_status == DocumentStatus.PUBLISHED.value)
            .where(Document.published_version_id == DocumentVersion.id)
            .where(DocumentVersion.status == DocumentStatus.PUBLISHED.value)
            .where(DocumentVersion.frozen_at.is_not(None))
            .where(Source.is_active.is_(True))
            .where(SourceLicense.status.in_(_ELIGIBLE_LICENSE_STATUSES))
            .where(SourceLicense.embedding_permission == "allowed")
            .order_by(distance.asc(), DocumentChunk.id.asc())
            .limit(query.limit)
        )
        return statement

    @staticmethod
    def _expected_dimension(model: ModelConfiguration) -> int | None:
        raw_value = model.configuration_json.get("dimensions")
        if raw_value is None:
            return None
        try:
            dimension = int(raw_value)
        except (TypeError, ValueError) as exc:
            raise VectorSearchError(
                "VECTOR_MODEL_DIMENSION_INVALID",
                "Embedding model configuration has an invalid dimension.",
                status_code=500,
            ) from exc
        if dimension < 1:
            raise VectorSearchError(
                "VECTOR_MODEL_DIMENSION_INVALID",
                "Embedding model configuration has an invalid dimension.",
                status_code=500,
            )
        return dimension

    def _session(self) -> Any:
        if self.uow.session is None:
            raise RuntimeError("Database session not initialised in UoW.")
        return self.uow.session


def _cosine_similarity(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    if len(left) != len(right):
        return 0.0
    dot_product = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot_product / (left_norm * right_norm)


def _pgvector_literal(vector: tuple[float, ...]) -> str:
    return "[" + ",".join(str(float(value)) for value in vector) + "]"
