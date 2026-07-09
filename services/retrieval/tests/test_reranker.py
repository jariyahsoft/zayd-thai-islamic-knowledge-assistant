from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import Base, RetrievalResult, RetrievalRun
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_service_retrieval.hybrid_search import HybridSearchResponse, HybridSearchResult
from zayd_service_retrieval.reranker import (
    LOCAL_RERANKER_VERSION,
    RERANKER_INTERFACE_VERSION,
    RerankerConfig,
    RerankerProviderInfo,
    RerankerService,
    RerankRequest,
    RerankScore,
)


def _hybrid_result(*, chunk_id, rank: int, content: str, score: float) -> HybridSearchResult:
    return HybridSearchResult(
        chunk_id=chunk_id,
        document_version_id=uuid4(),
        document_id=uuid4(),
        source_id=uuid4(),
        canonical_reference=f"ref:{rank}",
        content=content,
        content_normalized=content,
        language="th",
        madhhab="shafii",
        source_type="fiqh",
        license_status="persistent_redistributable",
        score_exact=None,
        score_full_text=score,
        score_vector=None,
        score_reliability=1.0,
        score_final=score,
        rank=rank,
        metadata={"hybrid_signal_sources": ["full_text"]},
    )


def _hybrid_response() -> HybridSearchResponse:
    first_id = uuid4()
    second_id = uuid4()
    return HybridSearchResponse(
        request_id="rerank-test",
        trace_id="trace-rerank",
        query_original="ละหมาด เดินทาง",
        query_normalized="ละหมาด เดินทาง",
        retriever_version="hybrid-retriever-v1",
        weights_version="hybrid-weights-v1",
        weights={"exact": 0.0, "full_text": 1.0, "vector": 0.0, "reliability": 0.0},
        retrieval_run_id=None,
        results=(
            _hybrid_result(
                chunk_id=first_id,
                rank=1,
                content="ละหมาด ทั่วไป",
                score=0.90,
            ),
            _hybrid_result(
                chunk_id=second_id,
                rank=2,
                content="ละหมาด เดินทาง ลดจำนวน",
                score=0.80,
            ),
        ),
    )


class FailingProvider:
    def provider_info(self) -> RerankerProviderInfo:
        return RerankerProviderInfo(
            provider_name="failing",
            provider_version="failing-v1",
            model_id="failing-model",
            model_revision="test",
            timeout_ms=100,
            max_candidates=10,
            supports_multilingual=True,
            data_sharing_allowed=True,
        )

    def rerank(self, request: RerankRequest) -> tuple[RerankScore, ...]:
        raise RuntimeError("provider unavailable")


class ExternalRestrictedProvider:
    def provider_info(self) -> RerankerProviderInfo:
        return RerankerProviderInfo(
            provider_name="external",
            provider_version="external-v1",
            model_id="external-model",
            model_revision="test",
            timeout_ms=100,
            max_candidates=10,
            supports_multilingual=True,
            data_sharing_allowed=False,
            is_external=True,
        )

    def rerank(self, request: RerankRequest) -> tuple[RerankScore, ...]:
        return ()


def test_local_reranker_contract_and_score_trace() -> None:
    response = _hybrid_response()
    service = RerankerService(config=RerankerConfig(timeout_ms=500, max_candidates=10))

    reranked = service.rerank(response)

    assert reranked.fallback_used is False
    assert reranked.provider_info is not None
    assert reranked.provider_info.interface_version == RERANKER_INTERFACE_VERSION
    assert reranked.provider_info.provider_version == LOCAL_RERANKER_VERSION
    assert reranked.results[0].hybrid_result.content == "ละหมาด เดินทาง ลดจำนวน"
    assert reranked.results[0].score_reranker == 1.0
    assert reranked.results[0].metadata["reranker_model_id"] == "local-keyword-overlap"


def test_reranker_failure_falls_back_to_hybrid_ranking() -> None:
    response = _hybrid_response()
    service = RerankerService(provider=FailingProvider())

    reranked = service.rerank(response)

    assert reranked.fallback_used is True
    assert reranked.fallback_reason == "provider_error"
    assert [result.hybrid_result.chunk_id for result in reranked.results] == [
        result.chunk_id for result in response.results
    ]
    assert all(result.score_reranker is None for result in reranked.results)


def test_reranker_disabled_falls_back_without_provider_call() -> None:
    response = _hybrid_response()
    service = RerankerService(provider=FailingProvider(), config=RerankerConfig(enabled=False))

    reranked = service.rerank(response)

    assert reranked.fallback_used is True
    assert reranked.fallback_reason == "disabled"
    assert reranked.provider_info is None


def test_external_data_sharing_restriction_blocks_provider() -> None:
    response = _hybrid_response()
    service = RerankerService(provider=ExternalRestrictedProvider())

    reranked = service.rerank(response)

    assert reranked.fallback_used is True
    assert reranked.fallback_reason == "provider_data_sharing_not_allowed"
    assert reranked.provider_info is not None
    assert reranked.provider_info.is_external is True
    assert reranked.provider_info.data_sharing_allowed is False


def test_reranker_preserves_hybrid_when_no_score_returned() -> None:
    response = _hybrid_response()
    empty_scores = RerankerProviderInfo(
        provider_name="empty",
        provider_version="empty-v1",
        model_id="empty-model",
        model_revision="test",
        timeout_ms=100,
        max_candidates=10,
        supports_multilingual=True,
        data_sharing_allowed=True,
    )

    class EmptyProvider:
        def provider_info(self) -> RerankerProviderInfo:
            return empty_scores

        def rerank(self, request: RerankRequest) -> tuple[RerankScore, ...]:
            return ()

    reranked = RerankerService(provider=EmptyProvider()).rerank(response)

    assert reranked.fallback_used is False
    assert [result.score_final for result in reranked.results] == [
        result.score_final for result in response.results
    ]


def test_reranker_persists_score_trace_when_run_exists() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)
    response = _hybrid_response()
    run_id = uuid4()
    stored_id = uuid4()
    with db() as session:
        session.add(
            RetrievalRun(
                id=run_id,
                request_id=response.request_id,
                trace_id=response.trace_id,
                query_original=response.query_original,
                query_normalized=response.query_normalized,
                query_expansions={},
                filters={},
                retriever_version=response.retriever_version,
                evidence_sufficient=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        session.add(
            RetrievalResult(
                id=stored_id,
                retrieval_run_id=run_id,
                document_version_id=response.results[0].document_version_id,
                chunk_id=response.results[0].chunk_id,
                rank=response.results[0].rank,
                score_exact=response.results[0].score_exact,
                score_full_text=response.results[0].score_full_text,
                score_vector=response.results[0].score_vector,
                score_reranker=None,
                score_final=response.results[0].score_final,
                metadata_json={},
            )
        )
        session.commit()

    response = HybridSearchResponse(
        request_id=response.request_id,
        trace_id=response.trace_id,
        query_original=response.query_original,
        query_normalized=response.query_normalized,
        retriever_version=response.retriever_version,
        weights_version=response.weights_version,
        weights=response.weights,
        retrieval_run_id=run_id,
        results=response.results,
    )
    reranked = RerankerService(SQLAlchemyUnitOfWork(db)).rerank(response)

    with db() as session:
        stored = session.scalar(select(RetrievalResult).where(RetrievalResult.id == stored_id))
        assert stored is not None
        matching = next(
            result
            for result in reranked.results
            if result.hybrid_result.chunk_id == stored.chunk_id
        )
        assert stored.score_reranker == matching.score_reranker
        assert stored.metadata_json["reranker_provider"] == "local-keyword-reranker"
        assert stored.metadata_json["reranker_interface_version"] == RERANKER_INTERFACE_VERSION
