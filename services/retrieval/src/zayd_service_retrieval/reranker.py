"""Reranker provider contract with safe fallback to hybrid ranking."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from zayd_common.database.models import RetrievalResult
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

from .hybrid_search import HybridSearchResponse, HybridSearchResult

RERANKER_INTERFACE_VERSION = "reranker-interface-v1"
LOCAL_RERANKER_VERSION = "local-keyword-reranker-v1"


class RerankerError(Exception):
    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class RerankerProviderInfo:
    provider_name: str
    provider_version: str
    model_id: str
    model_revision: str | None
    timeout_ms: int
    max_candidates: int
    supports_multilingual: bool
    data_sharing_allowed: bool
    is_external: bool = False
    interface_version: str = RERANKER_INTERFACE_VERSION


@dataclass(frozen=True)
class RerankCandidate:
    chunk_id: UUID
    rank: int
    text: str
    canonical_reference: str
    hybrid_score: float
    metadata: dict[str, object]


@dataclass(frozen=True)
class RerankRequest:
    query: str
    language: str
    candidates: tuple[RerankCandidate, ...]
    timeout_ms: int
    trace_id: str | None = None


@dataclass(frozen=True)
class RerankScore:
    chunk_id: UUID
    score: float
    metadata: dict[str, object]


class RerankerProvider(Protocol):
    def provider_info(self) -> RerankerProviderInfo:
        pass

    def rerank(self, request: RerankRequest) -> tuple[RerankScore, ...]:
        pass


@dataclass(frozen=True)
class RerankerConfig:
    enabled: bool = True
    timeout_ms: int = 500
    max_candidates: int = 25
    require_data_sharing_approval: bool = True


@dataclass(frozen=True)
class RerankedSearchResult:
    hybrid_result: HybridSearchResult
    score_reranker: float | None
    score_final: float
    rank: int
    metadata: dict[str, object]


@dataclass(frozen=True)
class RerankResponse:
    query_original: str
    retriever_version: str
    provider_info: RerankerProviderInfo | None
    fallback_used: bool
    fallback_reason: str | None
    results: tuple[RerankedSearchResult, ...]


class LocalKeywordRerankerProvider:
    """Deterministic local reranker used when no external provider is configured."""

    def __init__(
        self,
        *,
        provider_version: str = LOCAL_RERANKER_VERSION,
        model_revision: str | None = "2026-07",
        timeout_ms: int = 500,
        max_candidates: int = 25,
    ) -> None:
        self._info = RerankerProviderInfo(
            provider_name="local-keyword-reranker",
            provider_version=provider_version,
            model_id="local-keyword-overlap",
            model_revision=model_revision,
            timeout_ms=timeout_ms,
            max_candidates=max_candidates,
            supports_multilingual=True,
            data_sharing_allowed=True,
            is_external=False,
        )

    def provider_info(self) -> RerankerProviderInfo:
        return self._info

    def rerank(self, request: RerankRequest) -> tuple[RerankScore, ...]:
        query_terms = _terms(request.query)
        scores: list[RerankScore] = []
        for candidate in request.candidates:
            candidate_terms = _terms(candidate.text)
            overlap = len(query_terms & candidate_terms)
            denominator = max(1, len(query_terms))
            score = overlap / denominator
            scores.append(
                RerankScore(
                    chunk_id=candidate.chunk_id,
                    score=score,
                    metadata={
                        "overlap_terms": sorted(query_terms & candidate_terms),
                        "provider_version": self._info.provider_version,
                    },
                )
            )
        return tuple(scores)


class RerankerService:
    def __init__(
        self,
        uow: SQLAlchemyUnitOfWork | None = None,
        *,
        provider: RerankerProvider | None = None,
        config: RerankerConfig | None = None,
    ) -> None:
        self.uow = uow
        self.config = config or RerankerConfig()
        self.provider = provider or LocalKeywordRerankerProvider(
            timeout_ms=self.config.timeout_ms,
            max_candidates=self.config.max_candidates,
        )

    def rerank(self, response: HybridSearchResponse) -> RerankResponse:
        if not self.config.enabled:
            return self._fallback(response, reason="disabled")
        if self.config.timeout_ms < 1 or self.config.timeout_ms > 5_000:
            raise RerankerError(
                "RERANKER_INVALID_TIMEOUT",
                "Reranker timeout_ms must be between 1 and 5000.",
                status_code=400,
            )
        if self.config.max_candidates < 1 or self.config.max_candidates > 100:
            raise RerankerError(
                "RERANKER_INVALID_CANDIDATE_LIMIT",
                "Reranker max_candidates must be between 1 and 100.",
                status_code=400,
            )

        info = self.provider.provider_info()
        if (
            self.config.require_data_sharing_approval
            and info.is_external
            and not info.data_sharing_allowed
        ):
            return self._fallback(
                response,
                reason="provider_data_sharing_not_allowed",
                provider_info=info,
            )

        candidates = tuple(
            RerankCandidate(
                chunk_id=result.chunk_id,
                rank=result.rank,
                text=result.content,
                canonical_reference=result.canonical_reference,
                hybrid_score=result.score_final,
                metadata=result.metadata,
            )
            for result in response.results[: self.config.max_candidates]
        )
        try:
            started_at = perf_counter()
            scores = self.provider.rerank(
                RerankRequest(
                    query=response.query_original,
                    language=response.results[0].language if response.results else "unknown",
                    candidates=candidates,
                    timeout_ms=self.config.timeout_ms,
                    trace_id=response.trace_id,
                )
            )
            elapsed_ms = (perf_counter() - started_at) * 1000.0
        except Exception:
            return self._fallback(response, reason="provider_error", provider_info=info)
        if elapsed_ms > self.config.timeout_ms:
            return self._fallback(response, reason="provider_timeout", provider_info=info)

        score_by_chunk = {score.chunk_id: score for score in scores}
        reranked = self._rank(response, score_by_chunk=score_by_chunk, provider_info=info)
        if response.retrieval_run_id is not None and self.uow is not None:
            self._persist_scores(response.retrieval_run_id, reranked, provider_info=info)
        return RerankResponse(
            query_original=response.query_original,
            retriever_version=response.retriever_version,
            provider_info=info,
            fallback_used=False,
            fallback_reason=None,
            results=tuple(reranked),
        )

    def _rank(
        self,
        response: HybridSearchResponse,
        *,
        score_by_chunk: dict[UUID, RerankScore],
        provider_info: RerankerProviderInfo,
    ) -> list[RerankedSearchResult]:
        scored: list[tuple[float, float, HybridSearchResult, RerankedSearchResult]] = []
        for result in response.results:
            score = score_by_chunk.get(result.chunk_id)
            reranker_score = score.score if score is not None else None
            final_score = (
                (0.70 * result.score_final) + (0.30 * reranker_score)
                if reranker_score is not None
                else result.score_final
            )
            metadata = {
                **result.metadata,
                "reranker_provider": provider_info.provider_name,
                "reranker_model_id": provider_info.model_id,
                "reranker_model_revision": provider_info.model_revision,
                "reranker_provider_version": provider_info.provider_version,
                "reranker_interface_version": provider_info.interface_version,
                "reranker_score_metadata": score.metadata if score is not None else {},
            }
            reranked_result = RerankedSearchResult(
                hybrid_result=result,
                score_reranker=reranker_score,
                score_final=final_score,
                rank=0,
                metadata=metadata,
            )
            scored.append((final_score, reranker_score or 0.0, result, reranked_result))
        scored.sort(
            key=lambda item: (
                item[0],
                item[1],
                item[2].score_final,
                item[2].canonical_reference,
                str(item[2].chunk_id),
            ),
            reverse=True,
        )
        ranked: list[RerankedSearchResult] = []
        for rank, (_final, _reranker, _hybrid, reranked_result) in enumerate(scored, start=1):
            ranked.append(
                RerankedSearchResult(
                    hybrid_result=reranked_result.hybrid_result,
                    score_reranker=reranked_result.score_reranker,
                    score_final=reranked_result.score_final,
                    rank=rank,
                    metadata=reranked_result.metadata,
                )
            )
        return ranked

    def _fallback(
        self,
        response: HybridSearchResponse,
        *,
        reason: str,
        provider_info: RerankerProviderInfo | None = None,
    ) -> RerankResponse:
        results = tuple(
            RerankedSearchResult(
                hybrid_result=result,
                score_reranker=None,
                score_final=result.score_final,
                rank=result.rank,
                metadata={**result.metadata, "reranker_fallback_reason": reason},
            )
            for result in response.results
        )
        return RerankResponse(
            query_original=response.query_original,
            retriever_version=response.retriever_version,
            provider_info=provider_info,
            fallback_used=True,
            fallback_reason=reason,
            results=results,
        )

    def _persist_scores(
        self,
        retrieval_run_id: UUID,
        results: list[RerankedSearchResult],
        *,
        provider_info: RerankerProviderInfo,
    ) -> None:
        if self.uow is None:
            return
        with self.uow:
            session = self.uow.session
            if session is None:
                raise RuntimeError("Database session not initialised in UoW.")
            existing = session.scalars(
                select(RetrievalResult).where(RetrievalResult.retrieval_run_id == retrieval_run_id)
            ).all()
            by_chunk = {result.chunk_id: result for result in existing}
            for result in results:
                stored = by_chunk.get(result.hybrid_result.chunk_id)
                if stored is None:
                    continue
                stored.rank = result.rank
                stored.score_reranker = result.score_reranker
                stored.score_final = result.score_final
                stored.metadata_json = {
                    **stored.metadata_json,
                    "reranker_provider": provider_info.provider_name,
                    "reranker_provider_version": provider_info.provider_version,
                    "reranker_model_id": provider_info.model_id,
                    "reranker_model_revision": provider_info.model_revision,
                    "reranker_interface_version": provider_info.interface_version,
                }
            self.uow.commit()


def _terms(text: str) -> set[str]:
    return {term.casefold() for term in text.replace(":", " ").replace("-", " ").split() if term}
