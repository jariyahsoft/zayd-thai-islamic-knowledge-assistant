from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.answer_invalidation import (
    AnswerInvalidationError,
    AnswerInvalidationNotice,
    AnswerInvalidationService,
)
from zayd_common.database.models import (
    Answer,
    AnswerInvalidation,
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
from zayd_common.rbac import Permission


class Notifier:
    def __init__(self) -> None:
        self.notices: list[AnswerInvalidationNotice] = []

    def send(self, notice: AnswerInvalidationNotice) -> str:
        self.notices.append(notice)
        return "sent"


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _seed(db):
    actor, source_id, license_id, document_id, version_id, chunk_id = [uuid4() for _ in range(6)]
    citation_id, run_id, answer_id = uuid4(), uuid4(), uuid4()
    with db() as session:
        session.add(User(id=actor, email="invalidator@example.test", display_name="Invalidator"))
        session.add(
            Source(
                id=source_id,
                name="Source",
                source_type="book",
                language="th",
                reliability_level=3,
                is_active=True,
                created_by=actor,
            )
        )
        session.add(
            SourceLicense(
                id=license_id,
                source_id=source_id,
                license_name="Test",
                created_by=actor,
            )
        )
        session.add(
            Document(
                id=document_id,
                source_id=source_id,
                source_license_id=license_id,
                canonical_id="doc",
                document_type="book",
                title="Title",
                language="th",
                review_status="published",
                created_by=actor,
            )
        )
        session.add(
            DocumentVersion(
                id=version_id,
                document_id=document_id,
                version_number=1,
                status="published",
                content_hash="hash",
                created_by=actor,
            )
        )
        session.add(
            DocumentChunk(
                id=chunk_id,
                document_version_id=version_id,
                chunk_index=0,
                content="text",
                content_normalized="text",
                content_hash="chunk",
                token_count=1,
                is_published=True,
                chunking_strategy_version="test-v1",
            )
        )
        session.add(
            Citation(
                id=citation_id,
                canonical_reference="ref",
                document_version_id=version_id,
                chunk_id=chunk_id,
                citation_type="book",
                display_title="Ref",
                verified=True,
            )
        )
        session.add(
            RetrievalRun(
                id=run_id,
                request_id="request",
                query_original="q",
                query_normalized="q",
                query_expansions={},
                filters={},
                retriever_version="v1",
                evidence_sufficient=True,
            )
        )
        session.add(
            RetrievalResult(
                retrieval_run_id=run_id,
                document_version_id=version_id,
                chunk_id=chunk_id,
                citation_id=citation_id,
                rank=1,
                score_final=1.0,
                metadata_json={},
            )
        )
        session.add(
            Answer(
                id=answer_id,
                message_id=uuid4(),
                retrieval_run_id=run_id,
                model_configuration_id=uuid4(),
                prompt_version_id=uuid4(),
                policy_version_id=uuid4(),
                risk_level="low",
                madhhab="shafii",
                answer_json={"answer_th": "original"},
                confidence_level="high",
                evidence_sufficient=True,
            )
        )
        session.commit()
    return actor, source_id, citation_id, answer_id


def test_invalidation_is_immediate_historical_idempotent_and_notified(db) -> None:
    actor, source_id, citation_id, answer_id = _seed(db)
    notifier = Notifier()
    service = AnswerInvalidationService(SQLAlchemyUnitOfWork(db), notifier)
    permissions = frozenset({Permission.ANSWERS_INVALIDATE.value, Permission.ANSWERS_REVIEW.value})
    first = service.invalidate(
        answer_id=answer_id,
        reason="Citation withdrawn",
        idempotency_key="invalidate-1",
        actor_user_id=actor,
        permissions=permissions,
        citation_id=citation_id,
    )
    second = service.invalidate(
        answer_id=answer_id,
        reason="Citation withdrawn",
        idempotency_key="invalidate-1",
        actor_user_id=actor,
        permissions=permissions,
        citation_id=citation_id,
    )
    assert first.idempotent is False and second.idempotent is True
    assert len(notifier.notices) == 1
    with db() as session:
        answer = session.get(Answer, answer_id)
        assert answer is not None and answer.invalidated_at is not None
        assert answer.answer_json["invalidation_warning"]
        assert session.scalar(
            select(AnswerInvalidation).where(AnswerInvalidation.answer_id == answer_id)
        )
        assert session.scalar(select(AuditLog).where(AuditLog.action == "answer.invalidate"))


def test_bounded_retryable_discovery_by_citation_and_source(db) -> None:
    actor, source_id, citation_id, answer_id = _seed(db)
    service = AnswerInvalidationService(SQLAlchemyUnitOfWork(db))
    permissions = frozenset({Permission.ANSWERS_REVIEW.value})
    by_citation = service.discover(
        permissions=permissions, citation_id=citation_id, limit=999, actor_user_id=actor
    )
    by_source = service.discover(
        permissions=permissions, source_id=source_id, limit=1, offset=0, actor_user_id=actor
    )
    assert by_citation.answer_ids == (answer_id,)
    assert by_citation.limit == 200
    assert by_source.answer_ids == (answer_id,)
    assert by_source.next_offset is None


def test_discovery_requires_exactly_one_scope(db) -> None:
    service = AnswerInvalidationService(SQLAlchemyUnitOfWork(db))
    with pytest.raises(AnswerInvalidationError, match="exactly one"):
        service.discover(permissions=frozenset({Permission.ANSWERS_REVIEW.value}))


def test_invalidation_requires_permission(db) -> None:
    actor, _source_id, _citation_id, answer_id = _seed(db)
    service = AnswerInvalidationService(SQLAlchemyUnitOfWork(db))
    with pytest.raises(AnswerInvalidationError, match="Forbidden"):
        service.invalidate(
            answer_id=answer_id,
            reason="No permission",
            idempotency_key="denied",
            actor_user_id=actor,
            permissions=frozenset(),
        )
