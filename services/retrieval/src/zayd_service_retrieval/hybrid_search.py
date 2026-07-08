"""Hybrid retrieval that combines full-text, vector, and reliability signals."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID, uuid4

from zayd_common.database.models import RetrievalResult, RetrievalRun
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.normalization import NORMALIZATION_FRAMEWORK_VERSION, normalize_text

from .full_text_search import (
    FullTextSearchQuery,
    FullTextSearchResult,
    FullTextSearchService,
)
from .vector_search import (
    VectorSearchQuery,
    VectorSearchResult,
    VectorSearchService,
)

HYBRID_RETRIEVER_VERSION = "hybrid-retriever-v1"
DEFAULT_HYBRID_WEIGHTS_VERSION = "hybrid-weights-v1"

RetrievalLicenseStatus = Literal[
    "persistent_private",
    "persistent_redistributable",
]


class HybridSearchError(Exception):
    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class HybridSearchWeights:
    exact: float = 0.35
    full_text: float = 0.25
    vector: float = 0.30
    reliability: float = 0.10
    version: str = DEFAULT_HYBRID_WEIGHTS_VERSION

    def normalized(self) -> HybridSearchWeights:
        values = (self.exact, self.full_text, self.vector, self.reliability)
        if any(value < 0.0 for value in values):
            raise HybridSearchError(
                "HYBRID_INVALID_WEIGHTS",
                "Hybrid search weights must be non-negative.",
                status_code=400,
            )
        total = sum(values)
        if total <= 0.0:
            raise HybridSearchError(
                "HYBRID_INVALID_WEIGHTS",
                "At least one hybrid search weight must be greater than zero.",
                status_code=400,
            )
        if not self.version.strip():
            raise HybridSearchError(
                "HYBRID_INVALID_WEIGHTS_VERSION",
                "Hybrid search weights version is required.",
                status_code=400,
            )
        return HybridSearchWeights(
            exact=self.exact / total,
            full_text=self.full_text / total,
            vector=self.vector / total,
            reliability=self.reliability / total,
            version=self.version.strip(),
        )


@dataclass(frozen=True)
class HybridSearchQuery:
    text: str
    language: str
    embedding: tuple[float, ...] | None = None
    model_configuration_id: UUID | None = None
    provider_id: UUID | None = None
    madhhab: str | None = None
    source_type: str | None = None
    license_status: RetrievalLicenseStatus | None = None
    source_language: str | None = None
    reliability_level_min: int | None = None
    limit: int = 10
    offset: int = 0
    vector_timeout_ms: int = 500
    request_id: str | None = None
    trace_id: str | None = None
    weights: HybridSearchWeights = field(default_factory=HybridSearchWeights)
    persist_run: bool = True


@dataclass(frozen=True)
class HybridSearchResult:
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
    score_full_text: float | None
    score_vector: float | None
    score_reliability: float
    score_final: float
    rank: int
    metadata: dict[str, object]


@dataclass(frozen=True)
class HybridSearchResponse:
    request_id: str
    trace_id: str | None
    query_original: str
    query_normalized: str
    retriever_version: str
    weights_version: str
    weights: dict[str, float]
    retrieval_run_id: UUID | None
    results: tuple[HybridSearchResult, ...]


@dataclass
class _Candidate:
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
    score_exact_raw: float | None = None
    score_full_text_raw: float | None = None
    score_vector_raw: float | None = None
    score_reliability: float = 0.0
    sources: set[str] = field(default_factory=set)
    metadata: dict[str, object] = field(default_factory=dict)


class HybridSearchService:
    def __init__(
        self,
        uow: SQLAlchemyUnitOfWork,
        *,
        full_text_service: FullTextSearchService | None = None,
        vector_service: VectorSearchService | None = None,
    ) -> None:
        self.uow = uow
        self.full_text_service = full_text_service or FullTextSearchService(uow)
        self.vector_service = vector_service or VectorSearchService(uow)

    def search(self, query: HybridSearchQuery) -> HybridSearchResponse:
        self._validate_query(query)
        weights = query.weights.normalized()
        normalized = normalize_text(query.text.strip(), language=query.language)
        candidates: dict[UUID, _Candidate] = {}

        full_text_response = self.full_text_service.search(
            FullTextSearchQuery(
                text=query.text,
                language=query.language,
                madhhab=query.madhhab,
                source_type=query.source_type,
                license_status=query.license_status,
                source_language=query.source_language,
                reliability_level_min=query.reliability_level_min,
                limit=100,
                offset=0,
            )
        )
        for result in full_text_response.results:
            self._merge_full_text(candidates, result)

        vector_response = None
        if query.embedding is not None and query.model_configuration_id is not None:
            vector_response = self.vector_service.search(
                VectorSearchQuery(
                    embedding=query.embedding,
                    model_configuration_id=query.model_configuration_id,
                    provider_id=query.provider_id,
                    language=query.language,
                    madhhab=query.madhhab,
                    source_type=query.source_type,
                    license_status=query.license_status,
                    source_language=query.source_language,
                    reliability_level_min=query.reliability_level_min,
                    limit=100,
                    offset=0,
                    timeout_ms=query.vector_timeout_ms,
                )
            )
            for vector_result in vector_response.results:
                self._merge_vector(candidates, vector_result)

        ranked = self._rank_candidates(candidates, weights)
        paged = ranked[query.offset : query.offset + query.limit]
        request_id = query.request_id or f"hybrid-{uuid4()}"
        retrieval_run_id = (
            self._persist_run(
                query=query,
                request_id=request_id,
                normalized_query=normalized.normalized,
                weights=weights,
                results=paged,
                vector_metadata=vector_response.embedding_space if vector_response else None,
            )
            if query.persist_run
            else None
        )
        return HybridSearchResponse(
            request_id=request_id,
            trace_id=query.trace_id,
            query_original=query.text,
            query_normalized=normalized.normalized,
            retriever_version=HYBRID_RETRIEVER_VERSION,
            weights_version=weights.version,
            weights={
                "exact": weights.exact,
                "full_text": weights.full_text,
                "vector": weights.vector,
                "reliability": weights.reliability,
            },
            retrieval_run_id=retrieval_run_id,
            results=tuple(paged),
        )

    def _validate_query(self, query: HybridSearchQuery) -> None:
        if not query.text.strip():
            raise HybridSearchError(
                "HYBRID_QUERY_REQUIRED",
                "Hybrid search text is required.",
                status_code=400,
            )
        if query.limit < 1 or query.limit > 100:
            raise HybridSearchError(
                "HYBRID_INVALID_LIMIT",
                "limit must be between 1 and 100.",
                status_code=400,
            )
        if query.offset < 0:
            raise HybridSearchError(
                "HYBRID_INVALID_OFFSET",
                "offset must be non-negative.",
                status_code=400,
            )
        has_embedding = query.embedding is not None
        has_model = query.model_configuration_id is not None
        if has_embedding != has_model:
            raise HybridSearchError(
                "HYBRID_VECTOR_SIGNAL_INCOMPLETE",
                "Vector signal requires both embedding and model_configuration_id.",
                status_code=400,
            )

    def _merge_full_text(
        self,
        candidates: dict[UUID, _Candidate],
        result: FullTextSearchResult,
    ) -> None:
        candidate = candidates.setdefault(result.chunk_id, self._candidate_from_full_text(result))
        candidate.score_exact_raw = result.score_exact
        candidate.score_full_text_raw = result.score_full_text
        candidate.score_reliability = _reliability_score(result.metadata)
        candidate.sources.add("full_text")
        candidate.metadata.update(
            {
                "full_text_rank": result.rank,
                "full_text_backend": result.metadata.get("database_backend"),
                "chunking_strategy_version": result.metadata.get("chunking_strategy_version"),
                "source_language": result.metadata.get("source_language"),
                "reliability_level": result.metadata.get("reliability_level"),
            }
        )

    def _merge_vector(
        self,
        candidates: dict[UUID, _Candidate],
        result: VectorSearchResult,
    ) -> None:
        candidate = candidates.setdefault(result.chunk_id, self._candidate_from_vector(result))
        candidate.score_vector_raw = result.score_vector
        candidate.score_reliability = _reliability_score(result.metadata)
        candidate.sources.add("vector")
        candidate.metadata.update(
            {
                "vector_rank": result.rank,
                "vector_backend": result.metadata.get("database_backend"),
                "embedding_record_id": str(result.embedding_record_id),
                "model_configuration_id": str(result.model_configuration_id),
                "provider_id": str(result.provider_id),
                "distance_metric": result.metadata.get("distance_metric"),
                "index_family": result.metadata.get("index_family"),
                "chunking_strategy_version": result.metadata.get("chunking_strategy_version"),
                "source_language": result.metadata.get("source_language"),
                "reliability_level": result.metadata.get("reliability_level"),
            }
        )

    def _rank_candidates(
        self,
        candidates: dict[UUID, _Candidate],
        weights: HybridSearchWeights,
    ) -> list[HybridSearchResult]:
        max_exact = max(
            (candidate.score_exact_raw or 0.0 for candidate in candidates.values()),
            default=0.0,
        )
        max_full_text = max(
            (candidate.score_full_text_raw or 0.0 for candidate in candidates.values()),
            default=0.0,
        )
        scored: list[tuple[float, float, float, float, HybridSearchResult]] = []
        for candidate in candidates.values():
            exact = _normalize_positive(candidate.score_exact_raw, max_exact)
            full_text = _normalize_positive(candidate.score_full_text_raw, max_full_text)
            vector = _normalize_vector(candidate.score_vector_raw)
            reliability = candidate.score_reliability
            score_final = (
                weights.exact * exact
                + weights.full_text * full_text
                + weights.vector * vector
                + weights.reliability * reliability
            )
            result = HybridSearchResult(
                chunk_id=candidate.chunk_id,
                document_version_id=candidate.document_version_id,
                document_id=candidate.document_id,
                source_id=candidate.source_id,
                canonical_reference=candidate.canonical_reference,
                content=candidate.content,
                content_normalized=candidate.content_normalized,
                language=candidate.language,
                madhhab=candidate.madhhab,
                source_type=candidate.source_type,
                license_status=candidate.license_status,
                score_exact=exact if candidate.score_exact_raw is not None else None,
                score_full_text=full_text if candidate.score_full_text_raw is not None else None,
                score_vector=vector if candidate.score_vector_raw is not None else None,
                score_reliability=reliability,
                score_final=score_final,
                rank=0,
                metadata={
                    **candidate.metadata,
                    "hybrid_signal_sources": sorted(candidate.sources),
                    "score_exact_raw": candidate.score_exact_raw,
                    "score_full_text_raw": candidate.score_full_text_raw,
                    "score_vector_raw": candidate.score_vector_raw,
                },
            )
            scored.append((score_final, exact, full_text, vector, result))
        scored.sort(
            key=lambda item: (
                item[0],
                item[1],
                item[2],
                item[3],
                item[4].canonical_reference,
                str(item[4].chunk_id),
            ),
            reverse=True,
        )
        ranked: list[HybridSearchResult] = []
        for rank, (_final, _exact, _full_text, _vector, result) in enumerate(scored, start=1):
            ranked.append(
                HybridSearchResult(
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
                    score_vector=result.score_vector,
                    score_reliability=result.score_reliability,
                    score_final=result.score_final,
                    rank=rank,
                    metadata=result.metadata,
                )
            )
        return ranked

    def _persist_run(
        self,
        *,
        query: HybridSearchQuery,
        request_id: str,
        normalized_query: str,
        weights: HybridSearchWeights,
        results: list[HybridSearchResult],
        vector_metadata: dict[str, object] | None,
    ) -> UUID:
        run_id = uuid4()
        with self.uow:
            session = self.uow.session
            if session is None:
                raise RuntimeError("Database session not initialised in UoW.")
            run = RetrievalRun(
                id=run_id,
                request_id=request_id,
                trace_id=query.trace_id,
                query_original=query.text,
                query_normalized=normalized_query,
                query_expansions={},
                filters={
                    "language": query.language,
                    "madhhab": query.madhhab,
                    "source_type": query.source_type,
                    "license_status": query.license_status,
                    "source_language": query.source_language,
                    "reliability_level_min": query.reliability_level_min,
                },
                retriever_version=HYBRID_RETRIEVER_VERSION,
                evidence_sufficient=bool(results),
            )
            session.add(run)
            for result in results:
                session.add(
                    RetrievalResult(
                        retrieval_run_id=run_id,
                        document_version_id=result.document_version_id,
                        chunk_id=result.chunk_id,
                        rank=result.rank,
                        score_exact=result.score_exact,
                        score_full_text=result.score_full_text,
                        score_vector=result.score_vector,
                        score_reranker=None,
                        score_final=result.score_final,
                        metadata_json={
                            **result.metadata,
                            "hybrid_weights_version": weights.version,
                            "hybrid_weights": {
                                "exact": weights.exact,
                                "full_text": weights.full_text,
                                "vector": weights.vector,
                                "reliability": weights.reliability,
                            },
                            "normalization_framework_version": NORMALIZATION_FRAMEWORK_VERSION,
                            "vector_embedding_space": vector_metadata,
                        },
                    )
                )
            self.uow.commit()
        return run_id

    @staticmethod
    def _candidate_from_full_text(result: FullTextSearchResult) -> _Candidate:
        return _Candidate(
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
        )

    @staticmethod
    def _candidate_from_vector(result: VectorSearchResult) -> _Candidate:
        return _Candidate(
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
        )


def _normalize_positive(value: float | None, maximum: float) -> float:
    if value is None or value <= 0.0 or maximum <= 0.0:
        return 0.0
    return min(1.0, value / maximum)


def _normalize_vector(value: float | None) -> float:
    if value is None:
        return 0.0
    return max(0.0, min(1.0, (value + 1.0) / 2.0))


def _reliability_score(metadata: dict[str, object]) -> float:
    raw_value = metadata.get("reliability_level", 1)
    if isinstance(raw_value, int | float | str | bytes | bytearray):
        try:
            reliability = int(raw_value)
        except (TypeError, ValueError):
            reliability = 1
    else:
        reliability = 1
    return float(max(0.0, min(1.0, reliability / 5.0)))
