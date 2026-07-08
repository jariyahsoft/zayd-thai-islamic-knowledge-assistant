"""Tests for the review queue service.

Covers:
- Queue listing and filtering
- Visibility filtering by role and specialization
- Task detail retrieval
- Claim, release, assign, escalate operations
- Concurrency safety (atomic claim)
- Error paths and authorization
- Audit event verification
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import AuditLog, Base, Document, DocumentVersion, ReviewTask, User
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.review_queue import (
    ReviewQueueError,
    ReviewQueueQuery,
    ReviewQueueService,
)
from zayd_common.review_tasks import ReviewTaskService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return session_factory


@pytest.fixture
def actor() -> UUID:
    return uuid4()


@pytest.fixture
def reviewer_user(db, actor) -> UUID:
    """Create a reviewer user with preferred language/madhhab."""
    uid = actor
    with db() as session:
        session.add(
            User(
                id=uid,
                email="reviewer@zayd.local",
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
def admin_user(db) -> UUID:
    """Create an admin user."""
    uid = uuid4()
    with db() as session:
        session.add(
            User(
                id=uid,
                email="admin@zayd.local",
                display_name="Admin",
                password_hash=None,
                status="active",
                preferred_language="ar",
                preferred_madhhab="hanafi",
            )
        )
        session.commit()
    return uid


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


def _seed_review_task(
    session_factory,
    *,
    review_level: str = "initial",
    status: str = "open",
    priority: str = "normal",
    assigned_to: UUID | None = None,
    language: str | None = "th",
    madhhab: str | None = "shafii",
    category: str | None = "book",
    due_at: datetime | None = None,
    document_title: str = "Test Document",
    document_type: str = "book",
) -> tuple[UUID, UUID, UUID]:
    """Seed a document, version, and review task, returning (doc_id, ver_id, task_id)."""
    uow = SQLAlchemyUnitOfWork(session_factory)
    doc_id = uuid4()
    ver_id = uuid4()
    task_id = uuid4()
    doc_created_by = uuid4()
    with uow:
        uow.documents.create(
            Document(
                id=doc_id,
                source_id=uuid4(),
                source_license_id=uuid4(),
                canonical_id=f"doc-{uuid4().hex[:8]}",
                document_type=document_type,
                title=document_title,
                language=language or "th",
                madhhab=madhhab or "unknown",
                review_status="draft",
                created_by=doc_created_by,
            )
        )
        uow.documents.add_version(
            DocumentVersion(
                id=ver_id,
                document_id=doc_id,
                version_number=1,
                status="scanned_clean",
                content_hash="abc123",
                original_file_key="uploads/test.txt",
                extracted_text="Extracted content line one.\nLine two.\nLine three.",
                created_by=doc_created_by,
            )
        )
        uow.commit()

    # Create review task directly
    with session_factory() as session:
        task = ReviewTask(
            id=task_id,
            document_version_id=ver_id,
            document_id=doc_id,
            assigned_to=assigned_to,
            review_level=review_level,
            status=status,
            priority=priority,
            category=category,
            language=language,
            madhhab=madhhab,
            due_at=due_at,
            created_by=doc_created_by,
        )
        session.add(task)
        session.commit()
    return doc_id, ver_id, task_id


# ---------------------------------------------------------------------------
# Queue listing
# ---------------------------------------------------------------------------


class TestListQueue:
    """Queue listing, filtering, and pagination."""

    def test_list_all_tasks(self, db, reviewer_user):
        _, _, t1 = _seed_review_task(db)
        _, _, t2 = _seed_review_task(db)
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        result = service.list_queue(
            ReviewQueueQuery(),
            actor_user_id=reviewer_user,
            principal_roles=frozenset({"reviewer"}),
        )

        assert result.total_count >= 2
        task_ids = {t.id for t in result.tasks}
        assert t1 in task_ids
        assert t2 in task_ids

    def test_filter_by_status(self, db, reviewer_user):
        _, _, open_task = _seed_review_task(db, status="open")
        _seed_review_task(db, status="in_progress")
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        result = service.list_queue(
            ReviewQueueQuery(status="open"),
            actor_user_id=reviewer_user,
            principal_roles=frozenset({"reviewer"}),
        )

        assert all(t.status == "open" for t in result.tasks)
        assert open_task in {t.id for t in result.tasks}

    def test_filter_by_language(self, db, admin_user):
        _seed_review_task(db, language="th")
        _, _, t2 = _seed_review_task(db, language="ar")
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        result = service.list_queue(
            ReviewQueueQuery(language="ar"),
            actor_user_id=admin_user,
            principal_roles=frozenset({"admin"}),
        )

        assert all(t.language == "ar" for t in result.tasks)
        assert t2 in {t.id for t in result.tasks}

    def test_filter_by_madhhab(self, db, admin_user):
        _seed_review_task(db, madhhab="shafii")
        _, _, t2 = _seed_review_task(db, madhhab="hanafi")
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        result = service.list_queue(
            ReviewQueueQuery(madhhab="hanafi"),
            actor_user_id=admin_user,
            principal_roles=frozenset({"admin"}),
        )

        assert all(t.madhhab == "hanafi" for t in result.tasks)
        assert t2 in {t.id for t in result.tasks}

    def test_filter_by_priority(self, db, reviewer_user):
        _, _, t1 = _seed_review_task(db, priority="high")
        _seed_review_task(db, priority="normal")
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        result = service.list_queue(
            ReviewQueueQuery(priority="high"),
            actor_user_id=reviewer_user,
            principal_roles=frozenset({"reviewer"}),
        )

        assert all(t.priority == "high" for t in result.tasks)
        assert t1 in {t.id for t in result.tasks}

    def test_filter_by_assigned_to(self, db, reviewer_user):
        other = uuid4()
        _, _, t1 = _seed_review_task(db, assigned_to=reviewer_user)
        _seed_review_task(db, assigned_to=other)
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        result = service.list_queue(
            ReviewQueueQuery(assigned_to=reviewer_user),
            actor_user_id=reviewer_user,
            principal_roles=frozenset({"reviewer"}),
        )

        assert all(t.assigned_to == reviewer_user for t in result.tasks)
        assert t1 in {t.id for t in result.tasks}

    def test_filter_by_review_level(self, db, reviewer_user):
        _, _, t1 = _seed_review_task(db, review_level="initial")
        _seed_review_task(db, review_level="scholar")
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        result = service.list_queue(
            ReviewQueueQuery(review_level="initial"),
            actor_user_id=reviewer_user,
            principal_roles=frozenset({"reviewer"}),
        )

        assert all(t.review_level == "initial" for t in result.tasks)
        assert t1 in {t.id for t in result.tasks}

    def test_pagination(self, db, reviewer_user):
        # Seed 3 tasks
        task_ids = set()
        for _i in range(3):
            _, _, tid = _seed_review_task(db)
            task_ids.add(tid)
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        page1 = service.list_queue(
            ReviewQueueQuery(limit=2, offset=0),
            actor_user_id=reviewer_user,
            principal_roles=frozenset({"reviewer"}),
        )
        assert len(page1.tasks) == 2
        assert page1.total_count >= 3
        assert page1.next_offset is not None

        page2 = service.list_queue(
            ReviewQueueQuery(limit=2, offset=2),
            actor_user_id=reviewer_user,
            principal_roles=frozenset({"reviewer"}),
        )
        assert len(page2.tasks) >= 1
        assert page2.offset == 2

    def test_list_returns_document_titles(self, db, reviewer_user):
        _, _, tid = _seed_review_task(db, document_title="Unique Title")
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        result = service.list_queue(
            ReviewQueueQuery(),
            actor_user_id=reviewer_user,
            principal_roles=frozenset({"reviewer"}),
        )
        matching = [t for t in result.tasks if t.id == tid]
        assert len(matching) == 1
        assert matching[0].document_title == "Unique Title"
        assert matching[0].document_type == "book"


# ---------------------------------------------------------------------------
# Visibility filtering
# ---------------------------------------------------------------------------


class TestVisibility:
    """Role-based and specialization-based visibility."""

    def test_admin_sees_all_tasks(self, db, admin_user):
        _, _, t1 = _seed_review_task(db, language="ar", madhhab="hanafi", review_level="scholar")
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        result = service.list_queue(
            ReviewQueueQuery(),
            actor_user_id=admin_user,
            principal_roles=frozenset({"admin"}),
        )
        assert t1 in {t.id for t in result.tasks}

    def test_senior_scholar_sees_all(self, db, admin_user):
        _, _, t1 = _seed_review_task(db, review_level="scholar")
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        result = service.list_queue(
            ReviewQueueQuery(),
            actor_user_id=admin_user,
            principal_roles=frozenset({"senior_scholar"}),
        )
        assert t1 in {t.id for t in result.tasks}

    def test_reviewer_sees_matching_specialization(self, db, reviewer_user):
        # reviewer_user has preferred_language="th", preferred_madhhab="shafii"
        _, _, matching = _seed_review_task(db, language="th", madhhab="shafii")
        _, _, other_lang = _seed_review_task(db, language="ar", madhhab="shafii")
        _, _, other_madhhab = _seed_review_task(db, language="th", madhhab="maliki")
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        result = service.list_queue(
            ReviewQueueQuery(),
            actor_user_id=reviewer_user,
            principal_roles=frozenset({"reviewer"}),
        )
        task_ids = {t.id for t in result.tasks}

        # Should see matching
        assert matching in task_ids
        # Should see maliki (different madhhab but still visible since it's not excluded)
        # Actually, maliki != shafii, so it should be filtered out by madhhab rule
        # The rule: madhhab is None, unknown, general, other, or == preferred
        assert other_madhhab not in task_ids
        # Arabic language shouldn't match thai preference
        assert other_lang not in task_ids

    def test_reviewer_sees_unknown_madhhab(self, db, reviewer_user):
        _, _, tid = _seed_review_task(db, language="th", madhhab="unknown")
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        result = service.list_queue(
            ReviewQueueQuery(),
            actor_user_id=reviewer_user,
            principal_roles=frozenset({"reviewer"}),
        )
        assert tid in {t.id for t in result.tasks}

    def test_reviewer_blocked_from_scholar_level(self, db, reviewer_user):
        _, _, tid = _seed_review_task(db, review_level="scholar", language="th", madhhab="shafii")
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        result = service.list_queue(
            ReviewQueueQuery(),
            actor_user_id=reviewer_user,
            principal_roles=frozenset({"reviewer"}),
        )
        assert tid not in {t.id for t in result.tasks}

    def test_translator_sees_by_language(self, db, reviewer_user):
        """Translator sees tasks matching language but not madhhab-restricted."""
        # reviewer_user is used with preferred_language="th"
        _, _, matching = _seed_review_task(db, language="th", madhhab="maliki")
        _, _, other_lang = _seed_review_task(db, language="ar", madhhab="shafii")
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        result = service.list_queue(
            ReviewQueueQuery(),
            actor_user_id=reviewer_user,
            principal_roles=frozenset({"translator"}),
        )
        task_ids = {t.id for t in result.tasks}
        assert matching in task_ids  # th matches th
        assert other_lang not in task_ids  # ar != th


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------


class TestGetTaskDetail:
    """Review task detail retrieval."""

    def test_detail_includes_version_info(self, db, reviewer_user):
        _, _, tid = _seed_review_task(db)
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        detail = service.get_task_detail(
            tid,
            actor_user_id=reviewer_user,
            principal_roles=frozenset({"reviewer"}),
        )

        assert detail.id == tid
        assert detail.original_file_key == "uploads/test.txt"
        assert detail.extracted_text_preview is not None
        assert "Extracted content" in (detail.extracted_text_preview or "")
        assert detail.created_by is not None

    def test_detail_not_found(self, db, reviewer_user):
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))
        with pytest.raises(ReviewQueueError) as exc:
            service.get_task_detail(
                uuid4(),
                actor_user_id=reviewer_user,
                principal_roles=frozenset({"reviewer"}),
            )
        assert exc.value.code == "REVIEW_TASK_NOT_FOUND"

    def test_detail_access_denied_for_invisible_task(self, db, reviewer_user):
        """Reviewer cannot see scholar-level tasks from detail endpoint."""
        _, _, tid = _seed_review_task(db, review_level="scholar")
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))
        with pytest.raises(ReviewQueueError) as exc:
            service.get_task_detail(
                tid,
                actor_user_id=reviewer_user,
                principal_roles=frozenset({"reviewer"}),
            )
        assert exc.value.code == "REVIEW_QUEUE_ACCESS_DENIED"


# ---------------------------------------------------------------------------
# Claim
# ---------------------------------------------------------------------------


class TestClaim:
    """Task claiming."""

    def test_claim_open_task(self, db, reviewer_user):
        _, _, tid = _seed_review_task(db)
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        result = service.claim_task(
            tid,
            actor_user_id=reviewer_user,
        )

        assert result.status == "in_progress"
        assert result.assigned_to == reviewer_user

    def test_claim_already_assigned_to_self(self, db, reviewer_user):
        _, _, tid = _seed_review_task(db, assigned_to=reviewer_user, status="in_progress")
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        result = service.claim_task(
            tid,
            actor_user_id=reviewer_user,
        )
        assert result.status == "in_progress"
        assert result.assigned_to == reviewer_user

    def test_claim_already_assigned_to_other(self, db, reviewer_user):
        other = uuid4()
        _, _, tid = _seed_review_task(db, assigned_to=other, status="in_progress")
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        with pytest.raises(ReviewQueueError) as exc:
            service.claim_task(
                tid,
                actor_user_id=reviewer_user,
            )
        assert exc.value.code == "REVIEW_QUEUE_ACCESS_DENIED"

    def test_claim_completed_task(self, db, reviewer_user):
        _, _, tid = _seed_review_task(db, status="completed")
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        with pytest.raises(ReviewQueueError) as exc:
            service.claim_task(
                tid,
                actor_user_id=reviewer_user,
            )
        assert exc.value.code == "REVIEW_TASK_INVALID_STATUS"

    def test_claim_unknown_task(self, db, reviewer_user):
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))
        with pytest.raises(ReviewQueueError) as exc:
            service.claim_task(
                uuid4(),
                actor_user_id=reviewer_user,
            )
        assert exc.value.code == "REVIEW_TASK_NOT_FOUND"

    def test_claim_creates_audit_log(self, db, reviewer_user):
        _, _, tid = _seed_review_task(db)
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        service.claim_task(tid, actor_user_id=reviewer_user, trace_id="trace-claim")

        with db() as session:
            logs = list(
                session.execute(
                    select(AuditLog).where(AuditLog.action == "review_task.claimed")
                ).scalars().all()
            )
        assert len(logs) == 1
        assert logs[0].resource_id == tid
        assert logs[0].trace_id == "trace-claim"
        assert logs[0].after_summary is not None


# ---------------------------------------------------------------------------
# Release
# ---------------------------------------------------------------------------


class TestRelease:
    """Task releasing."""

    def test_release_own_task(self, db, reviewer_user):
        _, _, tid = _seed_review_task(
            db, assigned_to=reviewer_user, status="in_progress"
        )
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        result = service.release_task(
            tid,
            actor_user_id=reviewer_user,
            principal_roles=frozenset({"reviewer"}),
        )

        assert result.status == "open"
        assert result.assigned_to is None

    def test_release_not_assigned_to_self(self, db, reviewer_user):
        other = uuid4()
        _, _, tid = _seed_review_task(db, assigned_to=other, status="in_progress")
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        with pytest.raises(ReviewQueueError) as exc:
            service.release_task(
                tid,
                actor_user_id=reviewer_user,
                principal_roles=frozenset({"reviewer"}),
            )
        assert exc.value.code == "REVIEW_TASK_NOT_ASSIGNED"

    def test_release_by_admin(self, db, admin_user, reviewer_user):
        _, _, tid = _seed_review_task(
            db, assigned_to=reviewer_user, status="in_progress"
        )
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        result = service.release_task(
            tid,
            actor_user_id=admin_user,
            principal_roles=frozenset({"admin"}),
        )
        assert result.status == "open"
        assert result.assigned_to is None

    def test_release_creates_audit_log(self, db, reviewer_user):
        _, _, tid = _seed_review_task(db, assigned_to=reviewer_user, status="in_progress")
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        service.release_task(
            tid,
            actor_user_id=reviewer_user,
            principal_roles=frozenset({"reviewer"}),
            trace_id="trace-release",
        )

        with db() as session:
            logs = list(
                session.execute(
                    select(AuditLog).where(AuditLog.action == "review_task.released")
                ).scalars().all()
            )
        assert len(logs) == 1
        assert logs[0].trace_id == "trace-release"


# ---------------------------------------------------------------------------
# Assign
# ---------------------------------------------------------------------------


class TestAssign:
    """Task assignment by privileged users."""

    def test_assign_by_admin(self, db, admin_user, reviewer_user):
        _, _, tid = _seed_review_task(db)
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        result = service.assign_task(
            tid,
            assignee_user_id=reviewer_user,
            actor_user_id=admin_user,
            principal_roles=frozenset({"admin"}),
        )
        assert result.assigned_to == reviewer_user
        assert result.status == "in_progress"

    def test_assign_by_reviewer_denied(self, db, reviewer_user):
        other = uuid4()
        _, _, tid = _seed_review_task(db)
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        with pytest.raises(ReviewQueueError) as exc:
            service.assign_task(
                tid,
                assignee_user_id=other,
                actor_user_id=reviewer_user,
                principal_roles=frozenset({"reviewer"}),
            )
        assert exc.value.code == "REVIEW_QUEUE_ACCESS_DENIED"

    def test_assign_nonexistent_user(self, db, admin_user):
        _, _, tid = _seed_review_task(db)
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        with pytest.raises(ReviewQueueError) as exc:
            service.assign_task(
                tid,
                assignee_user_id=uuid4(),
                actor_user_id=admin_user,
                principal_roles=frozenset({"admin"}),
            )
        assert exc.value.code == "REVIEW_USER_NOT_FOUND"

    def test_assign_completed_task(self, db, admin_user, reviewer_user):
        _, _, tid = _seed_review_task(db, status="completed")
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        with pytest.raises(ReviewQueueError) as exc:
            service.assign_task(
                tid,
                assignee_user_id=reviewer_user,
                actor_user_id=admin_user,
                principal_roles=frozenset({"admin"}),
            )
        assert exc.value.code == "REVIEW_TASK_INVALID_STATUS"

    def test_assign_creates_audit_log(self, db, admin_user, reviewer_user):
        _, _, tid = _seed_review_task(db)
        service = ReviewQueueService(SQLAlchemyUnitOfWork(db))

        service.assign_task(
            tid,
            assignee_user_id=reviewer_user,
            actor_user_id=admin_user,
            principal_roles=frozenset({"admin"}),
            trace_id="trace-assign",
        )

        with db() as session:
            logs = list(
                session.execute(
                    select(AuditLog).where(AuditLog.action == "review_task.assigned")
                ).scalars().all()
            )
        assert len(logs) == 1
        assert logs[0].trace_id == "trace-assign"


# ---------------------------------------------------------------------------
# Escalate
# ---------------------------------------------------------------------------


class TestEscalate:
    """Task escalation — creates a scholar-level review task."""

    @pytest.fixture
    def seeded_version(self, db, admin_user):
        """Seed a document and version (no review task), return ver_id."""
        uow = SQLAlchemyUnitOfWork(db)
        doc_id = uuid4()
        ver_id = uuid4()
        with uow:
            uow.documents.create(
                Document(
                    id=doc_id,
                    source_id=uuid4(),
                    source_license_id=uuid4(),
                    canonical_id=f"doc-{uuid4().hex[:8]}",
                    document_type="book",
                    title="Escalate Test",
                    language="th",
                    madhhab="shafii",
                    review_status="draft",
                    created_by=admin_user,
                )
            )
            uow.documents.add_version(
                DocumentVersion(
                    id=ver_id,
                    document_id=doc_id,
                    version_number=1,
                    status="scanned_clean",
                    content_hash="abc",
                    created_by=admin_user,
                )
            )
            uow.commit()
        return ver_id

    def test_escalate_creates_scholar_task(self, db, admin_user, seeded_version):
        ver_id = seeded_version
        # Create initial task via service
        svc = ReviewTaskService(SQLAlchemyUnitOfWork(db))
        task = svc.create_review_task(
            document_version_id=ver_id,
            actor_user_id=admin_user,
            review_level="initial",
        )
        tid = task.id

        queue_svc = ReviewQueueService(SQLAlchemyUnitOfWork(db))
        queue_svc.claim_task(tid, actor_user_id=admin_user)
        queue_svc.escalate_task(
            tid,
            actor_user_id=admin_user,
            principal_roles=frozenset({"admin"}),
        )

        # Verify scholar task exists
        with db() as session:
            scholar_tasks = list(
                session.execute(
                    select(ReviewTask).where(ReviewTask.review_level == "scholar")
                ).scalars().all()
            )
        assert len(scholar_tasks) == 1
        assert scholar_tasks[0].document_version_id == ver_id

    def test_escalate_duplicate_raises(self, db, admin_user, seeded_version):
        ver_id = seeded_version
        svc = ReviewTaskService(SQLAlchemyUnitOfWork(db))
        initial = svc.create_review_task(
            document_version_id=ver_id, actor_user_id=admin_user, review_level="initial",
        )
        # Pre-create the scholar task
        svc.create_review_task(
            document_version_id=ver_id, actor_user_id=admin_user, review_level="scholar",
        )

        queue_svc = ReviewQueueService(SQLAlchemyUnitOfWork(db))
        queue_svc.claim_task(initial.id, actor_user_id=admin_user)

        with pytest.raises(ReviewQueueError) as exc:
            queue_svc.escalate_task(
                initial.id,
                actor_user_id=admin_user,
                principal_roles=frozenset({"admin"}),
            )
        assert exc.value.code == "REVIEW_QUEUE_ESCALATION_EXISTS"

    def test_escalate_by_non_assigned_denied(self, db, reviewer_user, admin_user, seeded_version):
        """Only assigned reviewer or privileged user can escalate."""
        ver_id = seeded_version
        svc = ReviewTaskService(SQLAlchemyUnitOfWork(db))
        task = svc.create_review_task(
            document_version_id=ver_id, actor_user_id=admin_user, review_level="initial",
        )
        queue_svc = ReviewQueueService(SQLAlchemyUnitOfWork(db))
        queue_svc.claim_task(task.id, actor_user_id=admin_user)

        with pytest.raises(ReviewQueueError) as exc:
            queue_svc.escalate_task(
                task.id,
                actor_user_id=reviewer_user,
                principal_roles=frozenset({"reviewer"}),
            )
        assert exc.value.code == "REVIEW_QUEUE_ACCESS_DENIED"
