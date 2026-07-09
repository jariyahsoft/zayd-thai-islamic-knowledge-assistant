"""User feedback submission for reported answers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from sqlalchemy import select

from zayd_common.database.models import Answer, AuditLog, Conversation, Feedback, Message
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

FEEDBACK_RATE_LIMIT_MAX = 10
FEEDBACK_RATE_LIMIT_WINDOW = timedelta(hours=1)
MAX_NOTES_LENGTH = 2000

FeedbackCategory = Literal[
    "incorrect_answer",
    "citation_error",
    "incomplete_answer",
    "inappropriate_content",
    "other",
]

ALLOWED_CATEGORIES = frozenset(
    {
        "incorrect_answer",
        "citation_error",
        "incomplete_answer",
        "inappropriate_content",
        "other",
    }
)

FeedbackErrorCode = Literal[
    "FEEDBACK_NOT_FOUND",
    "FEEDBACK_FORBIDDEN",
    "FEEDBACK_INPUT_INVALID",
    "FEEDBACK_RATE_LIMITED",
]

_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class FeedbackError(Exception):
    def __init__(
        self,
        code: FeedbackErrorCode,
        message: str,
        *,
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class FeedbackSubmit:
    answer_id: UUID
    category: str
    notes: str | None = None
    citation_id: UUID | None = None


@dataclass(frozen=True)
class FeedbackPublic:
    id: UUID
    category: str
    status: str
    answer_id: UUID | None
    citation_id: UUID | None
    created_at: datetime
    receipt_message: str


class FeedbackService:
    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self.uow = uow
        self._rate_limit_buckets: dict[str, list[float]] = {}

    def submit_feedback(
        self,
        *,
        user_id: UUID,
        submission: FeedbackSubmit,
        trace_id: str | None = None,
    ) -> FeedbackPublic:
        category = _normalize_category(submission.category)
        notes = _normalize_notes(submission.notes)
        self._check_rate_limit(user_id)

        with self.uow:
            session = self._session()
            answer = _get_owned_answer(session, user_id=user_id, answer_id=submission.answer_id)
            citation_id = _validate_citation_id(submission.citation_id)
            feedback = Feedback(
                user_id=user_id,
                answer_id=answer.id,
                citation_id=citation_id,
                category=category,
                body=notes,
                status="open",
            )
            session.add(feedback)
            session.flush()
            self._audit_submit(
                actor_user_id=user_id,
                feedback=feedback,
                answer=answer,
                trace_id=trace_id,
            )
            public = _public_feedback(feedback)
            self.uow.commit()
            return public

    def get_feedback(self, *, user_id: UUID, feedback_id: UUID) -> FeedbackPublic:
        with self.uow:
            session = self._session()
            feedback = session.get(Feedback, feedback_id)
            if (
                feedback is None
                or feedback.deleted_at is not None
                or feedback.user_id != user_id
            ):
                raise FeedbackError(
                    "FEEDBACK_NOT_FOUND",
                    "Feedback was not found.",
                    status_code=404,
                )
            public = _public_feedback(feedback)
            self.uow.commit()
            return public

    def _check_rate_limit(self, user_id: UUID) -> None:
        now = datetime.now(UTC).timestamp()
        key = str(user_id)
        window_seconds = FEEDBACK_RATE_LIMIT_WINDOW.total_seconds()
        bucket = [
            value
            for value in self._rate_limit_buckets.get(key, [])
            if now - value < window_seconds
        ]
        if len(bucket) >= FEEDBACK_RATE_LIMIT_MAX:
            raise FeedbackError(
                "FEEDBACK_RATE_LIMITED",
                "Too many feedback submissions. Please try again later.",
                status_code=429,
            )
        bucket.append(now)
        self._rate_limit_buckets[key] = bucket

    def _session(self):
        if self.uow.session is None:
            raise RuntimeError("Database session not initialised in UoW.")
        return self.uow.session

    def _audit_submit(
        self,
        *,
        actor_user_id: UUID,
        feedback: Feedback,
        answer: Answer,
        trace_id: str | None,
    ) -> None:
        if self.uow.session is None:
            return
        self.uow.session.add(
            AuditLog(
                actor_user_id=actor_user_id,
                action="feedback.submit",
                resource_type="feedback",
                resource_id=feedback.id,
                outcome="success",
                request_id=trace_id,
                trace_id=trace_id,
                before_summary={},
                after_summary={
                    "feedback_id": str(feedback.id),
                    "category": feedback.category,
                    "answer_id": str(answer.id),
                    "retrieval_run_id": str(answer.retrieval_run_id),
                    "model_configuration_id": str(answer.model_configuration_id),
                    "prompt_version_id": str(answer.prompt_version_id),
                    "policy_version_id": str(answer.policy_version_id),
                    "notes_length": len(feedback.body),
                },
            )
        )


def _public_feedback(feedback: Feedback) -> FeedbackPublic:
    return FeedbackPublic(
        id=feedback.id,
        category=feedback.category,
        status=feedback.status,
        answer_id=feedback.answer_id,
        citation_id=feedback.citation_id,
        created_at=feedback.created_at,
        receipt_message="ได้รับรายงานของคุณแล้ว ทีมตรวจสอบจะดำเนินการต่อไป",
    )


def _get_owned_answer(session, *, user_id: UUID, answer_id: UUID) -> Answer:
    answer = session.scalar(
        select(Answer)
        .join(Message, Message.id == Answer.message_id)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(
            Answer.id == answer_id,
            Conversation.user_id == user_id,
            Conversation.deleted_at.is_(None),
        )
    )
    if answer is None:
        raise FeedbackError(
            "FEEDBACK_FORBIDDEN",
            "Answer was not found for this user.",
            status_code=404,
        )
    return answer


def _normalize_category(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in ALLOWED_CATEGORIES:
        raise FeedbackError(
            "FEEDBACK_INPUT_INVALID",
            "category is not supported.",
            status_code=400,
        )
    return normalized


def _normalize_notes(value: str | None) -> str:
    if value is None:
        return ""
    normalized = value.strip()
    if len(normalized) > MAX_NOTES_LENGTH:
        raise FeedbackError(
            "FEEDBACK_INPUT_INVALID",
            f"notes must be at most {MAX_NOTES_LENGTH} characters.",
            status_code=400,
        )
    return normalized


def _validate_citation_id(value: UUID | None) -> UUID | None:
    if value is None:
        return None
    return value