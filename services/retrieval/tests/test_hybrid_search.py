from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import (
    Base,
    Document,
    DocumentChunk,
    DocumentVersion,
    EmbeddingRecord,
    ModelConfiguration,
    Provider,
    RetrievalResult,
    RetrievalRun,
    Source,
    SourceLicense,
    User,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_service_retrieval.hybrid_search import (
    HYBRID_RETRIEVER_VERSION,
    HybridSearchError,
    HybridSearchQuery,
    HybridSearchService,
    HybridSearchWeights,
)


@pytest.fixture
def db() -> Any:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _seed_hybrid_data(session_factory: Any) -> dict[str, UUID]:
    user_id = uuid4()
    source_id = uuid4()
    license_id = uuid4()
    document_id = uuid4()
    version_id = uuid4()
    provider_id = uuid4()
    model_id = uuid4()
    exact_chunk_id = uuid4()
    vector_chunk_id = uuid4()
    hidden_chunk_id = uuid4()
    with session_factory() as session:
        session.add(
            User(
                id=user_id,
                email="hybrid@example.com",
                display_name="Hybrid User",
                status="active",
            )
        )
        session.add(
            Provider(
                id=provider_id,
                name="Local Embeddings",
                provider_type="embedding",
                status="enabled",
                data_policy_json={},
                created_by=user_id,
            )
        )
        session.add(
            ModelConfiguration(
                id=model_id,
                provider_id=provider_id,
                model_name="local-hash",
                model_type="embedding",
                configuration_json={"dimensions": 3, "revision": "2026-07"},
                status="enabled",
                created_by=user_id,
            )
        )
        session.add(
            Source(
                id=source_id,
                name="Hybrid Source",
                source_type="fiqh",
                language="th",
                reliability_level=5,
                is_active=True,
                created_by=user_id,
            )
        )
        session.add(
            SourceLicense(
                id=license_id,
                source_id=source_id,
                license_name="Allowed",
                license_version="2026-07",
                status="persistent_redistributable",
                storage_permission="allowed",
                embedding_permission="allowed",
                commercial_use="allowed",
                redistribution="allowed",
                valid_from=date(2026, 1, 1),
                valid_until=date(2026, 12, 31),
                created_by=user_id,
            )
        )
        session.add(
            Document(
                id=document_id,
                source_id=source_id,
                source_license_id=license_id,
                canonical_id="hybrid-book",
                document_type="fiqh",
                title="Hybrid Book",
                language="th",
                madhhab="shafii",
                review_status="published",
                published_version_id=version_id,
                created_by=user_id,
            )
        )
        session.add(
            DocumentVersion(
                id=version_id,
                document_id=document_id,
                version_number=1,
                status="published",
                content_hash="version-hash",
                extracted_text="ข้อความทดสอบ",
                metadata_json={},
                created_by=user_id,
                frozen_at=datetime.now(UTC),
            )
        )
        session.add_all(
            [
                DocumentChunk(
                    id=exact_chunk_id,
                    document_version_id=version_id,
                    chunk_index=0,
                    content="กฎละหมาดสำหรับผู้เดินทาง",
                    content_normalized="กฎละหมาดสำหรับผู้เดินทาง",
                    token_count=4,
                    section="Prayer",
                    reference="hybrid-book:v1:travel-prayer",
                    metadata_json={},
                    is_published=True,
                    chunking_strategy_version="fiqh-issue-v1",
                    content_hash="chunk-exact",
                ),
                DocumentChunk(
                    id=vector_chunk_id,
                    document_version_id=version_id,
                    chunk_index=1,
                    content="ละหมาดทั่วไปสำหรับผู้อยู่อาศัย",
                    content_normalized="ละหมาดทั่วไปสำหรับผู้อยู่อาศัย",
                    token_count=4,
                    section="Prayer",
                    reference="hybrid-book:v1:resident-prayer",
                    metadata_json={},
                    is_published=True,
                    chunking_strategy_version="fiqh-issue-v1",
                    content_hash="chunk-vector",
                ),
                DocumentChunk(
                    id=hidden_chunk_id,
                    document_version_id=version_id,
                    chunk_index=2,
                    content="ละหมาดร่างซ่อน",
                    content_normalized="ละหมาดร่างซ่อน",
                    token_count=3,
                    section="Hidden",
                    reference="hybrid-book:v1:hidden",
                    metadata_json={},
                    is_published=False,
                    chunking_strategy_version="fiqh-issue-v1",
                    content_hash="chunk-hidden",
                ),
            ]
        )
        session.add_all(
            [
                EmbeddingRecord(
                    id=uuid4(),
                    document_version_id=version_id,
                    chunk_id=exact_chunk_id,
                    model_configuration_id=model_id,
                    provider_id=provider_id,
                    embedding=[0.6, 0.2, 0.0],
                    embedding_hash="emb-exact",
                    dimension=3,
                    status="active",
                ),
                EmbeddingRecord(
                    id=uuid4(),
                    document_version_id=version_id,
                    chunk_id=vector_chunk_id,
                    model_configuration_id=model_id,
                    provider_id=provider_id,
                    embedding=[1.0, 0.0, 0.0],
                    embedding_hash="emb-vector",
                    dimension=3,
                    status="active",
                ),
                EmbeddingRecord(
                    id=uuid4(),
                    document_version_id=version_id,
                    chunk_id=hidden_chunk_id,
                    model_configuration_id=model_id,
                    provider_id=provider_id,
                    embedding=[1.0, 0.0, 0.0],
                    embedding_hash="emb-hidden",
                    dimension=3,
                    status="active",
                ),
            ]
        )
        session.commit()
    return {
        "model_id": model_id,
        "provider_id": provider_id,
        "license_id": license_id,
        "exact_chunk_id": exact_chunk_id,
        "vector_chunk_id": vector_chunk_id,
        "hidden_chunk_id": hidden_chunk_id,
    }


def test_hybrid_search_records_scores_and_trace(db: Any) -> None:
    ids = _seed_hybrid_data(db)
    service = HybridSearchService(SQLAlchemyUnitOfWork(db))

    response = service.search(
        HybridSearchQuery(
            text="hybrid-book:v1:travel-prayer",
            language="th",
            embedding=(1.0, 0.0, 0.0),
            model_configuration_id=ids["model_id"],
            provider_id=ids["provider_id"],
            request_id="hybrid-test-1",
            trace_id="trace-hybrid-1",
            weights=HybridSearchWeights(version="weights-test"),
        )
    )

    assert response.retriever_version == HYBRID_RETRIEVER_VERSION
    assert response.weights_version == "weights-test"
    assert response.retrieval_run_id is not None
    assert response.results[0].chunk_id == ids["exact_chunk_id"]
    assert response.results[0].score_exact == 1.0
    assert response.results[0].score_full_text == 1.0
    assert response.results[0].score_vector is not None
    assert response.results[0].metadata["hybrid_signal_sources"] == ["full_text", "vector"]

    with db() as session:
        run = session.scalar(select(RetrievalRun).where(RetrievalRun.request_id == "hybrid-test-1"))
        assert run is not None
        assert run.trace_id == "trace-hybrid-1"
        assert run.retriever_version == HYBRID_RETRIEVER_VERSION
        stored_results = session.scalars(
            select(RetrievalResult).order_by(RetrievalResult.rank.asc())
        ).all()
        assert len(stored_results) == len(response.results)
        assert stored_results[0].score_exact == response.results[0].score_exact
        assert stored_results[0].metadata_json["hybrid_weights_version"] == "weights-test"


def test_hybrid_search_weight_configuration_changes_ranking(db: Any) -> None:
    ids = _seed_hybrid_data(db)
    service = HybridSearchService(SQLAlchemyUnitOfWork(db))

    exact_weighted = service.search(
        HybridSearchQuery(
            text="hybrid-book:v1:travel-prayer",
            language="th",
            embedding=(1.0, 0.0, 0.0),
            model_configuration_id=ids["model_id"],
            weights=HybridSearchWeights(exact=1.0, full_text=0.0, vector=0.0, reliability=0.0),
            persist_run=False,
        )
    )
    vector_weighted = service.search(
        HybridSearchQuery(
            text="hybrid-book:v1:travel-prayer",
            language="th",
            embedding=(1.0, 0.0, 0.0),
            model_configuration_id=ids["model_id"],
            weights=HybridSearchWeights(exact=0.0, full_text=0.0, vector=1.0, reliability=0.0),
            persist_run=False,
        )
    )

    assert exact_weighted.results[0].chunk_id == ids["exact_chunk_id"]
    assert vector_weighted.results[0].chunk_id == ids["vector_chunk_id"]
    assert exact_weighted.weights["exact"] == 1.0
    assert vector_weighted.weights["vector"] == 1.0


def test_hybrid_search_is_deterministic_for_fixed_inputs(db: Any) -> None:
    ids = _seed_hybrid_data(db)
    service = HybridSearchService(SQLAlchemyUnitOfWork(db))
    query = HybridSearchQuery(
        text="ละหมาด",
        language="th",
        embedding=(1.0, 0.0, 0.0),
        model_configuration_id=ids["model_id"],
        persist_run=False,
    )

    first = service.search(query)
    second = service.search(query)

    assert [result.chunk_id for result in first.results] == [
        result.chunk_id for result in second.results
    ]
    assert [result.score_final for result in first.results] == [
        result.score_final for result in second.results
    ]


def test_hybrid_search_full_text_only_fallback(db: Any) -> None:
    ids = _seed_hybrid_data(db)
    service = HybridSearchService(SQLAlchemyUnitOfWork(db))

    response = service.search(
        HybridSearchQuery(
            text="ละหมาด",
            language="th",
            weights=HybridSearchWeights(exact=0.2, full_text=0.7, vector=0.1, reliability=0.0),
            persist_run=False,
        )
    )

    assert len(response.results) == 2
    assert all(result.score_vector is None for result in response.results)
    assert ids["hidden_chunk_id"] not in {result.chunk_id for result in response.results}


def test_hybrid_search_fails_closed_for_invalid_weights_or_vector_signal(db: Any) -> None:
    ids = _seed_hybrid_data(db)
    service = HybridSearchService(SQLAlchemyUnitOfWork(db))

    with pytest.raises(HybridSearchError) as weights_error:
        service.search(
            HybridSearchQuery(
                text="ละหมาด",
                language="th",
                weights=HybridSearchWeights(exact=0.0, full_text=0.0, vector=0.0, reliability=0.0),
            )
        )
    assert weights_error.value.code == "HYBRID_INVALID_WEIGHTS"

    with pytest.raises(HybridSearchError) as vector_error:
        service.search(
            HybridSearchQuery(
                text="ละหมาด",
                language="th",
                embedding=(1.0, 0.0, 0.0),
            )
        )
    assert vector_error.value.code == "HYBRID_VECTOR_SIGNAL_INCOMPLETE"

    with db() as session:
        license_record = session.get(SourceLicense, ids["license_id"])
        assert license_record is not None
        license_record.status = "prohibited"
        session.commit()
    response = service.search(
        HybridSearchQuery(
            text="ละหมาด",
            language="th",
            embedding=(1.0, 0.0, 0.0),
            model_configuration_id=ids["model_id"],
            persist_run=False,
        )
    )
    assert response.results == ()
