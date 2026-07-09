from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import (
    Answer,
    AuditLog,
    Base,
    Conversation,
    Message,
    User,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.saved_answers import SavedAnswerError, SavedAnswerService


@pytest.fixture
def saved_fixture() -> tuple[SavedAnswerService, sessionmaker, User, User, Answer, Answer]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    owner_id = uuid4()
    other_id = uuid4()
    with session_factory() as session:
        session.add(
            User(
                id=owner_id,
                email="owner@example.test",
                display_name="Owner",
            )
        )
        session.add(
            User(
                id=other_id,
                email="other@example.test",
                display_name="Other",
            )
        )
        session.commit()
    owner_answer = _add_answer(session_factory, user_id=owner_id, summary="คำตอบของฉัน")
    other_answer = _add_answer(session_factory, user_id=other_id, summary="คำตอบของคนอื่น")
    service = SavedAnswerService(SQLAlchemyUnitOfWork(session_factory))
    with session_factory() as session:
        owner = session.get(User, owner_id)
        other = session.get(User, other_id)
        assert owner is not None and other is not None
        return service, session_factory, owner, other, owner_answer, other_answer


def _add_answer(session_factory: sessionmaker, *, user_id, summary: str) -> Answer:
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
                body=summary,
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
                answer_json={
                    "summary": summary,
                    "answer_th": summary,
                    "madhhab": "shafii",
                    "citations": [],
                },
                confidence_level="high",
                evidence_sufficient=True,
            )
        )
        session.commit()
        stored = session.get(Answer, answer_id)
        assert stored is not None
        return stored


def test_save_and_unsave_answer_for_owned_thread(
    saved_fixture: tuple[SavedAnswerService, sessionmaker, User, User, Answer, Answer],
) -> None:
    service, _session_factory, owner, _other, owner_answer, _other_answer = saved_fixture
    saved = service.save_answer(user_id=owner.id, answer_id=owner_answer.id, trace_id="trace-save")
    assert saved.answer_id == owner_answer.id

    listed = service.list_saved_answers(user_id=owner.id)
    assert listed.total_count == 1
    assert service.is_answer_saved(user_id=owner.id, answer_id=owner_answer.id)

    service.unsave_answer(
        user_id=owner.id,
        saved_answer_id=saved.id,
        trace_id="trace-unsave",
    )
    assert service.list_saved_answers(user_id=owner.id).total_count == 0


def test_save_answer_rejects_foreign_thread(
    saved_fixture: tuple[SavedAnswerService, sessionmaker, User, User, Answer, Answer],
) -> None:
    service, _session_factory, owner, _other, _owner_answer, other_answer = saved_fixture
    with pytest.raises(SavedAnswerError, match="not found"):
        service.save_answer(user_id=owner.id, answer_id=other_answer.id)


def test_saved_answer_warnings_include_invalidated_answer(
    saved_fixture: tuple[SavedAnswerService, sessionmaker, User, User, Answer, Answer],
) -> None:
    service, session_factory, owner, _other, owner_answer, _other_answer = saved_fixture
    with session_factory() as session:
        answer = session.get(Answer, owner_answer.id)
        assert answer is not None
        from datetime import UTC, datetime

        answer.invalidated_at = datetime.now(UTC)
        session.commit()

    saved = service.save_answer(user_id=owner.id, answer_id=owner_answer.id)
    assert "answer_invalidated" in saved.warnings


def test_save_answer_writes_audit_log(
    saved_fixture: tuple[SavedAnswerService, sessionmaker, User, User, Answer, Answer],
) -> None:
    service, session_factory, owner, _other, owner_answer, _other_answer = saved_fixture
    service.save_answer(user_id=owner.id, answer_id=owner_answer.id, trace_id="trace-audit")
    with session_factory() as session:
        audits = session.scalars(select(AuditLog)).all()
    assert len(audits) == 1
    assert audits[0].action == "saved_answers.save"