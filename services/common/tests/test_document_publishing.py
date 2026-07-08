"""Tests for document publishing service."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.chunking import CHUNKING_FRAMEWORK_VERSION, PARAGRAPH_STRATEGY_VERSION
from zayd_common.database.models import (
    AuditLog,
    Base,
    Document,
    DocumentChunk,
    DocumentVersion,
    ReviewApproval,
    ReviewTask,
    Source,
    SourceLicense,
    User,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.document_publishing import (
    CHUNKING_STRATEGY_VERSION,
    CITATION_PIPELINE_VERSION,
    DOCUMENT_PUBLISH_POLICY_VERSION,
    EMBEDDING_PIPELINE_VERSION,
    DocumentPublishingError,
    DocumentPublishingService,
)


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


def _seed_publish_context(
    session_factory,
    *,
    uploader_id: UUID,
    reviewer_id: UUID,
    scholar_id: UUID,
    document_status: str = "scholar_approved",
    version_status: str = "scholar_approved",
    license_status: str = "persistent_redistributable",
    embedding_permission: str = "allowed",
    extracted_text: str = "First reviewed paragraph.\n\nSecond reviewed paragraph.",
    content_risk: str = "sensitive",
) -> tuple[UUID, UUID, UUID]:
    source_id = uuid4()
    license_id = uuid4()
    document_id = uuid4()
    version_id = uuid4()
    task_id = uuid4()
    with session_factory() as session:
        session.add(
            Source(
                id=source_id,
                name="Known source",
                source_type="book",
                language="th",
                reliability_level=5,
                created_by=uploader_id,
            )
        )
        session.add(
            SourceLicense(
                id=license_id,
                source_id=source_id,
                license_name="Permission",
                license_version="2026-07",
                status=license_status,
                storage_permission="allowed",
                embedding_permission=embedding_permission,
                commercial_use="allowed",
                redistribution="allowed",
                attribution_required=False,
                valid_from=date(2026, 1, 1),
                valid_until=date(2026, 12, 31),
                created_by=uploader_id,
            )
        )
        session.add(
            Document(
                id=document_id,
                source_id=source_id,
                source_license_id=license_id,
                canonical_id="doc-publish",
                document_type="book",
                title="Publishable Document",
                language="th",
                madhhab="shafii",
                review_status=document_status,
                created_by=uploader_id,
            )
        )
        session.add(
            DocumentVersion(
                id=version_id,
                document_id=document_id,
                version_number=1,
                status=version_status,
                content_hash="hash-publish",
                extracted_text=extracted_text,
                metadata_json={"review": {"status": "approved"}},
                created_by=uploader_id,
            )
        )
        session.add(
            ReviewTask(
                id=task_id,
                document_version_id=version_id,
                document_id=document_id,
                assigned_to=scholar_id,
                review_level="scholar",
                status="completed",
                priority="high",
                category="book",
                language="th",
                madhhab="shafii",
                created_by=reviewer_id,
            )
        )
        levels = ("initial",) if content_risk == "routine" else ("initial", "scholar")
        for level, approver in zip(levels, (reviewer_id, scholar_id), strict=False):
            session.add(
                ReviewApproval(
                    id=uuid4(),
                    document_version_id=version_id,
                    review_task_id=task_id,
                    approver_id=approver,
                    approval_level=level,
                    content_risk=content_risk,
                    status="active",
                    reason=f"{level} approval.",
                )
            )
        session.commit()
    return document_id, version_id, license_id


def _service(session_factory, *, before_visibility_flip=None) -> DocumentPublishingService:
    return DocumentPublishingService(
        SQLAlchemyUnitOfWork(session_factory),
        before_visibility_flip=before_visibility_flip,
    )


def test_publish_success_records_versions_and_exposes_chunks(db):
    uploader = _seed_user(db, "uploader@example.com")
    reviewer = _seed_user(db, "reviewer@example.com")
    scholar = _seed_user(db, "scholar@example.com")
    document_id, version_id, _ = _seed_publish_context(
        db,
        uploader_id=uploader,
        reviewer_id=reviewer,
        scholar_id=scholar,
    )

    result = _service(db).publish_document_version(
        document_version_id=version_id,
        actor_user_id=scholar,
        principal_roles=frozenset({"senior_scholar"}),
        content_risk="sensitive",
        reason="Approved for retrieval.",
        trace_id="trace-publish",
        today=date(2026, 7, 8),
    )

    assert result.document_id == document_id
    assert result.published_version_id == version_id
    assert result.document_status == "published"
    assert result.version_status == "published"
    assert result.chunk_count == 2
    assert result.idempotent is False
    assert result.policy_version == DOCUMENT_PUBLISH_POLICY_VERSION
    assert result.chunking_strategy_version == CHUNKING_STRATEGY_VERSION
    assert result.chunking_strategy_version == CHUNKING_FRAMEWORK_VERSION
    assert result.embedding_pipeline_version == EMBEDDING_PIPELINE_VERSION
    assert result.citation_pipeline_version == CITATION_PIPELINE_VERSION
    with db() as session:
        document = session.get(Document, document_id)
        version = session.get(DocumentVersion, version_id)
        chunks = session.execute(
            select(DocumentChunk).where(DocumentChunk.document_version_id == version_id)
        ).scalars().all()
        chunks = sorted(chunks, key=lambda chunk: chunk.chunk_index)
        logs = session.execute(
            select(AuditLog).where(AuditLog.action == "documents.publish")
        ).scalars().all()
    assert document is not None
    assert document.review_status == "published"
    assert document.published_version_id == version_id
    assert version is not None
    assert version.frozen_at is not None
    assert version.metadata_json["publishing"]["published_version_id"] == str(version_id)
    assert version.metadata_json["publishing"]["license_policy_version"]
    assert len(chunks) == 2
    assert all(chunk.is_published is True for chunk in chunks)
    assert [chunk.chunking_strategy_version for chunk in chunks] == [
        PARAGRAPH_STRATEGY_VERSION,
        PARAGRAPH_STRATEGY_VERSION,
    ]
    assert [chunk.reference for chunk in chunks] == [
        "doc-publish:v1:paragraph-1",
        "doc-publish:v1:paragraph-2",
    ]
    assert chunks[0].metadata_json["document_version_id"] == str(version_id)
    assert chunks[0].metadata_json["chunking_framework_version"] == CHUNKING_FRAMEWORK_VERSION
    assert chunks[0].metadata_json["embedding"]["pipeline_version"] == EMBEDDING_PIPELINE_VERSION
    assert chunks[0].metadata_json["citation"]["canonical_reference"].endswith("paragraph-1")
    assert any(log.trace_id == "trace-publish" and log.outcome == "success" for log in logs)


def test_missing_approval_blocks_publish_and_search_visibility(db):
    uploader = _seed_user(db, "uploader-missing@example.com")
    reviewer = _seed_user(db, "reviewer-missing@example.com")
    scholar = _seed_user(db, "scholar-missing@example.com")
    document_id, version_id, _ = _seed_publish_context(
        db,
        uploader_id=uploader,
        reviewer_id=reviewer,
        scholar_id=scholar,
        content_risk="routine",
    )

    with pytest.raises(DocumentPublishingError) as exc:
        _service(db).publish_document_version(
            document_version_id=version_id,
            actor_user_id=scholar,
            principal_roles=frozenset({"senior_scholar"}),
            content_risk="sensitive",
            reason="Attempt publish.",
            today=date(2026, 7, 8),
        )

    assert exc.value.code == "DOCUMENT_PUBLISH_APPROVAL_REQUIRED"
    with db() as session:
        document = session.get(Document, document_id)
        chunks = session.execute(
            select(DocumentChunk).where(DocumentChunk.document_version_id == version_id)
        ).scalars().all()
    assert document is not None
    assert document.review_status == "scholar_approved"
    assert chunks == []


def test_license_change_race_blocks_immediately_before_publish(db):
    uploader = _seed_user(db, "uploader-license@example.com")
    reviewer = _seed_user(db, "reviewer-license@example.com")
    scholar = _seed_user(db, "scholar-license@example.com")
    document_id, version_id, license_id = _seed_publish_context(
        db,
        uploader_id=uploader,
        reviewer_id=reviewer,
        scholar_id=scholar,
        embedding_permission="allowed",
    )
    with db() as session:
        license_record = session.get(SourceLicense, license_id)
        assert license_record is not None
        license_record.embedding_permission = "prohibited"
        session.commit()

    with pytest.raises(DocumentPublishingError) as exc:
        _service(db).publish_document_version(
            document_version_id=version_id,
            actor_user_id=scholar,
            principal_roles=frozenset({"senior_scholar"}),
            content_risk="sensitive",
            reason="Attempt publish.",
            today=date(2026, 7, 8),
        )

    assert exc.value.code == "DOCUMENT_PUBLISH_LICENSE_BLOCKED"
    with db() as session:
        document = session.get(Document, document_id)
        chunks = session.execute(
            select(DocumentChunk).where(DocumentChunk.document_version_id == version_id)
        ).scalars().all()
        denied = session.execute(
            select(AuditLog).where(AuditLog.action == "documents.publish")
        ).scalars().all()
    assert document is not None
    assert document.published_version_id is None
    assert chunks == []
    assert any(log.outcome == "denied" for log in denied)


def test_retry_does_not_duplicate_chunks(db):
    uploader = _seed_user(db, "uploader-retry@example.com")
    reviewer = _seed_user(db, "reviewer-retry@example.com")
    scholar = _seed_user(db, "scholar-retry@example.com")
    _, version_id, _ = _seed_publish_context(
        db,
        uploader_id=uploader,
        reviewer_id=reviewer,
        scholar_id=scholar,
    )
    service = _service(db)

    first = service.publish_document_version(
        document_version_id=version_id,
        actor_user_id=scholar,
        principal_roles=frozenset({"senior_scholar"}),
        content_risk="sensitive",
        reason="Approved for retrieval.",
        today=date(2026, 7, 8),
    )
    second = service.publish_document_version(
        document_version_id=version_id,
        actor_user_id=scholar,
        principal_roles=frozenset({"senior_scholar"}),
        content_risk="sensitive",
        reason="Retry publish.",
        today=date(2026, 7, 8),
    )

    assert first.idempotent is False
    assert second.idempotent is True
    assert [chunk.content_hash for chunk in second.chunks] == [
        chunk.content_hash for chunk in first.chunks
    ]
    with db() as session:
        chunks = session.execute(
            select(DocumentChunk).where(DocumentChunk.document_version_id == version_id)
        ).scalars().all()
    assert len(chunks) == first.chunk_count


def test_failure_before_visibility_flip_leaves_no_searchable_chunks(db):
    uploader = _seed_user(db, "uploader-failure@example.com")
    reviewer = _seed_user(db, "reviewer-failure@example.com")
    scholar = _seed_user(db, "scholar-failure@example.com")
    document_id, version_id, _ = _seed_publish_context(
        db,
        uploader_id=uploader,
        reviewer_id=reviewer,
        scholar_id=scholar,
    )

    def fail() -> None:
        raise RuntimeError("pipeline failure")

    with pytest.raises(DocumentPublishingError) as exc:
        _service(db, before_visibility_flip=fail).publish_document_version(
            document_version_id=version_id,
            actor_user_id=scholar,
            principal_roles=frozenset({"senior_scholar"}),
            content_risk="sensitive",
            reason="Attempt publish.",
            today=date(2026, 7, 8),
        )

    assert exc.value.code == "DOCUMENT_PUBLISH_PIPELINE_FAILED"
    with db() as session:
        document = session.get(Document, document_id)
        version = session.get(DocumentVersion, version_id)
        chunks = session.execute(
            select(DocumentChunk).where(DocumentChunk.document_version_id == version_id)
        ).scalars().all()
    assert document is not None
    assert document.review_status == "scholar_approved"
    assert document.published_version_id is None
    assert version is not None
    assert version.status == "scholar_approved"
    assert chunks == []


def test_expired_approval_does_not_satisfy_publish(db):
    uploader = _seed_user(db, "uploader-expired@example.com")
    reviewer = _seed_user(db, "reviewer-expired@example.com")
    scholar = _seed_user(db, "scholar-expired@example.com")
    _, version_id, _ = _seed_publish_context(
        db,
        uploader_id=uploader,
        reviewer_id=reviewer,
        scholar_id=scholar,
        content_risk="routine",
    )
    with db() as session:
        approval = session.execute(
            select(ReviewApproval).where(ReviewApproval.document_version_id == version_id)
        ).scalar_one()
        approval.valid_until = datetime.now(UTC) - timedelta(minutes=1)
        session.commit()

    with pytest.raises(DocumentPublishingError) as exc:
        _service(db).publish_document_version(
            document_version_id=version_id,
            actor_user_id=scholar,
            principal_roles=frozenset({"senior_scholar"}),
            content_risk="routine",
            reason="Attempt publish.",
            today=date(2026, 7, 8),
        )

    assert exc.value.code == "DOCUMENT_PUBLISH_APPROVAL_REQUIRED"
