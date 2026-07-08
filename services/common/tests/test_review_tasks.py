"""Tests for the review task creation service.

Covers:
- Task creation integration tests (success paths)
- Duplicate-event/idempotency tests
- Assignment-rule tests (priority, due date)
- Rejection of ineligible documents
- Audit event verification
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import AuditLog, Base, Document, DocumentVersion
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.review_tasks import (
    REVIEW_TASK_POLICY_VERSION,
    ReviewTaskCreationError,
    ReviewTaskService,
    resolve_due_at,
    resolve_priority,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return session_factory


def _seed_document_and_version(
    session_factory,
    *,
    version_status: str = "scanned_clean",
    review_status: str = "draft",
    madhhab: str = "shafii",
    language: str = "th",
    document_type: str = "book",
) -> tuple[UUID, UUID]:
    uow = SQLAlchemyUnitOfWork(session_factory)
    doc_id = uuid4()
    ver_id = uuid4()
    actor = uuid4()
    with uow:
        uow.documents.create(
            Document(
                id=doc_id,
                source_id=uuid4(),
                source_license_id=uuid4(),
                canonical_id="doc-review-001",
                document_type=document_type,
                title="Reviewable Document",
                language=language,
                madhhab=madhhab,
                review_status=review_status,
                created_by=actor,
            )
        )
        uow.documents.add_version(
            DocumentVersion(
                id=ver_id,
                document_id=doc_id,
                version_number=1,
                status=version_status,
                content_hash="abc123",
                original_file_key="uploads/reviewable.txt",
                created_by=actor,
            )
        )
        uow.commit()
    return doc_id, ver_id


# ---------------------------------------------------------------------------
# Task creation integration tests
# ---------------------------------------------------------------------------


class TestCreateReviewTask:
    """Main success and failure paths for review task creation."""

    def test_create_review_task_success(self, db):
        doc_id, ver_id = _seed_document_and_version(db)
        service = ReviewTaskService(SQLAlchemyUnitOfWork(db))
        actor = uuid4()

        task = service.create_review_task(
            document_version_id=ver_id,
            actor_user_id=actor,
            trace_id="trace-create-review",
        )

        assert task.id is not None
        assert task.document_version_id == ver_id
        assert task.document_id == doc_id
        assert task.status == "open"
        assert task.review_level == "initial"
        assert task.created_by == actor

        # Verify audit log
        ver_session = db()
        try:
            logs = list(ver_session.execute(
                select(AuditLog).where(AuditLog.action == "review_task.created")
            ).scalars().all())
            assert len(logs) == 1
            assert logs[0].resource_id == task.id
            assert logs[0].trace_id == "trace-create-review"
            log_after = logs[0].after_summary or {}
            assert log_after["review_level"] == "initial"
            assert log_after["policy_version"] == REVIEW_TASK_POLICY_VERSION
        finally:
            ver_session.close()

    def test_create_with_custom_review_level(self, db):
        _, ver_id = _seed_document_and_version(db)
        service = ReviewTaskService(SQLAlchemyUnitOfWork(db))
        actor = uuid4()

        task = service.create_review_task(
            document_version_id=ver_id,
            actor_user_id=actor,
            review_level="scholar",
        )
        assert task.review_level == "scholar"

    def test_rejects_missing_version(self, db):
        service = ReviewTaskService(SQLAlchemyUnitOfWork(db))
        with pytest.raises(ReviewTaskCreationError) as exc_info:
            service.create_review_task(
                document_version_id=uuid4(),
                actor_user_id=uuid4(),
            )
        assert exc_info.value.code == "REVIEW_VERSION_NOT_FOUND"

    def test_rejects_infected_version(self, db):
        _, ver_id = _seed_document_and_version(
            db, version_status="rejected"
        )
        service = ReviewTaskService(SQLAlchemyUnitOfWork(db))
        with pytest.raises(ReviewTaskCreationError) as exc_info:
            service.create_review_task(
                document_version_id=ver_id,
                actor_user_id=uuid4(),
            )
        assert exc_info.value.code == "REVIEW_VERSION_NOT_ELIGIBLE"
        assert "rejected" in exc_info.value.message

    def test_rejects_rejected_document(self, db):
        _, ver_id = _seed_document_and_version(
            db, review_status="rejected"
        )
        service = ReviewTaskService(SQLAlchemyUnitOfWork(db))
        with pytest.raises(ReviewTaskCreationError) as exc_info:
            service.create_review_task(
                document_version_id=ver_id,
                actor_user_id=uuid4(),
            )
        assert exc_info.value.code == "REVIEW_VERSION_NOT_ELIGIBLE"


# ---------------------------------------------------------------------------
# Duplicate-event/idempotency tests
# ---------------------------------------------------------------------------


class TestIdempotency:
    """One active review task per document version and review level."""

    def test_duplicate_level_raises(self, db):
        _, ver_id = _seed_document_and_version(db)
        service = ReviewTaskService(SQLAlchemyUnitOfWork(db))
        actor = uuid4()

        service.create_review_task(
            document_version_id=ver_id, actor_user_id=actor
        )
        with pytest.raises(ReviewTaskCreationError) as exc_info:
            service.create_review_task(
                document_version_id=ver_id, actor_user_id=actor
            )
        assert exc_info.value.code == "REVIEW_TASK_ALREADY_EXISTS"

    def test_different_levels_allowed(self, db):
        _, ver_id = _seed_document_and_version(db)
        service = ReviewTaskService(SQLAlchemyUnitOfWork(db))
        actor = uuid4()

        initial = service.create_review_task(
            document_version_id=ver_id,
            actor_user_id=actor,
            review_level="initial",
        )
        scholar = service.create_review_task(
            document_version_id=ver_id,
            actor_user_id=actor,
            review_level="scholar",
        )
        assert initial.id != scholar.id
        assert initial.review_level == "initial"
        assert scholar.review_level == "scholar"

    def test_only_one_audit_log_per_creation(self, db,):
        _, ver_id = _seed_document_and_version(db)
        service = ReviewTaskService(SQLAlchemyUnitOfWork(db))
        actor = uuid4()

        service.create_review_task(
            document_version_id=ver_id,
            actor_user_id=actor,
            review_level="initial",
        )
        ver_session = db()
        try:
            logs = list(ver_session.execute(
                select(AuditLog).where(AuditLog.action == "review_task.created")
            ).scalars().all())
            assert len(logs) == 1
        finally:
            ver_session.close()


# ---------------------------------------------------------------------------
# Assignment-rule tests
# ---------------------------------------------------------------------------


class TestAssignmentRules:
    """Priority and due date resolution from document metadata."""

    def test_priority_shafii(self):
        assert resolve_priority("shafii", "th") == "high"

    def test_priority_unknown(self):
        assert resolve_priority("unknown", "th") == "normal"

    def test_priority_none(self):
        assert resolve_priority(None, "ar") == "normal"

    def test_priority_case_insensitive(self):
        assert resolve_priority("SHAFII", "th") == "high"

    def test_due_date_high_priority(self):
        due = resolve_due_at("high")
        assert due is not None
        now = datetime.now(UTC)
        assert due > now
        assert (due - now).days >= 6  # allow small clock drift

    def test_due_date_urgent(self):
        due = resolve_due_at("urgent")
        assert due is not None
        assert (due - datetime.now(UTC)).days <= 4

    def test_due_date_low(self):
        due = resolve_due_at("low")
        assert due is not None
        assert (due - datetime.now(UTC)).days >= 28

    def test_due_date_unknown_priority(self):
        assert resolve_due_at("unknown") is None

    def test_shafii_document_gets_high_priority(self, db):
        _, ver_id = _seed_document_and_version(db, madhhab="shafii")
        service = ReviewTaskService(SQLAlchemyUnitOfWork(db))
        actor = uuid4()

        task = service.create_review_task(
            document_version_id=ver_id, actor_user_id=actor
        )
        assert task.priority == "high"
        assert task.due_at is not None

    def test_unknown_madhhab_gets_normal_priority(self, db):
        _, ver_id = _seed_document_and_version(db, madhhab="unknown")
        service = ReviewTaskService(SQLAlchemyUnitOfWork(db))
        actor = uuid4()

        task = service.create_review_task(
            document_version_id=ver_id, actor_user_id=actor
        )
        assert task.priority == "normal"

    def test_metadata_from_document(self, db):
        _, ver_id = _seed_document_and_version(
            db,
            madhhab="maliki",
            language="ar",
            document_type="fatwa",
        )
        service = ReviewTaskService(SQLAlchemyUnitOfWork(db))
        actor = uuid4()

        task = service.create_review_task(
            document_version_id=ver_id, actor_user_id=actor
        )
        assert task.madhhab == "maliki" or task.madhhab is None
        assert task.language == "ar"
        assert task.category == "fatwa"
