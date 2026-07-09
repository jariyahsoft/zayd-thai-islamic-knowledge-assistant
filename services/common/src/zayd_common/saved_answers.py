"""User-owned saved answer bookmarks."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import func, select

from zayd_common.database.models import (
    Answer,
    AuditLog,
    Citation,
    Conversation,
    Document,
    DocumentVersion,
    Message,
    SavedAnswer,
    Source,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

MAX_LIST_LIMIT = 100
PREVIEW_MAX_LENGTH = 200

SavedAnswerErrorCode = Literal[
    "SAVED_ANSWER_NOT_FOUND",
    "SAVED_ANSWER_FORBIDDEN",
    "SAVED_ANSWER_INPUT_INVALID",
]

_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_TOKEN_PATTERN = re.compile(
    r"^CIT-[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class SavedAnswerError(Exception):
    def __init__(
        self,
        code: SavedAnswerErrorCode,
        message: str,
        *,
        status_code: int = 404,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class SavedAnswerPublic:
    id: UUID
    answer_id: UUID
    saved_at: datetime
    summary: str
    answer_th: str
    madhhab: str
    warnings: tuple[str, ...]
    citations: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class SavedAnswerListResult:
    saved_answers: tuple[SavedAnswerPublic, ...]
    total_count: int


class SavedAnswerService:
    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self.uow = uow

    def list_saved_answers(
        self,
        *,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> SavedAnswerListResult:
        normalized_limit = _normalize_limit(limit)
        normalized_offset = _normalize_offset(offset)
        with self.uow:
            session = self._session()
            base = select(SavedAnswer).where(
                SavedAnswer.user_id == user_id,
                SavedAnswer.deleted_at.is_(None),
            )
            total_count = session.scalar(select(func.count()).select_from(base.subquery())) or 0
            rows = session.scalars(
                base.order_by(SavedAnswer.updated_at.desc())
                .limit(normalized_limit)
                .offset(normalized_offset)
            ).all()
            public_rows = tuple(_public_from_saved(session, row) for row in rows)
            self.uow.commit()
            return SavedAnswerListResult(
                saved_answers=public_rows,
                total_count=total_count,
            )

    def save_answer(
        self,
        *,
        user_id: UUID,
        answer_id: UUID,
        trace_id: str | None = None,
    ) -> SavedAnswerPublic:
        with self.uow:
            session = self._session()
            answer = _get_owned_answer(session, user_id=user_id, answer_id=answer_id)
            existing = session.scalar(
                select(SavedAnswer).where(
                    SavedAnswer.user_id == user_id,
                    SavedAnswer.answer_id == answer.id,
                    SavedAnswer.deleted_at.is_(None),
                )
            )
            if existing is not None:
                public = _public_from_saved(session, existing)
                self.uow.commit()
                return public

            restored = session.scalar(
                select(SavedAnswer).where(
                    SavedAnswer.user_id == user_id,
                    SavedAnswer.answer_id == answer.id,
                    SavedAnswer.deleted_at.is_not(None),
                )
            )
            if restored is not None:
                restored.deleted_at = None
                saved = restored
            else:
                saved = SavedAnswer(user_id=user_id, answer_id=answer.id)
                session.add(saved)
            session.flush()
            self._audit(
                actor_user_id=user_id,
                action="saved_answers.save",
                resource_id=saved.id,
                trace_id=trace_id,
                before_summary={"answer_id": str(answer.id)},
                after_summary={"saved_answer_id": str(saved.id)},
            )
            public = _public_from_saved(session, saved)
            self.uow.commit()
            return public

    def unsave_answer(
        self,
        *,
        user_id: UUID,
        saved_answer_id: UUID,
        trace_id: str | None = None,
    ) -> None:
        with self.uow:
            session = self._session()
            saved = session.get(SavedAnswer, saved_answer_id)
            if saved is None or saved.deleted_at is not None or saved.user_id != user_id:
                raise SavedAnswerError(
                    "SAVED_ANSWER_NOT_FOUND",
                    "Saved answer was not found.",
                    status_code=404,
                )
            saved.deleted_at = datetime.now(UTC)
            self._audit(
                actor_user_id=user_id,
                action="saved_answers.unsave",
                resource_id=saved.id,
                trace_id=trace_id,
                before_summary={"answer_id": str(saved.answer_id)},
                after_summary={"deleted_at": saved.deleted_at.isoformat()},
            )
            self.uow.commit()

    def is_answer_saved(self, *, user_id: UUID, answer_id: UUID) -> bool:
        with self.uow:
            session = self._session()
            saved = session.scalar(
                select(SavedAnswer.id).where(
                    SavedAnswer.user_id == user_id,
                    SavedAnswer.answer_id == answer_id,
                    SavedAnswer.deleted_at.is_(None),
                )
            )
            self.uow.commit()
            return saved is not None

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
                resource_type="saved_answer",
                resource_id=resource_id,
                outcome="success",
                request_id=trace_id,
                trace_id=trace_id,
                before_summary=before_summary,
                after_summary=after_summary,
            )
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
        raise SavedAnswerError(
            "SAVED_ANSWER_FORBIDDEN",
            "Answer was not found for this user.",
            status_code=404,
        )
    return answer


def _public_from_saved(session, saved: SavedAnswer) -> SavedAnswerPublic:
    answer = session.get(Answer, saved.answer_id)
    if answer is None:
        raise SavedAnswerError(
            "SAVED_ANSWER_NOT_FOUND",
            "Saved answer reference is no longer available.",
            status_code=404,
        )
    answer_json = dict(answer.answer_json)
    warnings = _resolve_warnings(session, answer=answer, answer_json=answer_json)
    citations = tuple(
        {
            "citation_id": str(item.get("citation_id", "")),
            "display": str(item.get("display", "")),
            "source_type": str(item.get("source_type", "")),
            "verification_status": str(item.get("verification_status", "")),
        }
        for item in answer_json.get("citations", [])
        if isinstance(item, dict)
    )
    return SavedAnswerPublic(
        id=saved.id,
        answer_id=answer.id,
        saved_at=saved.created_at,
        summary=str(answer_json.get("summary", "")),
        answer_th=_truncate_preview(str(answer_json.get("answer_th", ""))),
        madhhab=str(answer_json.get("madhhab", answer.madhhab)),
        warnings=warnings,
        citations=citations,
    )


def _resolve_warnings(session, *, answer: Answer, answer_json: dict[str, Any]) -> tuple[str, ...]:
    warnings: list[str] = []
    if answer.invalidated_at is not None:
        warnings.append("answer_invalidated")
    invalidation_warning = answer_json.get("invalidation_warning")
    if isinstance(invalidation_warning, str) and invalidation_warning.strip():
        if "suspended" in invalidation_warning.lower():
            warnings.append("source_suspended")
        else:
            warnings.append("answer_invalidated")
    for item in answer_json.get("citations", []):
        if not isinstance(item, dict):
            continue
        citation_id = _parse_citation_ref(item.get("citation_id"))
        if citation_id is None:
            continue
        citation = session.get(Citation, citation_id)
        if citation is None:
            continue
        if citation.invalidated_at is not None or not citation.verified:
            warnings.append("citation_invalidated")
        version = session.get(DocumentVersion, citation.document_version_id)
        document = session.get(Document, version.document_id) if version is not None else None
        if document is not None:
            source = session.get(Source, document.source_id)
            if source is not None and not source.is_active:
                warnings.append("source_suspended")
    return tuple(dict.fromkeys(warnings))


def _parse_citation_ref(value: Any) -> UUID | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if _UUID_PATTERN.match(normalized):
        return UUID(normalized)
    if normalized.startswith("CIT-"):
        token = normalized.removeprefix("CIT-")
        if _UUID_PATTERN.match(token):
            return UUID(token)
    if _TOKEN_PATTERN.match(normalized):
        return UUID(normalized.removeprefix("CIT-"))
    return None


def _truncate_preview(value: str) -> str:
    normalized = " ".join(value.strip().split())
    if len(normalized) <= PREVIEW_MAX_LENGTH:
        return normalized
    return f"{normalized[: PREVIEW_MAX_LENGTH - 1].rstrip()}…"


def _normalize_limit(limit: int) -> int:
    if limit < 1:
        raise SavedAnswerError(
            "SAVED_ANSWER_INPUT_INVALID",
            "limit must be at least 1.",
            status_code=400,
        )
    return min(limit, MAX_LIST_LIMIT)


def _normalize_offset(offset: int) -> int:
    if offset < 0:
        raise SavedAnswerError(
            "SAVED_ANSWER_INPUT_INVALID",
            "offset must be zero or greater.",
            status_code=400,
        )
    return offset