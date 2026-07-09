"""User-owned conversation history."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import func, or_, select

from zayd_common.database.models import Answer, AuditLog, Conversation, Message
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

NO_HISTORY_BODY = "[no-history]"
MAX_SEARCH_LENGTH = 200
MAX_LIST_LIMIT = 100
TITLE_MAX_LENGTH = 120
PREVIEW_MAX_LENGTH = 160

ConversationHistoryErrorCode = Literal[
    "CONVERSATION_NOT_FOUND",
    "CONVERSATION_INPUT_INVALID",
]


class ConversationHistoryError(Exception):
    def __init__(
        self,
        code: ConversationHistoryErrorCode,
        message: str,
        *,
        status_code: int = 404,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class ConversationSummaryPublic:
    id: UUID
    title: str | None
    language: str
    madhhab: str
    message_count: int
    preview: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ConversationMessagePublic:
    id: UUID
    sender_type: str
    body: str
    created_at: datetime
    answer: dict[str, Any] | None = None


@dataclass(frozen=True)
class ConversationDetailPublic:
    conversation: ConversationSummaryPublic
    messages: tuple[ConversationMessagePublic, ...]


@dataclass(frozen=True)
class ConversationListResult:
    conversations: tuple[ConversationSummaryPublic, ...]
    total_count: int
    limit: int
    offset: int
    next_offset: int | None


@dataclass(frozen=True)
class ConversationDeleteAllResult:
    deleted_count: int


class ConversationHistoryService:
    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self.uow = uow

    def list_conversations(
        self,
        *,
        user_id: UUID,
        query: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ConversationListResult:
        normalized_limit = _normalize_limit(limit)
        normalized_offset = _normalize_offset(offset)
        search = _normalize_search(query)

        with self.uow:
            session = self._session()
            base = _owned_history_conversations_stmt(user_id)
            if search:
                pattern = f"%{search}%"
                base = base.where(
                    or_(
                        Conversation.title.ilike(pattern),
                        Conversation.id.in_(
                            select(Message.conversation_id).where(
                                Message.sender_type == "user",
                                Message.deleted_at.is_(None),
                                Message.body != NO_HISTORY_BODY,
                                Message.body.ilike(pattern),
                            )
                        ),
                    )
                )

            total_count = session.scalar(select(func.count()).select_from(base.subquery())) or 0
            rows = session.scalars(
                base.order_by(Conversation.updated_at.desc())
                .limit(normalized_limit)
                .offset(normalized_offset)
            ).all()
            summaries = tuple(_summary_from_conversation(session, row) for row in rows)
            next_offset = (
                normalized_offset + normalized_limit
                if normalized_offset + normalized_limit < total_count
                else None
            )
            self.uow.commit()
            return ConversationListResult(
                conversations=summaries,
                total_count=total_count,
                limit=normalized_limit,
                offset=normalized_offset,
                next_offset=next_offset,
            )

    def get_conversation(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
    ) -> ConversationDetailPublic:
        with self.uow:
            session = self._session()
            conversation = self._get_owned_conversation(
                session,
                user_id=user_id,
                conversation_id=conversation_id,
            )
            if not _conversation_has_history(session, conversation.id):
                raise ConversationHistoryError(
                    "CONVERSATION_NOT_FOUND",
                    "Conversation was not found.",
                    status_code=404,
                )
            messages = session.scalars(
                select(Message)
                .where(
                    Message.conversation_id == conversation.id,
                    Message.deleted_at.is_(None),
                    Message.body != NO_HISTORY_BODY,
                )
                .order_by(Message.created_at.asc())
            ).all()
            answer_by_message = _answers_for_messages(session, messages)
            public_messages = tuple(
                ConversationMessagePublic(
                    id=message.id,
                    sender_type=message.sender_type,
                    body=message.body,
                    created_at=message.created_at,
                    answer=answer_by_message.get(message.id),
                )
                for message in messages
            )
            detail = ConversationDetailPublic(
                conversation=_summary_from_conversation(session, conversation),
                messages=public_messages,
            )
            self.uow.commit()
            return detail

    def delete_conversation(
        self,
        *,
        user_id: UUID,
        conversation_id: UUID,
        trace_id: str | None = None,
    ) -> None:
        with self.uow:
            session = self._session()
            conversation = self._get_owned_conversation(
                session,
                user_id=user_id,
                conversation_id=conversation_id,
            )
            now = datetime.now(UTC)
            conversation.deleted_at = now
            self._audit(
                actor_user_id=user_id,
                action="conversations.delete",
                resource_id=conversation.id,
                trace_id=trace_id,
                before_summary={"deleted_at": None},
                after_summary={"deleted_at": now.isoformat()},
            )
            self.uow.commit()

    def delete_all_conversations(
        self,
        *,
        user_id: UUID,
        trace_id: str | None = None,
    ) -> ConversationDeleteAllResult:
        with self.uow:
            session = self._session()
            conversations = session.scalars(_owned_history_conversations_stmt(user_id)).all()
            now = datetime.now(UTC)
            for conversation in conversations:
                conversation.deleted_at = now
            deleted_count = len(conversations)
            if deleted_count:
                self._audit(
                    actor_user_id=user_id,
                    action="conversations.delete_all",
                    resource_id=user_id,
                    trace_id=trace_id,
                    before_summary={"active_count": deleted_count},
                    after_summary={"deleted_count": deleted_count},
                )
            self.uow.commit()
            return ConversationDeleteAllResult(deleted_count=deleted_count)

    def _get_owned_conversation(
        self,
        session,
        *,
        user_id: UUID,
        conversation_id: UUID,
    ) -> Conversation:
        conversation = session.get(Conversation, conversation_id)
        if (
            conversation is None
            or conversation.deleted_at is not None
            or conversation.user_id != user_id
        ):
            raise ConversationHistoryError(
                "CONVERSATION_NOT_FOUND",
                "Conversation was not found.",
                status_code=404,
            )
        return conversation

    def _session(self):
        if self.uow.session is None:
            raise RuntimeError("Database session not initialised in UoW.")
        return self.uow.session

    def _audit(
        self,
        *,
        actor_user_id: UUID,
        action: str,
        resource_id: UUID,
        trace_id: str | None,
        before_summary: dict[str, Any],
        after_summary: dict[str, Any],
    ) -> None:
        if self.uow.session is None:
            return
        self.uow.session.add(
            AuditLog(
                actor_user_id=actor_user_id,
                action=action,
                resource_type="conversation",
                resource_id=resource_id,
                outcome="success",
                request_id=trace_id,
                trace_id=trace_id,
                before_summary=before_summary,
                after_summary=after_summary,
            )
        )


def truncate_conversation_title(value: str) -> str:
    normalized = " ".join(value.strip().split())
    if len(normalized) <= TITLE_MAX_LENGTH:
        return normalized
    return f"{normalized[: TITLE_MAX_LENGTH - 1].rstrip()}…"


def _owned_history_conversations_stmt(user_id: UUID):
    history_message_exists = (
        select(Message.id)
        .where(
            Message.conversation_id == Conversation.id,
            Message.deleted_at.is_(None),
            Message.body != NO_HISTORY_BODY,
        )
        .exists()
    )
    return select(Conversation).where(
        Conversation.user_id == user_id,
        Conversation.deleted_at.is_(None),
        history_message_exists,
    )


def _conversation_has_history(session, conversation_id: UUID) -> bool:
    message = session.scalar(
        select(Message.id)
        .where(
            Message.conversation_id == conversation_id,
            Message.deleted_at.is_(None),
            Message.body != NO_HISTORY_BODY,
        )
        .limit(1)
    )
    return message is not None


def _summary_from_conversation(session, conversation: Conversation) -> ConversationSummaryPublic:
    messages = session.scalars(
        select(Message)
        .where(
            Message.conversation_id == conversation.id,
            Message.deleted_at.is_(None),
            Message.body != NO_HISTORY_BODY,
        )
        .order_by(Message.created_at.asc())
    ).all()
    first_user = next((message for message in messages if message.sender_type == "user"), None)
    last_assistant = next(
        (message for message in reversed(messages) if message.sender_type == "assistant"),
        None,
    )
    title = conversation.title or (first_user.body if first_user else None)
    preview_source = last_assistant or first_user
    preview = _truncate_preview(preview_source.body) if preview_source else None
    return ConversationSummaryPublic(
        id=conversation.id,
        title=title,
        language=conversation.language,
        madhhab=conversation.madhhab,
        message_count=len(messages),
        preview=preview,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


def _answers_for_messages(session, messages: list[Message]) -> dict[UUID, dict[str, Any]]:
    assistant_messages = [message for message in messages if message.sender_type == "assistant"]
    if not assistant_messages:
        return {}
    assistant_ids = [message.id for message in assistant_messages]
    status_by_message = {
        message.id: message.metadata_json.get("status") for message in assistant_messages
    }
    answers = session.scalars(select(Answer).where(Answer.message_id.in_(assistant_ids))).all()
    mapped: dict[UUID, dict[str, Any]] = {}
    for answer in answers:
        payload = dict(answer.answer_json)
        payload["id"] = str(answer.id)
        payload["status"] = status_by_message.get(answer.message_id)
        mapped[answer.message_id] = payload
    return mapped


def _truncate_preview(value: str) -> str:
    normalized = " ".join(value.strip().split())
    if len(normalized) <= PREVIEW_MAX_LENGTH:
        return normalized
    return f"{normalized[: PREVIEW_MAX_LENGTH - 1].rstrip()}…"


def _normalize_limit(limit: int) -> int:
    if limit < 1:
        raise ConversationHistoryError(
            "CONVERSATION_INPUT_INVALID",
            "limit must be at least 1.",
            status_code=400,
        )
    return min(limit, MAX_LIST_LIMIT)


def _normalize_offset(offset: int) -> int:
    if offset < 0:
        raise ConversationHistoryError(
            "CONVERSATION_INPUT_INVALID",
            "offset must be zero or greater.",
            status_code=400,
        )
    return offset


def _normalize_search(query: str | None) -> str | None:
    if query is None:
        return None
    normalized = query.strip()
    if not normalized:
        return None
    if len(normalized) > MAX_SEARCH_LENGTH:
        raise ConversationHistoryError(
            "CONVERSATION_INPUT_INVALID",
            f"query must be at most {MAX_SEARCH_LENGTH} characters.",
            status_code=400,
        )
    return normalized