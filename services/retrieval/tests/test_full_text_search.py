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
    Source,
    SourceLicense,
    User,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_service_retrieval.full_text_search import (
    FULL_TEXT_REFERENCE_SCORE,
    FULL_TEXT_RETRIEVER_VERSION,
    FullTextSearchQuery,
    FullTextSearchService,
)


@pytest.fixture
def db() -> Any:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _seed_search_data(session_factory: Any) -> dict[str, UUID]:
    user_id = uuid4()
    source_id = uuid4()
    license_id = uuid4()
    document_id = uuid4()
    version_id = uuid4()
    with session_factory() as session:
        session.add(
            User(
                id=user_id,
                email="retrieval@example.com",
                display_name="Retrieval User",
                status="active",
            )
        )
        session.add(
            Source(
                id=source_id,
                name="Thai Fiqh Source",
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
                canonical_id="fiqh-book",
                document_type="fiqh",
                title="Thai Fiqh Book",
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
                    id=uuid4(),
                    document_version_id=version_id,
                    chunk_index=0,
                    content="กฎละหมาดสำหรับผู้เดินทาง",
                    content_normalized="กฎละหมาดสำหรับผู้เดินทาง",
                    token_count=4,
                    section="Prayer",
                    reference="fiqh-book:v1:travel-prayer",
                    metadata_json={},
                    is_published=True,
                    chunking_strategy_version="fiqh-issue-v1",
                    content_hash="chunk-a",
                ),
                DocumentChunk(
                    id=uuid4(),
                    document_version_id=version_id,
                    chunk_index=1,
                    content="حديث 42 الاعمال بالنيات",
                    content_normalized="حديث 42 الاعمال بالنيات",
                    token_count=4,
                    section="Hadith",
                    reference="fiqh-book:v1:hadith-42",
                    metadata_json={},
                    is_published=True,
                    chunking_strategy_version="hadith-record-v1",
                    content_hash="chunk-b",
                ),
                DocumentChunk(
                    id=uuid4(),
                    document_version_id=version_id,
                    chunk_index=2,
                    content="ร่างที่ยังไม่เผยแพร่",
                    content_normalized="ร่างที่ยังไม่เผยแพร่",
                    token_count=4,
                    section="Draft",
                    reference="fiqh-book:v1:draft-hidden",
                    metadata_json={},
                    is_published=False,
                    chunking_strategy_version="paragraph-v1",
                    content_hash="chunk-c",
                ),
            ]
        )
        session.commit()
    return {"document_id": document_id, "version_id": version_id, "license_id": license_id}


def test_full_text_search_exact_reference_is_deterministic(db: Any) -> None:
    _seed_search_data(db)
    service = FullTextSearchService(SQLAlchemyUnitOfWork(db))

    response = service.search(
        FullTextSearchQuery(
            text="fiqh-book:v1:travel-prayer",
            language="en",
            limit=5,
        )
    )

    assert response.retriever_version == FULL_TEXT_RETRIEVER_VERSION
    assert len(response.results) == 1
    assert response.results[0].canonical_reference == "fiqh-book:v1:travel-prayer"
    assert response.results[0].score_exact == FULL_TEXT_REFERENCE_SCORE
    assert response.results[0].rank == 1


def test_full_text_search_filters_published_chunks_and_metadata(db: Any) -> None:
    _seed_search_data(db)
    service = FullTextSearchService(SQLAlchemyUnitOfWork(db))

    response = service.search(
        FullTextSearchQuery(
            text="ละหมาด",
            language="th",
            madhhab="shafii",
            source_type="fiqh",
            source_language="th",
            license_status="persistent_redistributable",
        )
    )

    assert len(response.results) == 1
    assert response.results[0].content == "กฎละหมาดสำหรับผู้เดินทาง"
    assert response.results[0].metadata["database_backend"] == "sqlite"


def test_full_text_search_supports_arabic_content_queries(db: Any) -> None:
    _seed_search_data(db)
    service = FullTextSearchService(SQLAlchemyUnitOfWork(db))

    response = service.search(
        FullTextSearchQuery(
            text="الاعمال بالنيات",
            language="ar",
        )
    )

    assert len(response.results) == 1
    assert response.results[0].canonical_reference == "fiqh-book:v1:hadith-42"
    assert response.results[0].score_full_text > 0.0


def test_full_text_search_hides_ineligible_license_and_unpublished_content(db: Any) -> None:
    ids = _seed_search_data(db)
    with db() as session:
        license_record = session.get(SourceLicense, ids["license_id"])
        assert license_record is not None
        license_record.status = "prohibited"
        session.commit()

    service = FullTextSearchService(SQLAlchemyUnitOfWork(db))
    response = service.search(FullTextSearchQuery(text="ร่าง", language="th"))

    assert response.results == ()


def test_postgres_search_statement_contains_exact_and_tsvector_paths(db: Any) -> None:
    _seed_search_data(db)
    service = FullTextSearchService(SQLAlchemyUnitOfWork(db))

    statement = service.postgres_search_statement(
        FullTextSearchQuery(text="travel prayer", language="en")
    )
    compiled = str(statement)

    assert "to_tsvector" in compiled
    assert "websearch_to_tsquery" in compiled
    assert "document_chunks.reference" in compiled
