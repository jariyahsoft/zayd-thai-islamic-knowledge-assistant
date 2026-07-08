"""Lifecycle controls for published documents.

Suspension, archival, and rollback are retrieval-safety operations. They hide
affected chunks immediately, flag citations and historical answers, and retain
append-only audit evidence for every transition.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, cast
from uuid import UUID, uuid4

from sqlalchemy import select

from zayd_common.database.models import (
    Answer,
    AuditLog,
    Citation,
    Document,
    DocumentChunk,
    DocumentVersion,
    RetrievalResult,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.enums import DocumentStatus
from zayd_common.state_machines import DocumentStateMachine, TransitionMetadata

DOCUMENT_LIFECYCLE_POLICY_VERSION = "document-lifecycle-v1"

LifecycleErrorCode = Literal[
    "DOCUMENT_LIFECYCLE_NOT_FOUND",
    "DOCUMENT_LIFECYCLE_VERSION_NOT_FOUND",
    "DOCUMENT_LIFECYCLE_ACCESS_DENIED",
    "DOCUMENT_LIFECYCLE_INVALID_STATUS",
    "DOCUMENT_LIFECYCLE_REASON_REQUIRED",
    "DOCUMENT_LIFECYCLE_ROLLBACK_TARGET_INVALID",
    "DOCUMENT_LIFECYCLE_CONFLICT",
]

_LIFECYCLE_ROLES = frozenset({"admin", "senior_scholar"})


class DocumentLifecycleError(Exception):
    """Raised when published document lifecycle controls fail closed."""

    def __init__(
        self,
        code: LifecycleErrorCode,
        message: str,
        *,
        status_code: int = 409,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class AffectedAnswerPublic:
    id: UUID
    invalidated_at: datetime
    warning: str


@dataclass(frozen=True)
class DocumentLifecycleResult:
    document_id: UUID
    previous_published_version_id: UUID | None
    current_published_version_id: UUID | None
    document_status: str
    affected_chunk_count: int
    affected_citation_count: int
    affected_answer_count: int
    affected_answers: tuple[AffectedAnswerPublic, ...]
    policy_version: str
    changed_at: datetime


class DocumentLifecycleService:
    """Manages published document suspension, archival, and rollback."""

    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self.uow = uow

    def suspend_document(
        self,
        *,
        document_id: UUID,
        actor_user_id: UUID,
        principal_roles: frozenset[str],
        reason: str,
        base_row_version: int | None = None,
        trace_id: str | None = None,
    ) -> DocumentLifecycleResult:
        return self._change_visibility(
            document_id=document_id,
            actor_user_id=actor_user_id,
            principal_roles=principal_roles,
            reason=reason,
            target_status=DocumentStatus.SUSPENDED,
            base_row_version=base_row_version,
            trace_id=trace_id,
        )

    def archive_document(
        self,
        *,
        document_id: UUID,
        actor_user_id: UUID,
        principal_roles: frozenset[str],
        reason: str,
        base_row_version: int | None = None,
        trace_id: str | None = None,
    ) -> DocumentLifecycleResult:
        return self._change_visibility(
            document_id=document_id,
            actor_user_id=actor_user_id,
            principal_roles=principal_roles,
            reason=reason,
            target_status=DocumentStatus.ARCHIVED,
            base_row_version=base_row_version,
            trace_id=trace_id,
        )

    def rollback_document(
        self,
        *,
        document_id: UUID,
        target_document_version_id: UUID,
        actor_user_id: UUID,
        principal_roles: frozenset[str],
        reason: str,
        base_row_version: int | None = None,
        trace_id: str | None = None,
    ) -> DocumentLifecycleResult:
        normalized_reason = _require_reason(reason)
        _assert_lifecycle_role(principal_roles)
        with self.uow:
            session = self._session()
            document = _load_document(session, document_id)
            _assert_row_version(document, base_row_version)
            previous_version_id = document.published_version_id
            current_status = _document_status(document.review_status)
            if current_status not in {DocumentStatus.PUBLISHED, DocumentStatus.SUSPENDED}:
                raise DocumentLifecycleError(
                    "DOCUMENT_LIFECYCLE_INVALID_STATUS",
                    "Only published or suspended documents can be rolled back.",
                    status_code=409,
                )
            if previous_version_id == target_document_version_id:
                raise DocumentLifecycleError(
                    "DOCUMENT_LIFECYCLE_ROLLBACK_TARGET_INVALID",
                    "Rollback target is already the published version.",
                    status_code=409,
                )
            target = session.get(DocumentVersion, target_document_version_id)
            if target is None or target.document_id != document.id:
                raise DocumentLifecycleError(
                    "DOCUMENT_LIFECYCLE_VERSION_NOT_FOUND",
                    "Rollback target version not found for this document.",
                    status_code=404,
                )
            if target.status not in {
                DocumentStatus.PUBLISHED.value,
                DocumentStatus.SCHOLAR_APPROVED.value,
            }:
                raise DocumentLifecycleError(
                    "DOCUMENT_LIFECYCLE_ROLLBACK_TARGET_INVALID",
                    "Rollback target must be a previously approved or published version.",
                    status_code=409,
                )

            now = datetime.now(UTC)
            current_chunks = _chunks_for_version(session, previous_version_id)
            target_chunks = _chunks_for_version(session, target.id)
            if not target_chunks:
                raise DocumentLifecycleError(
                    "DOCUMENT_LIFECYCLE_ROLLBACK_TARGET_INVALID",
                    "Rollback target has no retrieval chunks.",
                    status_code=409,
                )

            affected_citations = _citations_for_chunks(session, current_chunks)
            affected_answers = _answers_for_chunks(session, current_chunks)
            for chunk in current_chunks:
                _mark_chunk_hidden(chunk, now, "rollback", normalized_reason, actor_user_id)
            for chunk in target_chunks:
                _mark_chunk_restored(chunk, now, normalized_reason, actor_user_id)
            _invalidate_citations(affected_citations, now, "rollback", normalized_reason)
            public_answers = _invalidate_answers(
                affected_answers,
                now,
                "rollback",
                normalized_reason,
            )

            target.status = DocumentStatus.PUBLISHED.value
            if target.frozen_at is None:
                target.frozen_at = now
            if previous_version_id is not None:
                previous = session.get(DocumentVersion, previous_version_id)
                if previous is not None and previous.id != target.id:
                    previous.status = DocumentStatus.SUSPENDED.value
            document.review_status = DocumentStatus.PUBLISHED.value
            document.published_version_id = target.id
            document.updated_by = actor_user_id
            document.updated_at = now
            document.row_version += 1
            _audit(
                session,
                action="documents.rollback",
                outcome="success",
                actor_user_id=actor_user_id,
                resource_id=document.id,
                reason=normalized_reason,
                before_summary={
                    "published_version_id": str(previous_version_id)
                    if previous_version_id
                    else None,
                    "status": "published",
                },
                after_summary={
                    "published_version_id": str(target.id),
                    "status": document.review_status,
                    "affected_chunk_count": len(current_chunks),
                    "restored_chunk_count": len(target_chunks),
                    "affected_citation_count": len(affected_citations),
                    "affected_answer_count": len(public_answers),
                    "policy_version": DOCUMENT_LIFECYCLE_POLICY_VERSION,
                },
                trace_id=trace_id,
            )
            result = _result(
                document=document,
                previous_version_id=previous_version_id,
                changed_at=now,
                affected_chunk_count=len(current_chunks),
                affected_citation_count=len(affected_citations),
                affected_answers=public_answers,
            )
            self.uow.commit()
            return result

    def _change_visibility(
        self,
        *,
        document_id: UUID,
        actor_user_id: UUID,
        principal_roles: frozenset[str],
        reason: str,
        target_status: DocumentStatus,
        base_row_version: int | None,
        trace_id: str | None,
    ) -> DocumentLifecycleResult:
        normalized_reason = _require_reason(reason)
        _assert_lifecycle_role(principal_roles)
        with self.uow:
            session = self._session()
            document = _load_document(session, document_id)
            _assert_row_version(document, base_row_version)
            previous_version_id = document.published_version_id
            current_status = _document_status(document.review_status)
            if target_status == DocumentStatus.SUSPENDED:
                if current_status != DocumentStatus.PUBLISHED or previous_version_id is None:
                    raise DocumentLifecycleError(
                        "DOCUMENT_LIFECYCLE_INVALID_STATUS",
                        "Only published documents can be suspended.",
                        status_code=409,
                    )
            elif current_status not in {DocumentStatus.PUBLISHED, DocumentStatus.SUSPENDED}:
                raise DocumentLifecycleError(
                    "DOCUMENT_LIFECYCLE_INVALID_STATUS",
                    "Only published or suspended documents can be archived.",
                    status_code=409,
                )
            DocumentStateMachine.validate_transition(
                current_status,
                target_status,
                TransitionMetadata(actor_id=str(actor_user_id), reason=normalized_reason),
            )

            now = datetime.now(UTC)
            chunks = _chunks_for_version(session, previous_version_id)
            citations = _citations_for_chunks(session, chunks)
            answers = _answers_for_chunks(session, chunks)
            action_name = "suspend" if target_status == DocumentStatus.SUSPENDED else "archive"
            for chunk in chunks:
                _mark_chunk_hidden(chunk, now, action_name, normalized_reason, actor_user_id)
            _invalidate_citations(citations, now, action_name, normalized_reason)
            public_answers = _invalidate_answers(answers, now, action_name, normalized_reason)

            if previous_version_id is not None:
                version = session.get(DocumentVersion, previous_version_id)
                if version is not None:
                    version.status = target_status.value
            document.review_status = target_status.value
            if target_status == DocumentStatus.ARCHIVED:
                document.published_version_id = None
            document.updated_by = actor_user_id
            document.updated_at = now
            document.row_version += 1
            _audit(
                session,
                action=f"documents.{action_name}",
                outcome="success",
                actor_user_id=actor_user_id,
                resource_id=document.id,
                reason=normalized_reason,
                before_summary={
                    "published_version_id": str(previous_version_id)
                    if previous_version_id
                    else None,
                    "status": current_status.value,
                },
                after_summary={
                    "published_version_id": str(document.published_version_id)
                    if document.published_version_id
                    else None,
                    "status": document.review_status,
                    "affected_chunk_count": len(chunks),
                    "affected_citation_count": len(citations),
                    "affected_answer_count": len(public_answers),
                    "policy_version": DOCUMENT_LIFECYCLE_POLICY_VERSION,
                },
                trace_id=trace_id,
            )
            result = _result(
                document=document,
                previous_version_id=previous_version_id,
                changed_at=now,
                affected_chunk_count=len(chunks),
                affected_citation_count=len(citations),
                affected_answers=public_answers,
            )
            self.uow.commit()
            return result

    def _session(self) -> Any:
        if self.uow.session is None:
            raise RuntimeError("Database session not initialised in UoW.")
        return self.uow.session


def _require_reason(reason: str) -> str:
    normalized = reason.strip()
    if not normalized:
        raise DocumentLifecycleError(
            "DOCUMENT_LIFECYCLE_REASON_REQUIRED",
            "A non-empty reason is required.",
            status_code=400,
        )
    return normalized


def _assert_lifecycle_role(principal_roles: frozenset[str]) -> None:
    if not principal_roles & _LIFECYCLE_ROLES:
        raise DocumentLifecycleError(
            "DOCUMENT_LIFECYCLE_ACCESS_DENIED",
            "Only senior scholars or admins can change published document visibility.",
            status_code=403,
        )


def _load_document(session: Any, document_id: UUID) -> Document:
    document = session.get(Document, document_id)
    if document is None:
        raise DocumentLifecycleError(
            "DOCUMENT_LIFECYCLE_NOT_FOUND",
            "Document not found.",
            status_code=404,
        )
    return cast(Document, document)


def _assert_row_version(document: Document, base_row_version: int | None) -> None:
    if base_row_version is not None and document.row_version != base_row_version:
        raise DocumentLifecycleError(
            "DOCUMENT_LIFECYCLE_CONFLICT",
            "Document row version does not match.",
            status_code=409,
        )


def _document_status(status: str) -> DocumentStatus:
    try:
        return DocumentStatus(status)
    except ValueError as exc:
        raise DocumentLifecycleError(
            "DOCUMENT_LIFECYCLE_INVALID_STATUS",
            "Document status is not supported.",
            status_code=409,
        ) from exc


def _chunks_for_version(session: Any, version_id: UUID | None) -> list[DocumentChunk]:
    if version_id is None:
        return []
    return list(
        session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_version_id == version_id)
            .order_by(DocumentChunk.chunk_index)
        ).scalars().all()
    )


def _citations_for_chunks(session: Any, chunks: list[DocumentChunk]) -> list[Citation]:
    chunk_ids = [chunk.id for chunk in chunks]
    if not chunk_ids:
        return []
    return list(
        session.execute(select(Citation).where(Citation.chunk_id.in_(chunk_ids))).scalars().all()
    )


def _answers_for_chunks(session: Any, chunks: list[DocumentChunk]) -> list[Answer]:
    chunk_ids = [chunk.id for chunk in chunks]
    if not chunk_ids:
        return []
    retrieval_run_ids = set(
        session.execute(
            select(RetrievalResult.retrieval_run_id).where(RetrievalResult.chunk_id.in_(chunk_ids))
        ).scalars().all()
    )
    if not retrieval_run_ids:
        return []
    return list(
        session.execute(
            select(Answer).where(Answer.retrieval_run_id.in_(retrieval_run_ids))
        ).scalars().all()
    )


def _mark_chunk_hidden(
    chunk: DocumentChunk,
    changed_at: datetime,
    action: str,
    reason: str,
    actor_user_id: UUID,
) -> None:
    chunk.is_published = False
    metadata = dict(chunk.metadata_json or {})
    metadata["visibility"] = {
        "status": "hidden",
        "action": action,
        "reason": reason,
        "changed_at": changed_at.isoformat(),
        "changed_by": str(actor_user_id),
        "policy_version": DOCUMENT_LIFECYCLE_POLICY_VERSION,
    }
    chunk.metadata_json = metadata
    chunk.updated_at = changed_at


def _mark_chunk_restored(
    chunk: DocumentChunk,
    changed_at: datetime,
    reason: str,
    actor_user_id: UUID,
) -> None:
    chunk.is_published = True
    metadata = dict(chunk.metadata_json or {})
    metadata["visibility"] = {
        "status": "published",
        "action": "rollback_restore",
        "reason": reason,
        "changed_at": changed_at.isoformat(),
        "changed_by": str(actor_user_id),
        "policy_version": DOCUMENT_LIFECYCLE_POLICY_VERSION,
    }
    chunk.metadata_json = metadata
    chunk.updated_at = changed_at


def _invalidate_citations(
    citations: list[Citation],
    changed_at: datetime,
    action: str,
    reason: str,
) -> None:
    for citation in citations:
        if citation.invalidated_at is None:
            citation.invalidated_at = changed_at
        citation.verified = False
        citation.updated_at = changed_at


def _invalidate_answers(
    answers: list[Answer],
    changed_at: datetime,
    action: str,
    reason: str,
) -> tuple[AffectedAnswerPublic, ...]:
    public: list[AffectedAnswerPublic] = []
    warning = _answer_warning(action)
    for answer in answers:
        if answer.invalidated_at is None:
            answer.invalidated_at = changed_at
        answer_json = dict(answer.answer_json or {})
        warnings = list(answer_json.get("warnings", []))
        invalidation = {
            "type": "source_content_invalidated",
            "action": action,
            "warning": warning,
            "reason": reason,
            "invalidated_at": changed_at.isoformat(),
            "policy_version": DOCUMENT_LIFECYCLE_POLICY_VERSION,
        }
        if invalidation not in warnings:
            warnings.append(invalidation)
        answer_json["warnings"] = warnings
        answer_json["invalidation_warning"] = warning
        answer.answer_json = answer_json
        answer.updated_at = changed_at
        public.append(AffectedAnswerPublic(answer.id, answer.invalidated_at, warning))
    return tuple(public)


def _answer_warning(action: str) -> str:
    if action == "rollback":
        return "This answer used a document version that has been rolled back for review."
    if action == "archive":
        return "This answer used a document that has been archived and should be reviewed."
    return "This answer used a document that has been suspended and should be reviewed."


def _result(
    *,
    document: Document,
    previous_version_id: UUID | None,
    changed_at: datetime,
    affected_chunk_count: int,
    affected_citation_count: int,
    affected_answers: tuple[AffectedAnswerPublic, ...],
) -> DocumentLifecycleResult:
    return DocumentLifecycleResult(
        document_id=document.id,
        previous_published_version_id=previous_version_id,
        current_published_version_id=document.published_version_id,
        document_status=document.review_status,
        affected_chunk_count=affected_chunk_count,
        affected_citation_count=affected_citation_count,
        affected_answer_count=len(affected_answers),
        affected_answers=affected_answers,
        policy_version=DOCUMENT_LIFECYCLE_POLICY_VERSION,
        changed_at=changed_at,
    )


def _audit(
    session: Any,
    *,
    action: str,
    outcome: str,
    actor_user_id: UUID,
    resource_id: UUID,
    reason: str,
    before_summary: dict[str, Any],
    after_summary: dict[str, Any],
    trace_id: str | None,
) -> None:
    session.add(
        AuditLog(
            id=uuid4(),
            actor_user_id=actor_user_id,
            action=action,
            resource_type="document",
            resource_id=resource_id,
            outcome=outcome,
            reason=reason,
            request_id=trace_id,
            trace_id=trace_id,
            before_summary=before_summary,
            after_summary=after_summary,
            source_context={},
        )
    )
