"""Tests for published document lifecycle controls."""

from __future__ import annotations

from datetime import date
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
    ReviewApproval,
    ReviewTask,
    Source,
    SourceLicense,
    User,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.document_lifecycle import (
    DOCUMENT_LIFECYCLE_POLICY_VERSION,
    DocumentLifecycleError,
    DocumentLifecycleService,
)
from zayd_common.document_publishing import DocumentPublishingService


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _seed_user(session_factory, email: str) -> UUID:
    user_id = uuid4()
    with session_factory() as session:
        session.add(
            User(
                id=user_id,
                email=email,
                display_name=email.split("@")[0],
                password_hash=None,
                status="active",
            )
        )
        session.commit()
    return user_id


def _seed_published_document(session_factory, *, actor_id: UUID) -> tuple[UUID, UUID, UUID]:
    source_id = uuid4()
    license_id = uuid4()
    document_id = uuid4()
    v1_id = uuid4()
    v2_id = uuid4()
    with session_factory() as session:
        session.add(
            Source(
                id=source_id,
                name="Lifecycle source",
                source_type="book",
                language="th",
                reliability_level=5,
                created_by=actor_id,
            )
        )
        session.add(
            SourceLicense(
                id=license_id,
                source_id=source_id,
                license_name="Permission",
                license_version="2026-07",
                status="persistent_redistributable",
                storage_permission="allowed",
                embedding_permission="allowed",
                commercial_use="allowed",
                redistribution="allowed",
                attribution_required=False,
                valid_from=date(2026, 1, 1),
                valid_until=date(2026, 12, 31),
                created_by=actor_id,
            )
        )
        session.add(
            Document(
                id=document_id,
                source_id=source_id,
                source_license_id=license_id,
                canonical_id="doc-lifecycle",
                document_type="book",
                title="Lifecycle Document",
                language="th",
                madhhab="shafii",
                review_status="scholar_approved",
                created_by=actor_id,
            )
        )
        session.add(
            DocumentVersion(
                id=v1_id,
                document_id=document_id,
                version_number=1,
                status="scholar_approved",
                content_hash="hash-v1",
                extracted_text="Previous approved content.",
                metadata_json={"review": {"status": "approved"}},
                created_by=actor_id,
            )
        )
        session.add(
            DocumentVersion(
                id=v2_id,
                document_id=document_id,
                version_number=2,
                status="scholar_approved",
                content_hash="hash-v2",
                extracted_text="Current published content.",
                metadata_json={"review": {"status": "approved"}},
                created_by=actor_id,
            )
        )
        session.commit()

    publisher = DocumentPublishingService(SQLAlchemyUnitOfWork(session_factory))
    # Seed chunks for v1 without making it the current document version.
    with session_factory() as session:
        version_1 = session.get(DocumentVersion, v1_id)
        document = session.get(Document, document_id)
        assert version_1 is not None and document is not None
        chunk = DocumentChunk(
            id=uuid4(),
            document_version_id=v1_id,
            chunk_index=0,
            content="Previous approved content.",
            content_normalized="Previous approved content.",
            token_count=3,
            reference="doc-lifecycle:v1:chunk-1",
            metadata_json={"publishing_policy_version": "document-publish-v1"},
            is_published=False,
            chunking_strategy_version="publish-chunker-v1",
            content_hash=f"v1-{uuid4().hex}",
        )
        session.add(chunk)
        version_1.status = "scholar_approved"
        session.commit()
    with session_factory() as session:
        document = session.get(Document, document_id)
        assert document is not None
        document.review_status = "scholar_approved"
        document.published_version_id = None
        task_id = uuid4()
        session.add(
            ReviewTask(
                id=task_id,
                document_version_id=v2_id,
                document_id=document_id,
                assigned_to=actor_id,
                review_level="initial",
                status="completed",
                priority="normal",
                category="book",
                language="th",
                madhhab="shafii",
                created_by=actor_id,
            )
        )
        session.add(
            ReviewApproval(
                id=uuid4(),
                document_version_id=v2_id,
                review_task_id=task_id,
                approver_id=actor_id,
                approval_level="initial",
                content_risk="routine",
                status="active",
                reason="Routine publish seed.",
            )
        )
        session.commit()
    publisher.publish_document_version(
        document_version_id=v2_id,
        actor_user_id=actor_id,
        principal_roles=frozenset({"senior_scholar"}),
        content_risk="routine",
        reason="Seed publish.",
        today=date(2026, 7, 8),
    )
    return document_id, v1_id, v2_id


def _seed_answer_for_version(session_factory, *, version_id: UUID) -> UUID:
    with session_factory() as session:
        chunk = session.execute(
            select(DocumentChunk).where(DocumentChunk.document_version_id == version_id)
        ).scalars().first()
        assert chunk is not None
        citation_id = uuid4()
        session.add(
            Citation(
                id=citation_id,
                canonical_reference=chunk.reference or f"chunk-{chunk.id}",
                document_version_id=version_id,
                chunk_id=chunk.id,
                citation_type="book",
                display_title="Lifecycle Document",
                verified=True,
            )
        )
        run_id = uuid4()
        session.add(
            RetrievalRun(
                id=run_id,
                request_id=f"request-{uuid4().hex}",
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
                id=uuid4(),
                retrieval_run_id=run_id,
                document_version_id=version_id,
                chunk_id=chunk.id,
                citation_id=citation_id,
                rank=1,
                score_final=1.0,
                metadata_json={},
            )
        )
        answer_id = uuid4()
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
                answer_json={"text": "synthetic test answer"},
                confidence_level="high",
                evidence_sufficient=True,
            )
        )
        session.commit()
    return answer_id


def _service(session_factory) -> DocumentLifecycleService:
    return DocumentLifecycleService(SQLAlchemyUnitOfWork(session_factory))


def test_suspend_hides_chunks_and_invalidates_answers(db):
    actor = _seed_user(db, "lifecycle-scholar@example.com")
    document_id, _, version_id = _seed_published_document(db, actor_id=actor)
    answer_id = _seed_answer_for_version(db, version_id=version_id)

    result = _service(db).suspend_document(
        document_id=document_id,
        actor_user_id=actor,
        principal_roles=frozenset({"senior_scholar"}),
        reason="Citation issue.",
        trace_id="trace-suspend",
    )

    assert result.document_status == "suspended"
    assert result.current_published_version_id == version_id
    assert result.affected_chunk_count == 1
    assert result.affected_citation_count == 1
    assert result.affected_answer_count == 1
    assert result.policy_version == DOCUMENT_LIFECYCLE_POLICY_VERSION
    with db() as session:
        chunk = session.execute(
            select(DocumentChunk).where(DocumentChunk.document_version_id == version_id)
        ).scalar_one()
        citation = session.execute(
            select(Citation).where(Citation.document_version_id == version_id)
        ).scalar_one()
        answer = session.get(Answer, answer_id)
        logs = session.execute(
            select(AuditLog).where(AuditLog.action == "documents.suspend")
        ).scalars().all()
    assert chunk.is_published is False
    assert chunk.metadata_json["visibility"]["status"] == "hidden"
    assert citation.verified is False
    assert citation.invalidated_at is not None
    assert answer is not None
    assert answer.invalidated_at is not None
    assert "suspended" in answer.answer_json["invalidation_warning"]
    assert any(log.trace_id == "trace-suspend" for log in logs)


def test_archive_clears_published_version_and_keeps_chunks_hidden(db):
    actor = _seed_user(db, "lifecycle-archive@example.com")
    document_id, _, version_id = _seed_published_document(db, actor_id=actor)

    result = _service(db).archive_document(
        document_id=document_id,
        actor_user_id=actor,
        principal_roles=frozenset({"admin"}),
        reason="Source withdrawn.",
    )

    assert result.document_status == "archived"
    assert result.previous_published_version_id == version_id
    assert result.current_published_version_id is None
    with db() as session:
        document = session.get(Document, document_id)
        chunk = session.execute(
            select(DocumentChunk).where(DocumentChunk.document_version_id == version_id)
        ).scalar_one()
    assert document is not None
    assert document.published_version_id is None
    assert chunk.is_published is False


def test_rollback_restores_previous_approved_version_and_invalidates_answers(db):
    actor = _seed_user(db, "lifecycle-rollback@example.com")
    document_id, old_version_id, current_version_id = _seed_published_document(db, actor_id=actor)
    answer_id = _seed_answer_for_version(db, version_id=current_version_id)

    result = _service(db).rollback_document(
        document_id=document_id,
        target_document_version_id=old_version_id,
        actor_user_id=actor,
        principal_roles=frozenset({"senior_scholar"}),
        reason="Rollback after citation review.",
    )

    assert result.document_status == "published"
    assert result.previous_published_version_id == current_version_id
    assert result.current_published_version_id == old_version_id
    assert result.affected_answer_count == 1
    with db() as session:
        document = session.get(Document, document_id)
        old_chunk = session.execute(
            select(DocumentChunk).where(DocumentChunk.document_version_id == old_version_id)
        ).scalar_one()
        current_chunk = session.execute(
            select(DocumentChunk).where(DocumentChunk.document_version_id == current_version_id)
        ).scalar_one()
        answer = session.get(Answer, answer_id)
    assert document is not None
    assert document.published_version_id == old_version_id
    assert old_chunk.is_published is True
    assert current_chunk.is_published is False
    assert answer is not None
    assert answer.invalidated_at is not None
    assert "rolled back" in answer.answer_json["invalidation_warning"]


def test_row_version_conflict_blocks_lifecycle_change(db):
    actor = _seed_user(db, "lifecycle-conflict@example.com")
    document_id, _, _ = _seed_published_document(db, actor_id=actor)

    with pytest.raises(DocumentLifecycleError) as exc:
        _service(db).suspend_document(
            document_id=document_id,
            actor_user_id=actor,
            principal_roles=frozenset({"senior_scholar"}),
            reason="Conflict.",
            base_row_version=999,
        )

    assert exc.value.code == "DOCUMENT_LIFECYCLE_CONFLICT"


def test_unprivileged_role_cannot_suspend(db):
    actor = _seed_user(db, "lifecycle-reviewer@example.com")
    document_id, _, _ = _seed_published_document(db, actor_id=actor)

    with pytest.raises(DocumentLifecycleError) as exc:
        _service(db).suspend_document(
            document_id=document_id,
            actor_user_id=actor,
            principal_roles=frozenset({"reviewer"}),
            reason="Not allowed.",
        )

    assert exc.value.code == "DOCUMENT_LIFECYCLE_ACCESS_DENIED"
