from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import (
    Base,
    Document,
    DocumentChunk,
    DocumentVersion,
    EmbeddingRecord,
    ModelConfiguration,
    Provider,
    Source,
    SourceLicense,
    User,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_service_retrieval.vector_search import (
    VECTOR_RETRIEVER_VERSION,
    VectorSearchError,
    VectorSearchQuery,
    VectorSearchService,
)


@pytest.fixture
def db() -> Any:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _seed_vector_data(session_factory: Any) -> dict[str, UUID]:
    user_id = uuid4()
    source_id = uuid4()
    license_id = uuid4()
    document_id = uuid4()
    version_id = uuid4()
    provider_id = uuid4()
    other_provider_id = uuid4()
    model_id = uuid4()
    other_model_id = uuid4()
    travel_chunk_id = uuid4()
    hidden_chunk_id = uuid4()
    hadith_chunk_id = uuid4()
    with session_factory() as session:
        session.add(
            User(
                id=user_id,
                email="vector@example.com",
                display_name="Vector User",
                status="active",
            )
        )
        session.add_all(
            [
                Provider(
                    id=provider_id,
                    name="Local Embeddings",
                    provider_type="embedding",
                    status="enabled",
                    data_policy_json={},
                    created_by=user_id,
                ),
                Provider(
                    id=other_provider_id,
                    name="Other Embeddings",
                    provider_type="embedding",
                    status="enabled",
                    data_policy_json={},
                    created_by=user_id,
                ),
            ]
        )
        session.add_all(
            [
                ModelConfiguration(
                    id=model_id,
                    provider_id=provider_id,
                    model_name="local-hash",
                    model_type="embedding",
                    configuration_json={"dimensions": 3, "revision": "2026-07"},
                    status="enabled",
                    created_by=user_id,
                ),
                ModelConfiguration(
                    id=other_model_id,
                    provider_id=other_provider_id,
                    model_name="other-hash",
                    model_type="embedding",
                    configuration_json={"dimensions": 3, "revision": "2026-07-other"},
                    status="enabled",
                    created_by=user_id,
                ),
            ]
        )
        session.add(
            Source(
                id=source_id,
                name="Thai Vector Source",
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
                canonical_id="vector-book",
                document_type="fiqh",
                title="Vector Book",
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
                    id=travel_chunk_id,
                    document_version_id=version_id,
                    chunk_index=0,
                    content="กฎละหมาดสำหรับผู้เดินทาง",
                    content_normalized="กฎละหมาดสำหรับผู้เดินทาง",
                    token_count=4,
                    section="Prayer",
                    reference="vector-book:v1:travel-prayer",
                    metadata_json={},
                    is_published=True,
                    chunking_strategy_version="fiqh-issue-v1",
                    content_hash="chunk-a",
                ),
                DocumentChunk(
                    id=hadith_chunk_id,
                    document_version_id=version_id,
                    chunk_index=1,
                    content="حديث 42 الاعمال بالنيات",
                    content_normalized="حديث 42 الاعمال بالنيات",
                    token_count=4,
                    section="Hadith",
                    reference="vector-book:v1:hadith-42",
                    metadata_json={},
                    is_published=True,
                    chunking_strategy_version="hadith-record-v1",
                    content_hash="chunk-b",
                ),
                DocumentChunk(
                    id=hidden_chunk_id,
                    document_version_id=version_id,
                    chunk_index=2,
                    content="ร่างที่ยังไม่เผยแพร่",
                    content_normalized="ร่างที่ยังไม่เผยแพร่",
                    token_count=4,
                    section="Draft",
                    reference="vector-book:v1:draft-hidden",
                    metadata_json={},
                    is_published=False,
                    chunking_strategy_version="paragraph-v1",
                    content_hash="chunk-c",
                ),
            ]
        )
        session.add_all(
            [
                EmbeddingRecord(
                    id=uuid4(),
                    document_version_id=version_id,
                    chunk_id=travel_chunk_id,
                    model_configuration_id=model_id,
                    provider_id=provider_id,
                    embedding=[0.9, 0.1, 0.0],
                    embedding_hash="emb-a",
                    dimension=3,
                    status="active",
                ),
                EmbeddingRecord(
                    id=uuid4(),
                    document_version_id=version_id,
                    chunk_id=hadith_chunk_id,
                    model_configuration_id=model_id,
                    provider_id=provider_id,
                    embedding=[0.1, 0.9, 0.0],
                    embedding_hash="emb-b",
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
                EmbeddingRecord(
                    id=uuid4(),
                    document_version_id=version_id,
                    chunk_id=travel_chunk_id,
                    model_configuration_id=other_model_id,
                    provider_id=other_provider_id,
                    embedding=[0.0, 0.0, 1.0],
                    embedding_hash="emb-other-space",
                    dimension=3,
                    status="active",
                ),
            ]
        )
        session.commit()
    return {
        "model_id": model_id,
        "other_model_id": other_model_id,
        "provider_id": provider_id,
        "other_provider_id": other_provider_id,
        "license_id": license_id,
        "travel_chunk_id": travel_chunk_id,
        "hidden_chunk_id": hidden_chunk_id,
    }


def test_vector_search_ranks_by_similarity_and_metadata(db: Any) -> None:
    ids = _seed_vector_data(db)
    service = VectorSearchService(SQLAlchemyUnitOfWork(db))

    response = service.search(
        VectorSearchQuery(
            embedding=(1.0, 0.0, 0.0),
            model_configuration_id=ids["model_id"],
            provider_id=ids["provider_id"],
            language="th",
            madhhab="shafii",
            source_type="fiqh",
            source_language="th",
            license_status="persistent_redistributable",
            reliability_level_min=4,
        )
    )

    assert response.retriever_version == VECTOR_RETRIEVER_VERSION
    assert response.embedding_space["model_configuration_id"] == str(ids["model_id"])
    assert len(response.results) == 2
    assert response.results[0].chunk_id == ids["travel_chunk_id"]
    assert response.results[0].rank == 1
    assert response.results[0].score_vector > response.results[1].score_vector
    assert response.results[0].metadata["database_backend"] == "sqlite"
    assert response.results[0].metadata["index_family"] == "hnsw"


def test_vector_search_never_mixes_embedding_spaces(db: Any) -> None:
    ids = _seed_vector_data(db)
    service = VectorSearchService(SQLAlchemyUnitOfWork(db))

    response = service.search(
        VectorSearchQuery(
            embedding=(0.0, 0.0, 1.0),
            model_configuration_id=ids["model_id"],
            provider_id=ids["provider_id"],
        )
    )

    assert all(result.model_configuration_id == ids["model_id"] for result in response.results)
    assert all(result.provider_id == ids["provider_id"] for result in response.results)
    assert {result.provider_id for result in response.results} == {ids["provider_id"]}


def test_vector_search_rejects_provider_and_dimension_mismatch(db: Any) -> None:
    ids = _seed_vector_data(db)
    service = VectorSearchService(SQLAlchemyUnitOfWork(db))

    with pytest.raises(VectorSearchError) as provider_error:
        service.search(
            VectorSearchQuery(
                embedding=(1.0, 0.0, 0.0),
                model_configuration_id=ids["model_id"],
                provider_id=ids["other_provider_id"],
            )
        )
    assert provider_error.value.code == "VECTOR_PROVIDER_MISMATCH"

    with pytest.raises(VectorSearchError) as dimension_error:
        service.search(
            VectorSearchQuery(
                embedding=(1.0, 0.0),
                model_configuration_id=ids["model_id"],
                provider_id=ids["provider_id"],
            )
        )
    assert dimension_error.value.code == "VECTOR_DIMENSION_MISMATCH"


def test_vector_search_hides_ineligible_license_and_unpublished_content(db: Any) -> None:
    ids = _seed_vector_data(db)
    with db() as session:
        license_record = session.get(SourceLicense, ids["license_id"])
        assert license_record is not None
        license_record.status = "prohibited"
        session.commit()

    service = VectorSearchService(SQLAlchemyUnitOfWork(db))
    response = service.search(
        VectorSearchQuery(
            embedding=(1.0, 0.0, 0.0),
            model_configuration_id=ids["model_id"],
        )
    )

    assert response.results == ()


def test_vector_search_timeout_validation_and_smoke_metadata(db: Any) -> None:
    ids = _seed_vector_data(db)
    service = VectorSearchService(SQLAlchemyUnitOfWork(db))

    with pytest.raises(VectorSearchError) as timeout_error:
        service.search(
            VectorSearchQuery(
                embedding=(1.0, 0.0, 0.0),
                model_configuration_id=ids["model_id"],
                timeout_ms=5_001,
            )
        )
    assert timeout_error.value.code == "VECTOR_INVALID_TIMEOUT"

    response = service.search(
        VectorSearchQuery(
            embedding=(1.0, 0.0, 0.0),
            model_configuration_id=ids["model_id"],
            timeout_ms=250,
        )
    )

    assert response.timeout_ms == 250
    assert response.results[0].metadata["timeout_ms"] == 250


def test_postgres_search_statement_contains_vector_operator_and_filters(db: Any) -> None:
    ids = _seed_vector_data(db)
    service = VectorSearchService(SQLAlchemyUnitOfWork(db))

    statement = service.postgres_search_statement(
        VectorSearchQuery(
            embedding=(1.0, 0.0, 0.0),
            model_configuration_id=ids["model_id"],
        )
    )
    compiled = str(statement)

    assert "<=>" in compiled
    assert "embedding_records.model_configuration_id" in compiled
    assert "embedding_records.status" in compiled
    assert "document_chunks.is_published" in compiled
    assert "documents.review_status" in compiled
    assert "source_licenses.embedding_permission" in compiled
