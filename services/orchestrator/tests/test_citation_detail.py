from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
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
from zayd_service_orchestrator.citation_registry import (
    CitationRegistrationRequest,
    CitationRegistryError,
    CitationRegistryService,
    CitationType,
)


@pytest.fixture
def registry_fixture():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    actor_id = uuid4()
    source_id = uuid4()
    license_id = uuid4()
    document_id = uuid4()
    version_id = uuid4()
    chunk_id = uuid4()

    with session_factory() as session:
        session.add(
            User(
                id=actor_id,
                email="detail@example.test",
                display_name="Detail Reviewer",
            )
        )
        session.add(
            Source(
                id=source_id,
                name="Reviewed Source",
                source_type="fiqh",
                language="th",
                reliability_level=5,
                created_by=actor_id,
            )
        )
        session.add(
            SourceLicense(
                id=license_id,
                source_id=source_id,
                license_name="Reviewed License",
                status="persistent_redistributable",
                storage_permission="allowed",
                embedding_permission="allowed",
                commercial_use="allowed",
                redistribution="allowed",
                created_by=actor_id,
            )
        )
        session.add(
            Document(
                id=document_id,
                source_id=source_id,
                source_license_id=license_id,
                canonical_id="doc:reviewed",
                document_type="book",
                title="Reviewed Book",
                language="th",
                review_status="approved",
                created_by=actor_id,
            )
        )
        session.add(
            DocumentVersion(
                id=version_id,
                document_id=document_id,
                version_number=1,
                status="published",
                content_hash="version-hash",
                metadata_json={},
                created_by=actor_id,
            )
        )
        session.add(
            DocumentChunk(
                id=chunk_id,
                document_version_id=version_id,
                chunk_index=0,
                content="reviewed citation content",
                content_normalized="reviewed citation content",
                token_count=3,
                reference="book:1:10",
                metadata_json={"citation": {"canonical_reference": "book:1:10", "page": "10"}},
                is_published=True,
                chunking_strategy_version="test-v1",
                content_hash="chunk-hash-0",
            )
        )
        session.commit()

    service = CitationRegistryService(SQLAlchemyUnitOfWork(session_factory))
    return {
        "service": service,
        "session_factory": session_factory,
        "actor_id": actor_id,
        "version_id": version_id,
        "chunk_id": chunk_id,
    }


def _request(fixture, **overrides) -> CitationRegistrationRequest:
    return CitationRegistrationRequest(
        document_version_id=overrides.get("document_version_id", fixture["version_id"]),
        chunk_id=overrides.get("chunk_id", fixture["chunk_id"]),
        citation_type=overrides.get("citation_type", CitationType.BOOK),
        canonical_reference=overrides.get("canonical_reference", "book:1:10"),
        display_title=overrides.get("display_title", "Reviewed Book, vol. 1, p. 10"),
        actor_user_id=fixture["actor_id"],
        arabic_text=overrides.get("arabic_text"),
        thai_translation=overrides.get("thai_translation"),
        hadith_grade=overrides.get("hadith_grade"),
        volume=overrides.get("volume", "1"),
        page=overrides.get("page", "10"),
        trace_id="trace-citation-detail",
    )


def test_get_citation_detail_returns_source_text_and_metadata(registry_fixture) -> None:
    registered = registry_fixture["service"].register_citation(
        _request(
            registry_fixture,
            canonical_reference="quran:1:1",
            citation_type=CitationType.QURAN,
            display_title="Al-Fatihah 1:1",
            arabic_text="بِسْمِ اللَّهِ",
            thai_translation="ด้วยพระนามของอัลลอฮฺ",
        )
    )

    detail = registry_fixture["service"].get_citation_detail(registered.citation.id)

    assert detail.citation.id == registered.citation.id
    assert detail.source_text == "reviewed citation content"
    assert detail.source is not None
    assert detail.document is not None
    assert detail.document.title == "Reviewed Book"
    assert detail.warnings == ()


def test_get_citation_detail_warns_for_invalidated_citation(registry_fixture) -> None:
    registered = registry_fixture["service"].register_citation(_request(registry_fixture))
    registry_fixture["service"].invalidate_citation(
        citation_id=registered.citation.id,
        reason="reviewer flagged stale evidence",
        actor_user_id=registry_fixture["actor_id"],
    )

    detail = registry_fixture["service"].get_citation_detail(registered.citation.id)

    assert detail.citation.active is False
    assert "citation_invalidated" in detail.warnings


def test_get_citation_detail_warns_for_suspended_source(registry_fixture) -> None:
    registered = registry_fixture["service"].register_citation(_request(registry_fixture))
    with registry_fixture["session_factory"]() as session:
        source = session.scalars(select(Source)).first()
        assert source is not None
        source.is_active = False
        session.commit()

    detail = registry_fixture["service"].get_citation_detail(registered.citation.id)
    assert "source_suspended" in detail.warnings


def test_get_citation_detail_missing_citation_raises(registry_fixture) -> None:
    with pytest.raises(CitationRegistryError, match="not registered"):
        registry_fixture["service"].get_citation_detail(uuid4())