from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.conversations import (
    NO_HISTORY_BODY,
    ConversationHistoryError,
    ConversationHistoryService,
)
from zayd_common.database.models import AuditLog, Base, Conversation, Message, User
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork


@pytest.fixture
def history_fixture() -> tuple[ConversationHistoryService, sessionmaker, User, User]:
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
    service = ConversationHistoryService(SQLAlchemyUnitOfWork(session_factory))
    with session_factory() as session:
        owner = session.get(User, owner_id)
        other = session.get(User, other_id)
        assert owner is not None and other is not None
        return service, session_factory, owner, other


def _add_conversation(
    session_factory: sessionmaker,
    *,
    user_id,
    title: str,
    body: str,
    no_history: bool = False,
) -> Conversation:
    conversation_id = uuid4()
    with session_factory() as session:
        conversation = Conversation(
            id=conversation_id,
            user_id=user_id,
            title=title,
            language="th",
            madhhab="shafii",
        )
        session.add(conversation)
        session.add(
            Message(
                conversation_id=conversation_id,
                sender_type="user",
                body=NO_HISTORY_BODY if no_history else body,
                body_hash="hash-user",
                metadata_json={"no_history": no_history},
            )
        )
        if not no_history:
            session.add(
                Message(
                    conversation_id=conversation_id,
                    sender_type="assistant",
                    body="คำตอบตัวอย่าง",
                    body_hash="hash-assistant",
                    metadata_json={"status": "completed"},
                )
            )
        session.commit()
        stored = session.get(Conversation, conversation_id)
        assert stored is not None
        return stored


def test_list_conversations_returns_only_owned_history_threads(
    history_fixture: tuple[ConversationHistoryService, sessionmaker, User, User],
) -> None:
    service, session_factory, owner, other = history_fixture
    owned = _add_conversation(
        session_factory,
        user_id=owner.id,
        title="ละหมาด",
        body="ละหมาดคืออะไร",
    )
    _add_conversation(
        session_factory,
        user_id=other.id,
        title="ซะกาต",
        body="ซะกาตคืออะไร",
    )
    _add_conversation(
        session_factory,
        user_id=owner.id,
        title="no-history",
        body="คำถามลับ",
        no_history=True,
    )

    result = service.list_conversations(user_id=owner.id)

    assert result.total_count == 1
    assert result.conversations[0].id == owned.id
    assert result.conversations[0].title == "ละหมาด"


def test_get_conversation_rejects_other_users_thread(
    history_fixture: tuple[ConversationHistoryService, sessionmaker, User, User],
) -> None:
    service, session_factory, owner, other = history_fixture
    foreign = _add_conversation(
        session_factory,
        user_id=other.id,
        title="ของคนอื่น",
        body="คำถามของคนอื่น",
    )

    with pytest.raises(ConversationHistoryError, match="not found"):
        service.get_conversation(user_id=owner.id, conversation_id=foreign.id)


def test_delete_conversation_soft_deletes_and_audits(
    history_fixture: tuple[ConversationHistoryService, sessionmaker, User, User],
) -> None:
    service, session_factory, owner, _other = history_fixture
    conversation = _add_conversation(
        session_factory,
        user_id=owner.id,
        title="ลบได้",
        body="คำถามที่จะลบ",
    )

    service.delete_conversation(
        user_id=owner.id,
        conversation_id=conversation.id,
        trace_id="trace-delete",
    )

    with session_factory() as session:
        stored = session.get(Conversation, conversation.id)
        assert stored is not None
        assert stored.deleted_at is not None
        audits = session.scalars(select(AuditLog)).all()
    assert len(audits) == 1
    assert audits[0].action == "conversations.delete"


def test_delete_all_conversations_removes_only_owned_history(
    history_fixture: tuple[ConversationHistoryService, sessionmaker, User, User],
) -> None:
    service, session_factory, owner, other = history_fixture
    _add_conversation(session_factory, user_id=owner.id, title="หนึ่ง", body="คำถามหนึ่ง")
    _add_conversation(session_factory, user_id=owner.id, title="สอง", body="คำถามสอง")
    _add_conversation(session_factory, user_id=other.id, title="ของคนอื่น", body="คำถามอื่น")

    result = service.delete_all_conversations(user_id=owner.id, trace_id="trace-delete-all")

    assert result.deleted_count == 2
    remaining = service.list_conversations(user_id=owner.id)
    assert remaining.total_count == 0