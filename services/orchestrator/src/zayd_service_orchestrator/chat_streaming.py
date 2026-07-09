"""Streaming chat orchestration and SSE event schema."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session
from zayd_common.conversations import NO_HISTORY_BODY, truncate_conversation_title
from zayd_common.database.models import Answer, Conversation, Message, RetrievalRun
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.prompt_registry import PromptRegistryService

from .answer_orchestration import (
    AnswerOrchestrationRequest,
    AnswerOrchestrationResult,
    AnswerOrchestrationStatus,
    AnswerOrchestrator,
    StructuredAnswer,
)

STREAMING_CHAT_VERSION = "streaming-chat-v1"
STREAMING_SCHEMA_VERSION = "chat-stream-v1"
VERIFIED_CITATION_STATUS = "verified"
CHAT_RATE_LIMIT_WINDOW_SECONDS = 60
CHAT_RATE_LIMIT_MAX_STREAMS = 20


class ChatEventType(StrEnum):
    STATUS = "status"
    FINAL_ANSWER = "final_answer"
    ERROR = "error"
    COMPLETE = "complete"


class ChatStatusStage(StrEnum):
    ACCEPTED = "accepted"
    CLASSIFYING = "classifying"
    RETRIEVING = "retrieving"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ChatStreamingError(Exception):
    """Stable chat streaming error."""

    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class ChatRequest:
    """Input request for streaming chat."""

    question: str
    actor_user_id: UUID | None = None
    guest_session_id: UUID | None = None
    conversation_id: UUID | None = None
    requested_madhhab: str | None = None
    answer_length: str = "normal"
    no_history: bool = False
    trace_id: str | None = None
    idempotency_key: str | None = None


@dataclass(frozen=True)
class ChatEvent:
    """Typed SSE event."""

    event: ChatEventType
    data: dict[str, Any]
    event_id: str


@dataclass(frozen=True)
class ChatSessionResult:
    """Result persisted for one accepted chat message."""

    conversation_id: UUID
    message_id: UUID
    answer_id: UUID | None
    trace_id: str
    request_id: str
    status: str
    prompt_version_id: UUID | None
    policy_version_id: UUID | None
    model_configuration_id: UUID | None


@dataclass
class ChatStreamHandle:
    """Cancelable stream handle returned to the API layer."""

    stream_id: str
    events: AsyncIterator[ChatEvent]
    cancel: Callable[[], None]
    task: asyncio.Task[None]


@dataclass(frozen=True)
class ChatStreamSnapshot:
    """Snapshot returned for reconnect support."""

    stream_id: str
    events: tuple[ChatEvent, ...]
    completed: bool


class ChatStreamingService:
    """Coordinates orchestration, persistence, and SSE-friendly event flow."""

    def __init__(
        self,
        *,
        uow_factory: Callable[[], SQLAlchemyUnitOfWork],
        orchestrator: AnswerOrchestrator,
        prompt_registry_factory: Callable[[], PromptRegistryService] | None = None,
    ) -> None:
        self.uow_factory = uow_factory
        self.orchestrator = orchestrator
        self.prompt_registry_factory = prompt_registry_factory
        self._event_history: dict[str, list[ChatEvent]] = {}
        self._completed_streams: set[str] = set()
        self._active_handles: dict[str, ChatStreamHandle] = {}
        self._rate_limit_buckets: dict[str, list[float]] = {}

    def start_stream(self, request: ChatRequest) -> ChatStreamHandle:
        self._validate_request(request)
        self._check_rate_limit(request)
        stream_id = f"stream-{uuid4()}"
        queue: asyncio.Queue[ChatEvent | None] = asyncio.Queue()
        cancel_event = asyncio.Event()
        self._event_history[stream_id] = []
        task = asyncio.create_task(self._run_stream(stream_id, request, queue, cancel_event))

        async def iterator() -> AsyncIterator[ChatEvent]:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item

        handle = ChatStreamHandle(
            stream_id=stream_id,
            events=iterator(),
            cancel=cancel_event.set,
            task=task,
        )
        self._active_handles[stream_id] = handle
        return handle

    def cancel_stream(self, *, stream_id: str) -> bool:
        handle = self._active_handles.get(stream_id)
        if handle is None:
            return False
        handle.cancel()
        return True

    async def _run_stream(
        self,
        stream_id: str,
        request: ChatRequest,
        queue: asyncio.Queue[ChatEvent | None],
        cancel_event: asyncio.Event,
    ) -> None:
        trace_id = request.trace_id or stream_id
        request_id = f"chat-{uuid4()}"
        try:
            await self._emit(
                queue,
                stream_id,
                self._event(
                    ChatEventType.STATUS,
                    trace_id,
                    {"stage": ChatStatusStage.ACCEPTED.value, "stream_id": stream_id},
                )
            )
            if cancel_event.is_set():
                raise asyncio.CancelledError
            await self._emit(
                queue,
                stream_id,
                self._event(
                    ChatEventType.STATUS,
                    trace_id,
                    {"stage": ChatStatusStage.CLASSIFYING.value},
                )
            )
            orchestration_task = asyncio.create_task(
                self.orchestrator.answer(
                    AnswerOrchestrationRequest(
                        question=request.question,
                        actor=str(request.actor_user_id or request.guest_session_id or "guest"),
                        idempotency_key=request.idempotency_key,
                        trace_id=trace_id,
                        requested_madhhab=request.requested_madhhab,
                    )
                )
            )
            while not orchestration_task.done():
                if cancel_event.is_set():
                    orchestration_task.cancel()
                    raise asyncio.CancelledError
                await self._emit(
                    queue,
                    stream_id,
                    self._event(
                        ChatEventType.STATUS,
                        trace_id,
                        {"stage": ChatStatusStage.RETRIEVING.value},
                    )
                )
                await asyncio.sleep(0)
                break
            result = await orchestration_task
            if cancel_event.is_set():
                raise asyncio.CancelledError
            await self._emit(
                queue,
                stream_id,
                self._event(
                    ChatEventType.STATUS,
                    trace_id,
                    {"stage": ChatStatusStage.VERIFYING.value},
                )
            )
            persisted = self._persist_result(
                request=request,
                trace_id=trace_id,
                request_id=request_id,
                result=result,
            )
            if (
                result.status == AnswerOrchestrationStatus.COMPLETED
                and result.answer is not None
            ):
                await self._emit(
                    queue,
                    stream_id,
                    self._event(
                        ChatEventType.FINAL_ANSWER,
                        trace_id,
                        _final_answer_payload(result.answer, persisted),
                    ),
                )
            await self._emit(
                queue,
                stream_id,
                self._event(
                    ChatEventType.STATUS,
                    trace_id,
                    {"stage": ChatStatusStage.COMPLETED.value, "status": result.status.value},
                )
            )
            await self._emit(
                queue,
                stream_id,
                self._event(
                    ChatEventType.COMPLETE,
                    trace_id,
                    {"status": result.status.value, "stream_id": stream_id},
                )
            )
        except asyncio.CancelledError:
            await self._emit(
                queue,
                stream_id,
                self._event(
                    ChatEventType.STATUS,
                    trace_id,
                    {"stage": ChatStatusStage.CANCELLED.value},
                )
            )
            await self._emit(
                queue,
                stream_id,
                self._event(
                    ChatEventType.COMPLETE,
                    trace_id,
                    {"status": AnswerOrchestrationStatus.CANCELLED.value, "stream_id": stream_id},
                )
            )
        except ChatStreamingError as error:
            await self._emit(
                queue,
                stream_id,
                self._event(
                    ChatEventType.ERROR,
                    trace_id,
                    {"code": error.code, "message": error.message},
                )
            )
        finally:
            self._completed_streams.add(stream_id)
            self._active_handles.pop(stream_id, None)
            await queue.put(None)

    def _persist_result(
        self,
        *,
        request: ChatRequest,
        trace_id: str,
        request_id: str,
        result: AnswerOrchestrationResult,
    ) -> ChatSessionResult:
        conversation_id = request.conversation_id or uuid4()
        message_id = uuid4()
        answer_id: UUID | None = None
        with self.uow_factory() as uow:
            session = uow.session
            if session is None:
                raise RuntimeError("Database session not initialized in UoW.")
            conversation = session.get(Conversation, conversation_id)
            if conversation is None:
                conversation = Conversation(
                    id=conversation_id,
                    user_id=request.actor_user_id,
                    guest_session_id=str(request.guest_session_id) if request.guest_session_id else None,
                    title=(
                        None
                        if request.no_history
                        else truncate_conversation_title(request.question)
                    ),
                    language="th",
                    madhhab=request.requested_madhhab or "shafii",
                )
                session.add(conversation)
            else:
                if conversation.deleted_at is not None:
                    raise ChatStreamingError(
                        "CONVERSATION_NOT_FOUND",
                        "Conversation was not found.",
                        status_code=404,
                    )
                if request.actor_user_id is not None and conversation.user_id != request.actor_user_id:
                    raise ChatStreamingError(
                        "CONVERSATION_FORBIDDEN",
                        "Conversation belongs to another user.",
                        status_code=403,
                    )
                if conversation.title is None and not request.no_history:
                    conversation.title = truncate_conversation_title(request.question)
            session.add(
                Message(
                    id=message_id,
                    conversation_id=conversation_id,
                    sender_type="user",
                    body=request.question if not request.no_history else NO_HISTORY_BODY,
                    body_hash=_hash_body(request.question),
                    metadata_json={
                        "answer_length": request.answer_length,
                        "no_history": request.no_history,
                    },
                )
            )
            retrieval_run_id = self._ensure_retrieval_run(session, request_id=request_id, trace_id=trace_id, result=result)
            if result.answer is not None and self.orchestrator.prompt_version_id and self.orchestrator.policy_version_id and self.orchestrator.model_configuration_id:
                answer_id = uuid4()
                prompt_version_value = None
                if self.prompt_registry_factory and self.orchestrator.prompt_version_id:
                    prompt_service = self.prompt_registry_factory()
                    prompt_version_value = prompt_service.get_prompt(
                        prompt_id=self.orchestrator.prompt_version_id
                    ).version
                session.add(
                    Answer(
                        id=answer_id,
                        message_id=message_id,
                        retrieval_run_id=retrieval_run_id,
                        model_configuration_id=self.orchestrator.model_configuration_id,
                        prompt_version_id=self.orchestrator.prompt_version_id,
                        policy_version_id=self.orchestrator.policy_version_id,
                        risk_level=result.answer.risk_level,
                        madhhab=result.answer.madhhab,
                        answer_json=_answer_json(result.answer, no_history=request.no_history),
                        confidence_level=result.answer.confidence.value,
                        evidence_sufficient=result.answer.evidence_sufficient,
                    )
                )
                session.add(
                    Message(
                        id=uuid4(),
                        conversation_id=conversation_id,
                        sender_type="assistant",
                        body=result.answer.answer_th if not request.no_history else NO_HISTORY_BODY,
                        body_hash=_hash_body(result.answer.answer_th),
                        metadata_json={
                            "answer_id": str(answer_id),
                            "status": result.status.value,
                            "trace_id": trace_id,
                            "prompt_version": prompt_version_value,
                        },
                    )
                )
            uow.commit()
        return ChatSessionResult(
            conversation_id=conversation_id,
            message_id=message_id,
            answer_id=answer_id,
            trace_id=trace_id,
            request_id=request_id,
            status=result.status.value,
            prompt_version_id=self.orchestrator.prompt_version_id,
            policy_version_id=self.orchestrator.policy_version_id,
            model_configuration_id=self.orchestrator.model_configuration_id,
        )

    def _ensure_retrieval_run(
        self,
        session: Session,
        *,
        request_id: str,
        trace_id: str,
        result: AnswerOrchestrationResult,
    ) -> UUID:
        if result.request_id:
            existing = session.execute(
                select(RetrievalRun).where(RetrievalRun.request_id == result.request_id)
            ).scalar_one_or_none()
            if existing is not None:
                return UUID(str(existing.id))
        run_id = uuid4()
        session.add(
            RetrievalRun(
                id=run_id,
                request_id=result.request_id or request_id,
                trace_id=trace_id,
                query_original="[redacted]",
                query_normalized="[redacted]",
                query_expansions={},
                filters={},
                retriever_version=result.trace.get("orchestrator_version", STREAMING_CHAT_VERSION),
                evidence_sufficient=bool(
                    result.answer.evidence_sufficient if result.answer is not None else False
                ),
            )
        )
        return run_id

    def _rate_limit_key(self, request: ChatRequest) -> str:
        if request.actor_user_id is not None:
            return f"user:{request.actor_user_id}"
        if request.guest_session_id is not None:
            return f"guest:{request.guest_session_id}"
        return "anonymous"

    def _check_rate_limit(self, request: ChatRequest) -> None:
        import time

        key = self._rate_limit_key(request)
        now = time.monotonic()
        bucket = [value for value in self._rate_limit_buckets.get(key, []) if now - value < CHAT_RATE_LIMIT_WINDOW_SECONDS]
        if len(bucket) >= CHAT_RATE_LIMIT_MAX_STREAMS:
            raise ChatStreamingError(
                "CHAT_RATE_LIMITED",
                "Too many chat stream requests. Retry later.",
                status_code=429,
            )
        bucket.append(now)
        self._rate_limit_buckets[key] = bucket

    def _validate_request(self, request: ChatRequest) -> None:
        if not request.question.strip():
            raise ChatStreamingError("CHAT_INPUT_INVALID", "question is required.", status_code=400)
        if request.actor_user_id is None and request.guest_session_id is None:
            raise ChatStreamingError(
                "CHAT_AUTH_REQUIRED",
                "A user or guest session identity is required.",
                status_code=401,
            )

    def _event(self, event: ChatEventType, trace_id: str, data: dict[str, Any]) -> ChatEvent:
        return ChatEvent(
            event=event,
            event_id=str(uuid4()),
            data={
                "schema_version": STREAMING_SCHEMA_VERSION,
                "trace_id": trace_id,
                "timestamp": datetime.now(UTC).isoformat(),
                **data,
            },
        )

    async def _emit(
        self,
        queue: asyncio.Queue[ChatEvent | None],
        stream_id: str,
        event: ChatEvent,
    ) -> None:
        self._event_history.setdefault(stream_id, []).append(event)
        await queue.put(event)

    def get_snapshot(self, *, stream_id: str, last_event_id: str | None = None) -> ChatStreamSnapshot:
        events = list(self._event_history.get(stream_id, []))
        if last_event_id:
            for index, event in enumerate(events):
                if event.event_id == last_event_id:
                    events = events[index + 1 :]
                    break
        return ChatStreamSnapshot(
            stream_id=stream_id,
            events=tuple(events),
            completed=stream_id in self._completed_streams,
        )


def sse_encode(event: ChatEvent) -> str:
    """Render one SSE frame."""
    import json

    payload = json.dumps(event.data, ensure_ascii=False)
    return f"id: {event.event_id}\nevent: {event.event.value}\ndata: {payload}\n\n"


def _answer_json(answer: StructuredAnswer, *, no_history: bool) -> dict[str, Any]:
    return {
        "summary": answer.summary if not no_history else NO_HISTORY_BODY,
        "answer_th": answer.answer_th if not no_history else NO_HISTORY_BODY,
        "madhhab": answer.madhhab,
        "risk_level": answer.risk_level,
        "confidence": answer.confidence.value,
        "evidence_sufficient": answer.evidence_sufficient,
        "citations": _verified_citations(answer),
        "limitations": list(answer.limitations),
        "warning": answer.warning,
        "trace_id": answer.trace_id,
    }


def _final_answer_payload(answer: StructuredAnswer, persisted: ChatSessionResult) -> dict[str, Any]:
    return {
        "conversation_id": str(persisted.conversation_id),
        "message_id": str(persisted.message_id),
        "answer_id": str(persisted.answer_id) if persisted.answer_id else None,
        "status": persisted.status,
        "answer": _answer_json(answer, no_history=False),
        "prompt_version_id": str(persisted.prompt_version_id) if persisted.prompt_version_id else None,
        "policy_version_id": str(persisted.policy_version_id) if persisted.policy_version_id else None,
    }


def _verified_citations(answer: StructuredAnswer) -> list[dict[str, str]]:
    return [
        {
            "citation_id": item.citation_id,
            "display": item.display,
            "source_type": item.source_type,
            "verification_status": item.verification_status,
        }
        for item in answer.citations
        if item.verification_status == VERIFIED_CITATION_STATUS
    ]


def _hash_body(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()
