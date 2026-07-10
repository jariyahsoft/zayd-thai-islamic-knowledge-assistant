"""Tests for the document review service."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import (
    AuditLog,
    Base,
    Document,
    DocumentVersion,
    ReviewComment,
    ReviewDecisionRecord,
    ReviewRevision,
    ReviewTask,
    User,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.document_review import DocumentReviewError, DocumentReviewService


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture
def reviewer_id(db) -> UUID:
    uid = uuid4()
    with db() as session:
        session.add(
            User(
                id=uid,
                email="reviewer@example.com",
                display_name="Reviewer",
                password_hash=None,
                status="active",
                preferred_language="th",
                preferred_madhhab="shafii",
            )
        )
        session.commit()
    return uid


@pytest.fixture
def senior_scholar_id(db) -> UUID:
    uid = uuid4()
    with db() as session:
        session.add(
            User(
                id=uid,
                email="scholar@example.com",
                display_name="Scholar",
                password_hash=None,
                status="active",
            )
        )
        session.commit()
    return uid


def _seed_review_context(
    session_factory,
    *,
    created_by: UUID | None = None,
    assigned_to: UUID | None = None,
    review_level: str = "initial",
    task_status: str = "open",
    document_status: str = "in_review",
    text: str = "Original extracted text\nLine two",
    original_file_key: str = "uploads/original.txt",
) -> tuple[UUID, UUID, UUID, UUID]:
    creator = created_by or uuid4()
    doc_id = uuid4()
    version_id = uuid4()
    task_id = uuid4()
    with session_factory() as session:
        session.add(
            Document(
                id=doc_id,
                source_id=uuid4(),
                source_license_id=uuid4(),
                canonical_id=f"doc-{uuid4().hex[:8]}",
                document_type="book",
                title="Original Title",
                author="Original Author",
                language="th",
                madhhab="shafii",
                review_status=document_status,
                created_by=creator,
            )
        )
        session.add(
            DocumentVersion(
                id=version_id,
                document_id=doc_id,
                version_number=1,
                status="parsed",
                content_hash="hash-original",
                original_file_key=original_file_key,
                extracted_text=text,
                metadata_json={"filename": "original.txt", "content_type": "text/plain"},
                created_by=creator,
            )
        )
        session.add(
            ReviewTask(
                id=task_id,
                document_version_id=version_id,
                document_id=doc_id,
                assigned_to=assigned_to,
                review_level=review_level,
                status=task_status,
                priority="normal",
                category="book",
                language="th",
                madhhab="shafii",
                created_by=creator,
            )
        )
        session.commit()
    return doc_id, version_id, task_id, creator


def test_get_draft_preserves_original_file_key(db, reviewer_id):
    _, version_id, task_id, _ = _seed_review_context(db, assigned_to=reviewer_id)
    service = DocumentReviewService(SQLAlchemyUnitOfWork(db))

    draft = service.get_draft(
        task_id,
        actor_user_id=reviewer_id,
        principal_roles=frozenset({"reviewer"}),
    )

    assert draft.document_version_id == version_id
    assert draft.task_row_version == 1
    assert draft.original_file_key == "uploads/original.txt"
    assert draft.editable_text == "Original extracted text\nLine two"
    assert draft.editable_metadata["title"] == "Original Title"


def test_apply_edit_creates_revision_diff_and_does_not_modify_original_version(db, reviewer_id):
    _, version_id, task_id, _ = _seed_review_context(db, assigned_to=reviewer_id)
    service = DocumentReviewService(SQLAlchemyUnitOfWork(db))

    result = service.apply_edit(
        task_id,
        actor_user_id=reviewer_id,
        principal_roles=frozenset({"reviewer"}),
        base_task_row_version=1,
        text="Original extracted text\nCorrected line two",
        metadata_updates={"title": "Reviewed Title", "ignored_field": "nope"},
        trace_id="trace-edit",
    )

    assert result.task_row_version == 2
    assert result.revision.revision_number == 1
    assert result.revision.text_changed is True
    assert "title" in result.revision.metadata_changed_fields
    assert "ignored_field" not in result.editable_metadata
    assert "Corrected line two" in result.revision.diff_text

    with db() as session:
        version = session.get(DocumentVersion, version_id)
        revisions = session.execute(select(ReviewRevision)).scalars().all()
        logs = session.execute(
            select(AuditLog).where(AuditLog.action == "document_review.revision.created")
        ).scalars().all()
    assert version is not None
    assert version.extracted_text == "Original extracted text\nLine two"
    assert version.original_file_key == "uploads/original.txt"
    assert len(revisions) == 1
    assert logs and logs[0].trace_id == "trace-edit"


def test_apply_edit_detects_conflicting_row_version(db, reviewer_id):
    _, _, task_id, _ = _seed_review_context(db, assigned_to=reviewer_id)
    service = DocumentReviewService(SQLAlchemyUnitOfWork(db))
    service.apply_edit(
        task_id,
        actor_user_id=reviewer_id,
        principal_roles=frozenset({"reviewer"}),
        base_task_row_version=1,
        text="First edit",
    )

    with pytest.raises(DocumentReviewError) as exc:
        service.apply_edit(
            task_id,
            actor_user_id=reviewer_id,
            principal_roles=frozenset({"reviewer"}),
            base_task_row_version=1,
            text="Stale edit",
        )

    assert exc.value.code == "DOCUMENT_REVIEW_CONFLICT"


def test_add_comment_records_comment_and_audit(db, reviewer_id):
    _, _, task_id, _ = _seed_review_context(db, assigned_to=reviewer_id)
    service = DocumentReviewService(SQLAlchemyUnitOfWork(db))

    comment = service.add_comment(
        task_id,
        actor_user_id=reviewer_id,
        principal_roles=frozenset({"reviewer"}),
        body="  Please verify the reference.  ",
        anchor={"line": 2},
        trace_id="trace-comment",
    )

    assert comment.body == "Please verify the reference."
    assert comment.anchor == {"line": 2}
    with db() as session:
        comments = session.execute(select(ReviewComment)).scalars().all()
        logs = session.execute(
            select(AuditLog).where(AuditLog.action == "document_review.comment.created")
        ).scalars().all()
    assert len(comments) == 1
    assert logs and logs[0].trace_id == "trace-comment"


def test_request_changes_decision_follows_state_machine(db, reviewer_id):
    _, _, task_id, _ = _seed_review_context(db, assigned_to=reviewer_id)
    service = DocumentReviewService(SQLAlchemyUnitOfWork(db))

    result = service.decide(
        task_id,
        actor_user_id=reviewer_id,
        principal_roles=frozenset({"reviewer"}),
        decision="request_changes",
        reason="Needs corrected metadata.",
        base_task_row_version=1,
        trace_id="trace-decision",
    )

    assert result.decision.resulting_task_status == "completed"
    assert result.decision.resulting_document_status == "changes_requested"
    with db() as session:
        record = session.execute(select(ReviewDecisionRecord)).scalar_one()
        task = session.get(ReviewTask, task_id)
        doc = session.get(Document, record.document_version_id)
        logs = session.execute(
            select(AuditLog).where(AuditLog.action == "document_review.decision.request_changes")
        ).scalars().all()
        document = session.get(Document, task.document_id) if task else None
    assert doc is None
    assert task is not None and task.status == "completed"
    assert document is not None and document.review_status == "changes_requested"
    assert logs and logs[0].trace_id == "trace-decision"


def test_reject_requires_valid_state_transition(db, reviewer_id):
    _, _, task_id, _ = _seed_review_context(
        db,
        assigned_to=reviewer_id,
        document_status="draft",
    )
    service = DocumentReviewService(SQLAlchemyUnitOfWork(db))

    with pytest.raises(DocumentReviewError) as exc:
        service.decide(
            task_id,
            actor_user_id=reviewer_id,
            principal_roles=frozenset({"reviewer"}),
            decision="reject",
            reason="Invalid source.",
            base_task_row_version=1,
        )

    assert exc.value.code == "DOCUMENT_REVIEW_INVALID_STATUS"


def test_approve_blocks_self_approval(db, reviewer_id):
    _, _, task_id, _ = _seed_review_context(
        db,
        created_by=reviewer_id,
        assigned_to=reviewer_id,
    )
    service = DocumentReviewService(SQLAlchemyUnitOfWork(db))

    with pytest.raises(DocumentReviewError) as exc:
        service.decide(
            task_id,
            actor_user_id=reviewer_id,
            principal_roles=frozenset({"reviewer"}),
            decision="approve",
            reason="Looks correct.",
            base_task_row_version=1,
        )

    assert exc.value.code == "DOCUMENT_REVIEW_SELF_APPROVAL_DENIED"


def test_initial_approve_moves_document_to_scholar_review(db, reviewer_id, senior_scholar_id):
    _, _, task_id, _ = _seed_review_context(
        db,
        created_by=senior_scholar_id,
        assigned_to=reviewer_id,
    )
    service = DocumentReviewService(SQLAlchemyUnitOfWork(db))

    result = service.decide(
        task_id,
        actor_user_id=reviewer_id,
        principal_roles=frozenset({"reviewer"}),
        decision="approve",
        reason="Initial review complete.",
        base_task_row_version=1,
    )

    assert result.decision.resulting_document_status == "scholar_review"
    with db() as session:
        task = session.get(ReviewTask, task_id)
        document = session.get(Document, task.document_id) if task else None
    assert task is not None and task.status == "completed"
    assert document is not None and document.review_status == "scholar_review"


def test_scholar_approve_requires_senior_role(db, reviewer_id, senior_scholar_id):
    _, _, task_id, _ = _seed_review_context(
        db,
        created_by=reviewer_id,
        assigned_to=senior_scholar_id,
        review_level="scholar",
        document_status="scholar_review",
    )
    service = DocumentReviewService(SQLAlchemyUnitOfWork(db))

    result = service.decide(
        task_id,
        actor_user_id=senior_scholar_id,
        principal_roles=frozenset({"senior_scholar"}),
        decision="approve",
        reason="Scholar approval complete.",
        base_task_row_version=1,
    )

    assert result.decision.resulting_document_status == "scholar_approved"
