from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import (
    Answer,
    Base,
    Conversation,
    Document,
    DocumentVersion,
    Feedback,
    Message,
    ReviewTask,
    User,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.review_queue import ReviewQueueQuery, ReviewQueueService


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _seed_user(
    session_factory,
    *,
    email: str,
    language: str = "th",
    madhhab: str = "shafii",
) -> UUID:
    user_id = uuid4()
    with session_factory() as session:
        session.add(
            User(
                id=user_id,
                email=email,
                display_name=email,
                password_hash=None,
                status="active",
                preferred_language=language,
                preferred_madhhab=madhhab,
            )
        )
        session.commit()
    return user_id


def _seed_task(
    session_factory,
    *,
    reviewer_id: UUID,
    status: str = "open",
    assigned_to: UUID | None = None,
    review_status: str = "draft",
    due_at: datetime | None = None,
    title: str = "เอกสารทดสอบ",
) -> UUID:
    document_id = uuid4()
    version_id = uuid4()
    task_id = uuid4()
    created_by = reviewer_id
    with session_factory() as session:
        session.add(
            Document(
                id=document_id,
                source_id=uuid4(),
                source_license_id=uuid4(),
                canonical_id=f"doc-{document_id.hex[:8]}",
                document_type="book",
                title=title,
                language="th",
                madhhab="shafii",
                review_status=review_status,
                created_by=created_by,
            )
        )
        session.add(
            DocumentVersion(
                id=version_id,
                document_id=document_id,
                version_number=1,
                status="parsed",
                content_hash="hash",
                original_file_key="private/test.pdf",
                extracted_text="preview text",
                created_by=created_by,
            )
        )
        session.add(
            ReviewTask(
                id=task_id,
                document_version_id=version_id,
                document_id=document_id,
                assigned_to=assigned_to,
                review_level="initial",
                status=status,
                priority="high",
                category="book",
                language="th",
                madhhab="shafii",
                due_at=due_at,
                created_by=created_by,
            )
        )
        session.commit()
    return task_id


def _seed_feedback(session_factory, *, user_id: UUID) -> UUID:
    conversation_id = uuid4()
    message_id = uuid4()
    answer_id = uuid4()
    feedback_id = uuid4()
    with session_factory() as session:
        session.add(
            Conversation(
                id=conversation_id,
                user_id=user_id,
                title="ถาม",
                language="th",
                madhhab="shafii",
            )
        )
        session.add(
            Message(
                id=message_id,
                conversation_id=conversation_id,
                sender_type="assistant",
                body="answer",
                body_hash="hash",
                metadata_json={},
            )
        )
        session.add(
            Answer(
                id=answer_id,
                message_id=message_id,
                retrieval_run_id=uuid4(),
                model_configuration_id=uuid4(),
                prompt_version_id=uuid4(),
                policy_version_id=uuid4(),
                risk_level="low",
                madhhab="shafii",
                answer_json={"answer": "ตอบ"},
                confidence_level="high",
                evidence_sufficient=True,
            )
        )
        session.add(
            Feedback(
                id=feedback_id,
                user_id=user_id,
                answer_id=answer_id,
                citation_id=None,
                category="incorrect_answer",
                body="note",
                status="open",
            )
        )
        session.commit()
    return feedback_id


def test_dashboard_counts_and_feedback_work() -> None:
    session_factory = _db()
    reviewer_id = _seed_user(session_factory, email="reviewer@example.test")
    _seed_user(session_factory, email="reporter@example.test")

    _seed_task(session_factory, reviewer_id=reviewer_id, status="open", assigned_to=None)
    _seed_task(
        session_factory,
        reviewer_id=reviewer_id,
        status="in_progress",
        assigned_to=reviewer_id,
        due_at=datetime.now(UTC) - timedelta(days=1),
        title="งานเลยกำหนด",
    )
    _seed_task(
        session_factory,
        reviewer_id=reviewer_id,
        status="completed",
        review_status="changes_requested",
        title="งานขอแก้ไข",
    )
    _seed_feedback(session_factory, user_id=reviewer_id)

    service = ReviewQueueService(SQLAlchemyUnitOfWork(session_factory))
    dashboard = service.get_dashboard(
        ReviewQueueQuery(limit=10, offset=0),
        actor_user_id=reviewer_id,
        principal_roles=frozenset({"reviewer"}),
        feedback_limit=5,
    )

    assert dashboard.summary.total_visible_count == 3
    assert dashboard.summary.pending_count == 1
    assert dashboard.summary.assigned_count == 1
    assert dashboard.summary.overdue_count == 1
    assert dashboard.summary.changes_requested_count == 1
    assert dashboard.summary.feedback_open_count == 1
    assert len(dashboard.queue.tasks) == 3
    assert len(dashboard.feedback_items) == 1
    assert dashboard.feedback_items[0].category == "incorrect_answer"


def test_dashboard_filters_assigned_queue() -> None:
    session_factory = _db()
    reviewer_id = _seed_user(session_factory, email="reviewer2@example.test")
    other_id = _seed_user(session_factory, email="other@example.test")
    mine = _seed_task(
        session_factory,
        reviewer_id=reviewer_id,
        status="in_progress",
        assigned_to=reviewer_id,
        title="งานของฉัน",
    )
    _seed_task(
        session_factory,
        reviewer_id=reviewer_id,
        status="in_progress",
        assigned_to=other_id,
        title="งานคนอื่น",
    )

    service = ReviewQueueService(SQLAlchemyUnitOfWork(session_factory))
    dashboard = service.get_dashboard(
        ReviewQueueQuery(assigned_to=reviewer_id, limit=10, offset=0),
        actor_user_id=reviewer_id,
        principal_roles=frozenset({"reviewer"}),
    )

    assert [task.id for task in dashboard.queue.tasks] == [mine]


def test_dashboard_hides_feedback_without_feedback_read_permission() -> None:
    session_factory = _db()
    translator_id = _seed_user(session_factory, email="translator@example.test")
    _seed_task(session_factory, reviewer_id=translator_id, status="open", assigned_to=None)
    _seed_feedback(session_factory, user_id=translator_id)

    service = ReviewQueueService(SQLAlchemyUnitOfWork(session_factory))
    dashboard = service.get_dashboard(
        ReviewQueueQuery(limit=10, offset=0),
        actor_user_id=translator_id,
        principal_roles=frozenset({"translator"}),
        feedback_limit=5,
    )

    assert dashboard.summary.total_visible_count == 1
    assert dashboard.summary.feedback_open_count == 0
    assert dashboard.feedback_items == []
