"""Bounded, auditable answer invalidation and affected-answer discovery."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zayd_common.database.models import (
    Answer,
    AnswerInvalidation,
    AuditLog,
    Citation,
    Document,
    DocumentVersion,
    Incident,
    RetrievalResult,
    Source,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.rbac import Permission

ANSWER_INVALIDATION_POLICY_VERSION = "answer-invalidation-v1"
DEFAULT_WARNING = "This answer has been invalidated and should not be relied upon."
MAX_REASON_LENGTH = 2000
MAX_DISCOVERY_BATCH = 200


class AnswerInvalidationError(Exception):
    def __init__(self, code: str, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.code, self.message, self.status_code = code, message, status_code


@dataclass(frozen=True)
class AnswerInvalidationNotice:
    answer_id: UUID
    invalidated_at: datetime
    warning: str


class AnswerInvalidationNotifier(Protocol):
    def send(self, notice: AnswerInvalidationNotice) -> str: ...


class DisabledAnswerInvalidationNotifier:
    def send(self, notice: AnswerInvalidationNotice) -> str:
        return "not_configured"


@dataclass(frozen=True)
class AnswerInvalidationResult:
    answer_id: UUID
    invalidated_at: datetime
    warning: str
    notification_status: str
    idempotent: bool


@dataclass(frozen=True)
class AffectedAnswerPage:
    answer_ids: tuple[UUID, ...]
    total_count: int
    limit: int
    offset: int
    next_offset: int | None


class AnswerInvalidationService:
    def __init__(
        self, uow: SQLAlchemyUnitOfWork, notifier: AnswerInvalidationNotifier | None = None
    ) -> None:
        self.uow = uow
        self.notifier = notifier or DisabledAnswerInvalidationNotifier()

    def invalidate(
        self,
        *,
        answer_id: UUID,
        reason: str,
        idempotency_key: str,
        actor_user_id: UUID,
        permissions: frozenset[str],
        incident_id: UUID | None = None,
        citation_id: UUID | None = None,
        source_id: UUID | None = None,
        trace_id: str | None = None,
    ) -> AnswerInvalidationResult:
        _require_invalidate(permissions)
        normalized_reason = _require_text(reason, "reason", MAX_REASON_LENGTH)
        key = _require_text(idempotency_key, "idempotency_key", 200)
        with self.uow:
            session = self._session()
            existing = session.scalar(
                select(AnswerInvalidation).where(AnswerInvalidation.idempotency_key == key)
            )
            if existing is not None:
                answer = _get_answer(session, existing.answer_id)
                result = _result(existing, answer, True)
                self.uow.commit()
                return result
            answer = _get_answer(session, answer_id)
            if incident_id is not None and session.get(Incident, incident_id) is None:
                raise AnswerInvalidationError(
                    "ANSWER_INVALIDATION_LINK_NOT_FOUND", "Incident was not found.", status_code=404
                )
            if citation_id is not None and session.get(Citation, citation_id) is None:
                raise AnswerInvalidationError(
                    "ANSWER_INVALIDATION_LINK_NOT_FOUND", "Citation was not found.", status_code=404
                )
            if source_id is not None and session.get(Source, source_id) is None:
                raise AnswerInvalidationError(
                    "ANSWER_INVALIDATION_LINK_NOT_FOUND", "Source was not found.", status_code=404
                )
            changed_at = answer.invalidated_at or datetime.now(UTC)
            warning = DEFAULT_WARNING
            answer.invalidated_at = changed_at
            payload = dict(answer.answer_json or {})
            warnings = list(payload.get("warnings", []))
            warning_record = {
                "type": "answer_invalidated",
                "reason": normalized_reason,
                "invalidated_at": changed_at.isoformat(),
                "policy_version": ANSWER_INVALIDATION_POLICY_VERSION,
            }
            if warning_record not in warnings:
                warnings.append(warning_record)
            payload["warnings"] = warnings
            payload["invalidation_warning"] = warning
            answer.answer_json = payload
            answer.updated_at = changed_at
            notification_status = self.notifier.send(
                AnswerInvalidationNotice(answer.id, changed_at, warning)
            )
            record = AnswerInvalidation(
                answer_id=answer.id,
                incident_id=incident_id,
                citation_id=citation_id,
                source_id=source_id,
                reason=normalized_reason,
                warning=warning,
                actor_user_id=actor_user_id,
                idempotency_key=key,
                notification_status=notification_status,
                policy_version=ANSWER_INVALIDATION_POLICY_VERSION,
            )
            session.add(record)
            session.flush()
            _audit(
                session,
                actor_user_id,
                "answer.invalidate",
                answer.id,
                trace_id,
                {
                    "invalidation_id": str(record.id),
                    "incident_id": str(incident_id) if incident_id else None,
                    "notification_status": notification_status,
                },
            )
            result = AnswerInvalidationResult(
                answer.id, changed_at, warning, notification_status, False
            )
            self.uow.commit()
            return result

    def discover(
        self,
        *,
        permissions: frozenset[str],
        citation_id: UUID | None = None,
        source_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
        actor_user_id: UUID | None = None,
        trace_id: str | None = None,
    ) -> AffectedAnswerPage:
        _require_review(permissions)
        if (citation_id is None) == (source_id is None):
            raise AnswerInvalidationError(
                "ANSWER_INVALIDATION_INPUT_INVALID", "Provide exactly one citation_id or source_id."
            )
        bounded_limit = min(max(limit, 1), MAX_DISCOVERY_BATCH)
        bounded_offset = max(offset, 0)
        run_ids = select(RetrievalResult.retrieval_run_id)
        if citation_id is not None:
            run_ids = run_ids.where(RetrievalResult.citation_id == citation_id)
        else:
            run_ids = (
                run_ids.join(
                    DocumentVersion, DocumentVersion.id == RetrievalResult.document_version_id
                )
                .join(Document, Document.id == DocumentVersion.document_id)
                .where(Document.source_id == source_id)
            )
        stmt = (
            select(Answer)
            .where(Answer.retrieval_run_id.in_(run_ids))
            .order_by(Answer.created_at, Answer.id)
        )
        with self.uow:
            session = self._session()
            total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
            rows = session.scalars(stmt.limit(bounded_limit).offset(bounded_offset)).all()
            next_offset = bounded_offset + len(rows) if bounded_offset + len(rows) < total else None
            if actor_user_id is not None:
                _audit(
                    session,
                    actor_user_id,
                    "answer.invalidation.discover",
                    None,
                    trace_id,
                    {
                        "citation_id": str(citation_id) if citation_id else None,
                        "source_id": str(source_id) if source_id else None,
                        "result_count": len(rows),
                        "offset": bounded_offset,
                        "limit": bounded_limit,
                    },
                )
            result = AffectedAnswerPage(
                tuple(row.id for row in rows), total, bounded_limit, bounded_offset, next_offset
            )
            self.uow.commit()
            return result

    def _session(self) -> Session:
        if self.uow.session is None:
            raise RuntimeError("Database session not initialised in UoW.")
        return self.uow.session


def _require_invalidate(permissions: frozenset[str]) -> None:
    if Permission.ANSWERS_INVALIDATE.value not in permissions:
        raise AnswerInvalidationError(
            "ANSWER_INVALIDATION_FORBIDDEN", "Forbidden.", status_code=403
        )


def _require_review(permissions: frozenset[str]) -> None:
    if Permission.ANSWERS_REVIEW.value not in permissions:
        raise AnswerInvalidationError(
            "ANSWER_INVALIDATION_FORBIDDEN", "Forbidden.", status_code=403
        )


def _require_text(value: str, field: str, maximum: int) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise AnswerInvalidationError(
            "ANSWER_INVALIDATION_INPUT_INVALID", f"{field} must contain 1-{maximum} characters."
        )
    return normalized


def _get_answer(session: Session, answer_id: UUID) -> Answer:
    answer = session.get(Answer, answer_id)
    if answer is None:
        raise AnswerInvalidationError("ANSWER_NOT_FOUND", "Answer was not found.", status_code=404)
    return answer


def _result(
    record: AnswerInvalidation, answer: Answer, idempotent: bool
) -> AnswerInvalidationResult:
    return AnswerInvalidationResult(
        answer.id,
        answer.invalidated_at or record.created_at,
        record.warning,
        record.notification_status,
        idempotent,
    )


def _audit(
    session: Session,
    actor: UUID,
    action: str,
    resource_id: UUID | None,
    trace_id: str | None,
    after: dict[str, object],
) -> None:
    session.add(
        AuditLog(
            id=uuid4(),
            actor_user_id=actor,
            action=action,
            resource_type="answer",
            resource_id=resource_id,
            outcome="success",
            request_id=trace_id,
            trace_id=trace_id,
            before_summary={},
            after_summary={**after, "policy_version": ANSWER_INVALIDATION_POLICY_VERSION},
            source_context={},
        )
    )
