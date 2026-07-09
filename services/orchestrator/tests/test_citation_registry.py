from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import (
    Answer,
    AuditLog,
    Base,
    Citation,
    Document,
    DocumentChunk,
    DocumentVersion,
    RetrievalResult,
    RetrievalRun,
    Source,
    SourceLicense,
    User,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_service_orchestrator.citation_registry import (
    CITATION_REGISTRY_VERSION,
    CitationRegistrationRequest,
    CitationRegistryError,
    CitationRegistryService,
    CitationType,
    citation_token,
)


@dataclass(frozen=True)
class RegistryFixture:
    session_factory: sessionmaker[Any]
    actor_id: UUID
    version_id: UUID
    chunk_id: UUID

    @property
    def service(self) -> CitationRegistryService:
        return CitationRegistryService(SQLAlchemyUnitOfWork(self.session_factory))


@pytest.fixture
def registry_fixture() -> RegistryFixture:
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
                email="reviewer@example.test",
                display_name="Reviewer",
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

    return RegistryFixture(
        session_factory=session_factory,
        actor_id=actor_id,
        version_id=version_id,
        chunk_id=chunk_id,
    )


def _request(
    fixture: RegistryFixture,
    *,
    canonical_reference: str = "book:1:10",
    citation_type: CitationType | str = CitationType.BOOK,
    chunk_id: UUID | None = None,
    document_version_id: UUID | None = None,
    display_title: str = "Reviewed Book, vol. 1, p. 10",
    arabic_text: str | None = None,
    thai_translation: str | None = None,
    hadith_grade: str | None = None,
    volume: str | None = None,
    page: str | None = None,
) -> CitationRegistrationRequest:
    return CitationRegistrationRequest(
        document_version_id=document_version_id or fixture.version_id,
        chunk_id=chunk_id or fixture.chunk_id,
        citation_type=citation_type,
        canonical_reference=canonical_reference,
        display_title=display_title,
        actor_user_id=fixture.actor_id,
        arabic_text=arabic_text,
        thai_translation=thai_translation,
        hadith_grade=hadith_grade,
        volume=volume,
        page=page,
        trace_id="trace-citation-test",
    )


def test_registers_stable_canonical_id_and_is_idempotent(
    registry_fixture: RegistryFixture,
) -> None:
    first = registry_fixture.service.register_citation(
        _request(registry_fixture, volume="1", page="10")
    )
    second = registry_fixture.service.register_citation(
        _request(registry_fixture, volume="1", page="10")
    )

    assert first.citation.id == second.citation.id
    assert first.citation.token == citation_token(first.citation.id)
    assert first.idempotent is False
    assert second.idempotent is True
    assert first.citation.registry_version == CITATION_REGISTRY_VERSION
    assert first.citation.active is True
    assert first.trace["citation_token"] == first.citation.token

    with registry_fixture.session_factory() as session:
        citations = session.scalars(select(Citation)).all()
        audits = session.scalars(select(AuditLog)).all()

    assert len(citations) == 1
    assert len(audits) == 1
    assert audits[0].action == "citations.register"
    assert audits[0].after_summary is not None
    assert audits[0].after_summary["registry_version"] == CITATION_REGISTRY_VERSION


def test_citation_type_schema_validation(registry_fixture: RegistryFixture) -> None:
    quran = registry_fixture.service.register_citation(
        _request(
            registry_fixture,
            canonical_reference="quran:1:1",
            citation_type=CitationType.QURAN,
            display_title="Quran citation",
            arabic_text="الحمد لله",
        )
    )
    hadith = registry_fixture.service.register_citation(
        _request(
            registry_fixture,
            canonical_reference="hadith:bukhari:1",
            citation_type=CitationType.HADITH,
            display_title="Hadith citation",
            hadith_grade="sahih",
        )
    )
    book = registry_fixture.service.register_citation(
        _request(
            registry_fixture,
            canonical_reference="book:valid",
            citation_type=CitationType.BOOK,
            display_title="Book citation",
            volume="1",
        )
    )
    document = registry_fixture.service.register_citation(
        _request(
            registry_fixture,
            canonical_reference="document:valid",
            citation_type=CitationType.DOCUMENT,
            display_title="Document citation",
        )
    )

    assert quran.citation.citation_type == CitationType.QURAN
    assert hadith.citation.citation_type == CitationType.HADITH
    assert book.citation.citation_type == CitationType.BOOK
    assert document.citation.citation_type == CitationType.DOCUMENT

    for citation_type in (CitationType.QURAN, CitationType.HADITH, CitationType.BOOK):
        with pytest.raises(CitationRegistryError) as exc_info:
            registry_fixture.service.register_citation(
                _request(
                    registry_fixture,
                    canonical_reference=f"{citation_type.value}:invalid",
                    citation_type=citation_type,
                    display_title=f"{citation_type.value} citation",
                )
            )
        assert exc_info.value.code == "CITATION_SCHEMA_INVALID"


def test_llm_tokens_map_only_to_active_registered_records(
    registry_fixture: RegistryFixture,
) -> None:
    registered = registry_fixture.service.register_citation(
        _request(registry_fixture, volume="1", page="10")
    )

    tokens = registry_fixture.service.llm_tokens_for_citations((registered.citation.id,))
    resolved = registry_fixture.service.resolve_llm_token(tokens[0])

    assert tokens == (registered.citation.token,)
    assert resolved.id == registered.citation.id

    with pytest.raises(CitationRegistryError) as missing_exc:
        registry_fixture.service.llm_tokens_for_citations((uuid4(),))
    assert missing_exc.value.code == "CITATION_NOT_REGISTERED"

    with pytest.raises(CitationRegistryError) as malformed_exc:
        registry_fixture.service.resolve_llm_token("BAD-token")
    assert malformed_exc.value.code == "CITATION_INPUT_INVALID"

    registry_fixture.service.invalidate_citation(
        citation_id=registered.citation.id,
        reason="source correction",
        actor_user_id=registry_fixture.actor_id,
    )

    with pytest.raises(CitationRegistryError) as inactive_list_exc:
        registry_fixture.service.llm_tokens_for_citations((registered.citation.id,))
    assert inactive_list_exc.value.code == "CITATION_INACTIVE"

    with pytest.raises(CitationRegistryError) as inactive_resolve_exc:
        registry_fixture.service.resolve_llm_token(registered.citation.token)
    assert inactive_resolve_exc.value.code == "CITATION_INACTIVE"

    inactive = registry_fixture.service.resolve_llm_token(
        registered.citation.token,
        require_active=False,
    )
    assert inactive.active is False


def test_canonical_collision_rejects_same_reference_for_different_chunk(
    registry_fixture: RegistryFixture,
) -> None:
    registry_fixture.service.register_citation(_request(registry_fixture, volume="1", page="10"))
    other_chunk_id = uuid4()
    with registry_fixture.session_factory() as session:
        session.add(
            DocumentChunk(
                id=other_chunk_id,
                document_version_id=registry_fixture.version_id,
                chunk_index=1,
                content="different reviewed content",
                content_normalized="different reviewed content",
                token_count=3,
                reference="book:1:10",
                metadata_json={},
                is_published=True,
                chunking_strategy_version="test-v1",
                content_hash="chunk-hash-1",
            )
        )
        session.commit()

    with pytest.raises(CitationRegistryError) as exc_info:
        registry_fixture.service.register_citation(
            _request(
                registry_fixture,
                chunk_id=other_chunk_id,
                canonical_reference="book:1:10",
                volume="1",
                page="10",
            )
        )

    assert exc_info.value.code == "CITATION_CANONICAL_COLLISION"


def test_register_from_chunk_uses_canonical_chunk_metadata(
    registry_fixture: RegistryFixture,
) -> None:
    registered = registry_fixture.service.register_from_chunk(
        chunk_id=registry_fixture.chunk_id,
        citation_type=CitationType.BOOK,
        display_title="Reviewed Book",
        actor_user_id=registry_fixture.actor_id,
    )

    assert registered.citation.canonical_reference == "book:1:10"
    assert registered.citation.chunk_id == registry_fixture.chunk_id


def test_rejects_chunk_version_mismatch(registry_fixture: RegistryFixture) -> None:
    other_version_id = uuid4()
    with registry_fixture.session_factory() as session:
        document = session.scalar(select(Document))
        assert document is not None
        session.add(
            DocumentVersion(
                id=other_version_id,
                document_id=document.id,
                version_number=2,
                status="published",
                content_hash="version-hash-2",
                metadata_json={},
                created_by=registry_fixture.actor_id,
            )
        )
        session.commit()

    with pytest.raises(CitationRegistryError) as exc_info:
        registry_fixture.service.register_citation(
            _request(
                registry_fixture,
                document_version_id=other_version_id,
                volume="1",
                page="10",
            )
        )

    assert exc_info.value.code == "CITATION_CHUNK_VERSION_MISMATCH"


def test_invalidation_preserves_history_and_marks_downstream_impact(
    registry_fixture: RegistryFixture,
) -> None:
    registered = registry_fixture.service.register_citation(
        _request(registry_fixture, volume="1", page="10")
    )
    retrieval_run_id = uuid4()
    retrieval_result_id = uuid4()
    answer_id = uuid4()

    with registry_fixture.session_factory() as session:
        session.add(
            RetrievalRun(
                id=retrieval_run_id,
                request_id="request-citation-invalidation",
                trace_id="trace-citation-invalidation",
                query_original="question",
                query_normalized="question",
                query_expansions={},
                filters={},
                retriever_version="test-retriever-v1",
                evidence_sufficient=True,
            )
        )
        session.add(
            RetrievalResult(
                id=retrieval_result_id,
                retrieval_run_id=retrieval_run_id,
                document_version_id=registry_fixture.version_id,
                chunk_id=registry_fixture.chunk_id,
                citation_id=registered.citation.id,
                rank=1,
                score_final=0.93,
                metadata_json={"existing": True},
            )
        )
        session.add(
            Answer(
                id=answer_id,
                message_id=uuid4(),
                retrieval_run_id=retrieval_run_id,
                model_configuration_id=uuid4(),
                prompt_version_id=uuid4(),
                policy_version_id=uuid4(),
                risk_level="low",
                madhhab="shafii",
                answer_json={"citations": [registered.citation.token]},
                confidence_level="high",
                evidence_sufficient=True,
            )
        )
        session.commit()

    result = registry_fixture.service.invalidate_citation(
        citation_id=registered.citation.id,
        reason="review correction",
        actor_user_id=registry_fixture.actor_id,
        trace_id="trace-invalidate",
    )

    assert result.affected_retrieval_result_count == 1
    assert result.affected_answer_count == 1
    assert result.citation.active is False
    assert result.trace["active"] is False

    with registry_fixture.session_factory() as session:
        citation = session.get(Citation, registered.citation.id)
        retrieval_result = session.get(RetrievalResult, retrieval_result_id)
        answer = session.get(Answer, answer_id)
        audits = session.scalars(
            select(AuditLog).where(AuditLog.action == "citations.invalidate")
        ).all()

    assert citation is not None
    assert citation.invalidated_at is not None
    assert citation.verified is False
    assert retrieval_result is not None
    assert retrieval_result.metadata_json["citation_invalidation"]["reason"] == "review correction"
    assert retrieval_result.metadata_json["existing"] is True
    assert answer is not None
    assert answer.invalidated_at == citation.invalidated_at
    assert answer.answer_json["warnings"][0]["citation_token"] == registered.citation.token
    assert audits
    assert audits[0].after_summary is not None
    assert audits[0].after_summary["affected_answer_count"] == 1
