from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import Answer, AuditLog, Base, Conversation, Message, User
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.feedback import (
    FEEDBACK_RATE_LIMIT_MAX,
    FeedbackError,
    FeedbackService,
    FeedbackSubmit,
)


@pytest.fixture
def feedback_fixture() -> tuple[FeedbackService, sessionmaker, User, User, Answer]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    owner_id = uuid4()
    other_id = uuid4()
    with session_factory() as session:
        session.add(User(id=owner_id, email="owner@example.test", display_name="Owner"))
        session.add(User(id=other_id, email="other@example.test", display_name="Other"))
        session.commit()
    owner_answer = _add_answer(session_factory, user_id=owner_id)
    other_answer = _add_answer(session_factory, user_id=other_id)
    service = FeedbackService(SQLAlchemyUnitOfWork(session_factory))
    with session_factory() as session:
        owner = session.get(User, owner_id)
        other = session.get(User, other_id)
        assert owner is not None and other is not None
        return service, session_factory, owner, other, owner_answer, other_answer


def _add_answer(session_factory: sessionmaker, *, user_id) -> Answer:
    conversation_id = uuid4()
    message_id = uuid4()
    answer_id = uuid4()
    with session_factory() as session:
        session.add(
            Conversation(
                id=conversation_id,
                user_id=user_id,
                title="คำถาม",
                language="th",
                madhhab="shafii",
            )
        )
        session.add(
            Message(
                id=message_id,
                conversation_id=conversation_id,
                sender_type="assistant",
                body="คำตอบ",
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
                answer_json={"summary": "สรุป", "answer_th": "คำตอบ"},
                confidence_level="high",
                evidence_sufficient=True,
            )
        )
        session.commit()
        stored = session.get(Answer, answer_id)
        assert stored is not None
        return stored


def test_submit_feedback_creates_ticket_and_receipt(
    feedback_fixture: tuple[FeedbackService, sessionmaker, User, User, Answer, Answer],
) -> None:
    service, _session_factory, owner, _other, owner_answer, _other_answer = feedback_fixture
    result = service.submit_feedback(
        user_id=owner.id,
        submission=FeedbackSubmit(
            answer_id=owner_answer.id,
            category="incorrect_answer",
            notes="คำตอบไม่ตรงกับแหล่งอ้างอิง",
        ),
        trace_id="trace-feedback",
    )
    assert result.category == "incorrect_answer"
    assert result.receipt_message
    assert "trace" not in result.receipt_message.lower()


def test_submit_feedback_rejects_foreign_answer(
    feedback_fixture: tuple[FeedbackService, sessionmaker, User, User, Answer, Answer],
) -> None:
    service, _session_factory, owner, _other, _owner_answer, other_answer = feedback_fixture
    with pytest.raises(FeedbackError, match="not found"):
        service.submit_feedback(
            user_id=owner.id,
            submission=FeedbackSubmit(
                answer_id=other_answer.id,
                category="other",
            ),
        )


def test_submit_feedback_rate_limited(
    feedback_fixture: tuple[FeedbackService, sessionmaker, User, User, Answer, Answer],
) -> None:
    service, _session_factory, owner, _other, owner_answer, _other_answer = feedback_fixture
    for _ in range(FEEDBACK_RATE_LIMIT_MAX):
        service.submit_feedback(
            user_id=owner.id,
            submission=FeedbackSubmit(answer_id=owner_answer.id, category="other"),
        )
    with pytest.raises(FeedbackError, match="Too many"):
        service.submit_feedback(
            user_id=owner.id,
            submission=FeedbackSubmit(answer_id=owner_answer.id, category="other"),
        )


def test_submit_feedback_writes_audit_without_notes_body(
    feedback_fixture: tuple[FeedbackService, sessionmaker, User, User, Answer, Answer],
) -> None:
    service, session_factory, owner, _other, owner_answer, _other_answer = feedback_fixture
    service.submit_feedback(
        user_id=owner.id,
        submission=FeedbackSubmit(
            answer_id=owner_answer.id,
            category="citation_error",
            notes="secret user note",
        ),
    )
    with session_factory() as session:
        audit = session.scalar(select(AuditLog))
    assert audit is not None
    assert audit.action == "feedback.submit"
    assert audit.after_summary is not None
    assert audit.after_summary.get("notes_length") == len("secret user note")
    assert "secret user note" not in str(audit.after_summary)