"""Document review draft, revision, comment, and decision service."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from difflib import unified_diff
from typing import Any, Literal
from uuid import UUID, uuid4

from sqlalchemy import func, select

from zayd_common.database.models import (
    AuditLog,
    Document,
    DocumentVersion,
    ReviewComment,
    ReviewDecisionRecord,
    ReviewRevision,
    ReviewTask,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.enums import DocumentStatus, ReviewDecision, ReviewTaskStatus
from zayd_common.exceptions import InvalidStateTransitionError
from zayd_common.state_machines import (
    DocumentStateMachine,
    ReviewTaskStateMachine,
    TransitionMetadata,
)

DOCUMENT_REVIEW_POLICY_VERSION = "document-review-v1"

DocumentReviewErrorCode = Literal[
    "DOCUMENT_REVIEW_TASK_NOT_FOUND",
    "DOCUMENT_REVIEW_ACCESS_DENIED",
    "DOCUMENT_REVIEW_INVALID_STATUS",
    "DOCUMENT_REVIEW_CONFLICT",
    "DOCUMENT_REVIEW_EMPTY_EDIT",
    "DOCUMENT_REVIEW_EMPTY_COMMENT",
    "DOCUMENT_REVIEW_INVALID_DECISION",
    "DOCUMENT_REVIEW_SELF_APPROVAL_DENIED",
    "DOCUMENT_REVIEW_VERSION_NOT_FOUND",
]

_ACTIVE_STATUSES = frozenset({"open", "in_progress"})
_PRIVILEGED_ROLES = frozenset({"admin", "senior_scholar"})
_REVIEW_ROLES = frozenset({"reviewer", "translator"})
_METADATA_EDITABLE_FIELDS = frozenset({
    "title",
    "author",
    "translator",
    "publisher",
    "edition",
    "language",
    "madhhab",
    "document_type",
    "translation_notes",
    "review_notes",
    "references",
})


class DocumentReviewError(Exception):
    """Raised when a document-review operation cannot be completed."""

    def __init__(
        self,
        code: DocumentReviewErrorCode,
        message: str,
        *,
        status_code: int = 409,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class ReviewRevisionPublic:
    id: UUID
    review_task_id: UUID
    document_version_id: UUID
    actor_user_id: UUID
    revision_number: int
    base_task_row_version: int
    text_changed: bool
    metadata_changed_fields: list[str]
    diff_text: str
    created_at: datetime


@dataclass(frozen=True)
class ReviewCommentPublic:
    id: UUID
    review_task_id: UUID
    author_id: UUID
    body: str
    anchor: dict[str, Any]
    created_at: datetime


@dataclass(frozen=True)
class ReviewDecisionPublic:
    id: UUID
    review_task_id: UUID
    document_version_id: UUID
    actor_user_id: UUID
    decision: str
    reason: str
    resulting_task_status: str
    resulting_document_status: str
    created_at: datetime


@dataclass(frozen=True)
class ReviewDraft:
    review_task_id: UUID
    document_version_id: UUID
    task_status: str
    task_row_version: int
    document_review_status: str
    original_file_key: str | None
    editable_text: str | None
    editable_metadata: dict[str, Any]
    latest_revision_number: int
    comments: list[ReviewCommentPublic] = field(default_factory=list)


@dataclass(frozen=True)
class ReviewEditResult:
    revision: ReviewRevisionPublic
    task_row_version: int
    editable_text: str | None
    editable_metadata: dict[str, Any]


@dataclass(frozen=True)
class ReviewDecisionResult:
    decision: ReviewDecisionPublic
    task_row_version: int


class DocumentReviewService:
    """Handles mutable review drafts while preserving immutable source uploads."""

    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self.uow = uow

    def get_draft(
        self,
        review_task_id: UUID,
        *,
        actor_user_id: UUID,
        principal_roles: frozenset[str],
    ) -> ReviewDraft:
        """Return the current editable draft for a visible review task."""
        with self.uow:
            session = self._session()
            task = self._get_accessible_task(
                session, review_task_id, actor_user_id, principal_roles
            )
            version = self._get_version(session, task.document_version_id)
            document = session.get(Document, task.document_id)
            latest = self._latest_revision(session, review_task_id)
            comments = session.execute(
                select(ReviewComment)
                .where(ReviewComment.review_task_id == review_task_id)
                .where(ReviewComment.deleted_at.is_(None))
                .order_by(ReviewComment.created_at.asc())
            ).scalars().all()
            draft = ReviewDraft(
                review_task_id=task.id,
                document_version_id=task.document_version_id,
                task_status=task.status,
                task_row_version=task.row_version,
                document_review_status=document.review_status if document else "unknown",
                original_file_key=version.original_file_key,
                editable_text=latest.text_after if latest else version.extracted_text,
                editable_metadata=dict(latest.metadata_after)
                if latest
                else _editable_metadata(document, version),
                latest_revision_number=latest.revision_number if latest else 0,
                comments=[_comment_public(comment) for comment in comments],
            )
            self.uow.commit()
            return draft

    def apply_edit(
        self,
        review_task_id: UUID,
        *,
        actor_user_id: UUID,
        principal_roles: frozenset[str],
        base_task_row_version: int,
        text: str | None = None,
        metadata_updates: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> ReviewEditResult:
        """Apply text/metadata draft edits and create an immutable revision."""
        with self.uow:
            session = self._session()
            task = self._get_accessible_task(
                session, review_task_id, actor_user_id, principal_roles
            )
            self._assert_mutable(task)
            self._assert_row_version(task, base_task_row_version)
            version = self._get_version(session, task.document_version_id)
            document = session.get(Document, task.document_id)
            latest = self._latest_revision(session, review_task_id)

            before_text = latest.text_after if latest else version.extracted_text
            before_metadata = (
                dict(latest.metadata_after) if latest else _editable_metadata(document, version)
            )
            after_text = before_text if text is None else text
            after_metadata = dict(before_metadata)
            for key, value in (metadata_updates or {}).items():
                if key in _METADATA_EDITABLE_FIELDS:
                    after_metadata[key] = value

            text_changed = after_text != before_text
            metadata_changed = _changed_metadata_fields(before_metadata, after_metadata)
            if not text_changed and not metadata_changed:
                raise DocumentReviewError(
                    "DOCUMENT_REVIEW_EMPTY_EDIT",
                    "Edit did not change text or editable metadata.",
                    status_code=400,
                )

            now = datetime.now(UTC)
            revision_number = self._next_revision_number(session, review_task_id)
            diff_summary = _diff_summary(
                before_text=before_text,
                after_text=after_text,
                before_metadata=before_metadata,
                after_metadata=after_metadata,
            )
            revision = ReviewRevision(
                id=uuid4(),
                review_task_id=task.id,
                document_version_id=task.document_version_id,
                actor_user_id=actor_user_id,
                revision_number=revision_number,
                base_task_row_version=base_task_row_version,
                text_before=before_text,
                text_after=after_text,
                metadata_before=before_metadata,
                metadata_after=after_metadata,
                diff_summary=diff_summary,
                created_at=now,
            )
            session.add(revision)
            before_row_version = task.row_version
            task.row_version += 1
            task.status = "in_progress"
            task.assigned_to = actor_user_id if task.assigned_to is None else task.assigned_to
            task.updated_at = now
            session.flush()

            self._audit(
                session,
                action="document_review.revision.created",
                outcome="success",
                actor_user_id=actor_user_id,
                resource_id=task.id,
                before_summary={"row_version": before_row_version},
                after_summary={
                    "row_version": task.row_version,
                    "revision_number": revision_number,
                    "text_changed": text_changed,
                    "metadata_changed_fields": metadata_changed,
                    "policy_version": DOCUMENT_REVIEW_POLICY_VERSION,
                },
                trace_id=trace_id,
            )
            public = _revision_public(revision)
            self.uow.commit()
            return ReviewEditResult(
                revision=public,
                task_row_version=task.row_version,
                editable_text=after_text,
                editable_metadata=after_metadata,
            )

    def add_comment(
        self,
        review_task_id: UUID,
        *,
        actor_user_id: UUID,
        principal_roles: frozenset[str],
        body: str,
        anchor: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> ReviewCommentPublic:
        """Add an immutable reviewer comment to a review task."""
        normalized_body = body.strip()
        if not normalized_body:
            raise DocumentReviewError(
                "DOCUMENT_REVIEW_EMPTY_COMMENT",
                "Comment body is required.",
                status_code=400,
            )
        with self.uow:
            session = self._session()
            task = self._get_accessible_task(
                session, review_task_id, actor_user_id, principal_roles
            )
            self._assert_mutable(task)
            comment = ReviewComment(
                id=uuid4(),
                review_task_id=task.id,
                author_id=actor_user_id,
                body=normalized_body,
                anchor_json=anchor or {},
            )
            session.add(comment)
            task.updated_at = datetime.now(UTC)
            session.flush()
            self._audit(
                session,
                action="document_review.comment.created",
                outcome="success",
                actor_user_id=actor_user_id,
                resource_id=task.id,
                after_summary={
                    "comment_id": str(comment.id),
                    "anchor_keys": sorted((anchor or {}).keys()),
                    "policy_version": DOCUMENT_REVIEW_POLICY_VERSION,
                },
                trace_id=trace_id,
            )
            public = _comment_public(comment)
            self.uow.commit()
            return public

    def decide(
        self,
        review_task_id: UUID,
        *,
        actor_user_id: UUID,
        principal_roles: frozenset[str],
        decision: str,
        reason: str,
        base_task_row_version: int,
        trace_id: str | None = None,
    ) -> ReviewDecisionResult:
        """Apply a request-changes, reject, or approve decision."""
        normalized_decision = decision.strip().lower()
        normalized_reason = reason.strip()
        if normalized_decision not in {
            ReviewDecision.APPROVE.value,
            ReviewDecision.REQUEST_CHANGES.value,
            ReviewDecision.REJECT.value,
        }:
            raise DocumentReviewError(
                "DOCUMENT_REVIEW_INVALID_DECISION",
                "Decision must be approve, request_changes, or reject.",
                status_code=400,
            )
        if not normalized_reason:
            raise DocumentReviewError(
                "DOCUMENT_REVIEW_INVALID_DECISION",
                "A decision reason is required.",
                status_code=400,
            )

        with self.uow:
            session = self._session()
            task = self._get_accessible_task(
                session, review_task_id, actor_user_id, principal_roles
            )
            self._assert_mutable(task)
            self._assert_row_version(task, base_task_row_version)
            document = session.get(Document, task.document_id)
            if document is None:
                raise DocumentReviewError(
                    "DOCUMENT_REVIEW_VERSION_NOT_FOUND",
                    "Document was not found for this review task.",
                    status_code=404,
                )

            if normalized_decision == ReviewDecision.APPROVE.value:
                self._assert_can_approve(task, document, actor_user_id, principal_roles)
                next_document_status = (
                    DocumentStatus.SCHOLAR_REVIEW
                    if task.review_level != "scholar"
                    else DocumentStatus.SCHOLAR_APPROVED
                )
                next_task_status = ReviewTaskStatus.COMPLETED
            elif normalized_decision == ReviewDecision.REQUEST_CHANGES.value:
                next_document_status = DocumentStatus.CHANGES_REQUESTED
                next_task_status = ReviewTaskStatus.COMPLETED
            else:
                next_document_status = DocumentStatus.REJECTED
                next_task_status = ReviewTaskStatus.COMPLETED

            self._validate_transitions(
                task=task,
                document=document,
                next_task_status=next_task_status,
                next_document_status=next_document_status,
                actor_user_id=actor_user_id,
                reason=normalized_reason,
            )

            now = datetime.now(UTC)
            before_summary = {
                "task_status": task.status,
                "document_review_status": document.review_status,
                "row_version": task.row_version,
            }
            task.status = next_task_status.value
            task.row_version += 1
            task.updated_at = now
            document.review_status = next_document_status.value
            document.updated_by = actor_user_id
            document.updated_at = now

            decision_record = ReviewDecisionRecord(
                id=uuid4(),
                review_task_id=task.id,
                document_version_id=task.document_version_id,
                actor_user_id=actor_user_id,
                decision=normalized_decision,
                reason=normalized_reason,
                base_task_row_version=base_task_row_version,
                resulting_task_status=task.status,
                resulting_document_status=document.review_status,
                created_at=now,
            )
            session.add(decision_record)
            session.flush()
            self._audit(
                session,
                action=f"document_review.decision.{normalized_decision}",
                outcome="success",
                actor_user_id=actor_user_id,
                resource_id=task.id,
                before_summary=before_summary,
                after_summary={
                    "decision_id": str(decision_record.id),
                    "task_status": task.status,
                    "document_review_status": document.review_status,
                    "row_version": task.row_version,
                    "policy_version": DOCUMENT_REVIEW_POLICY_VERSION,
                },
                trace_id=trace_id,
            )
            public = _decision_public(decision_record)
            self.uow.commit()
            return ReviewDecisionResult(decision=public, task_row_version=task.row_version)

    def _get_accessible_task(
        self,
        session: Any,
        review_task_id: UUID,
        actor_user_id: UUID,
        principal_roles: frozenset[str],
    ) -> ReviewTask:
        task = session.get(ReviewTask, review_task_id)
        if task is None:
            raise DocumentReviewError(
                "DOCUMENT_REVIEW_TASK_NOT_FOUND",
                "Review task not found.",
                status_code=404,
            )
        is_privileged = bool(principal_roles & _PRIVILEGED_ROLES)
        if task.assigned_to not in (None, actor_user_id) and not is_privileged:
            raise DocumentReviewError(
                "DOCUMENT_REVIEW_ACCESS_DENIED",
                "This review task is assigned to another reviewer.",
                status_code=403,
            )
        if not is_privileged and not (principal_roles & _REVIEW_ROLES):
            raise DocumentReviewError(
                "DOCUMENT_REVIEW_ACCESS_DENIED",
                "You are not authorized to edit this review task.",
                status_code=403,
            )
        if task.review_level == "scholar" and "senior_scholar" not in principal_roles and "admin" not in principal_roles:
            raise DocumentReviewError(
                "DOCUMENT_REVIEW_ACCESS_DENIED",
                "Scholar-level review requires a senior scholar or admin role.",
                status_code=403,
            )
        return task  # type: ignore[no-any-return]

    @staticmethod
    def _get_version(session: Any, document_version_id: UUID) -> DocumentVersion:
        version = session.get(DocumentVersion, document_version_id)
        if version is None:
            raise DocumentReviewError(
                "DOCUMENT_REVIEW_VERSION_NOT_FOUND",
                "Document version not found.",
                status_code=404,
            )
        return version  # type: ignore[no-any-return]

    @staticmethod
    def _assert_mutable(task: ReviewTask) -> None:
        if task.status not in _ACTIVE_STATUSES:
            raise DocumentReviewError(
                "DOCUMENT_REVIEW_INVALID_STATUS",
                f"Cannot edit or decide task with status '{task.status}'.",
            )

    @staticmethod
    def _assert_row_version(task: ReviewTask, base_task_row_version: int) -> None:
        if task.row_version != base_task_row_version:
            raise DocumentReviewError(
                "DOCUMENT_REVIEW_CONFLICT",
                "Review task changed since the draft was loaded.",
                status_code=409,
            )

    @staticmethod
    def _assert_can_approve(
        task: ReviewTask,
        document: Document,
        actor_user_id: UUID,
        principal_roles: frozenset[str],
    ) -> None:
        if "admin" not in principal_roles and "senior_scholar" not in principal_roles and task.review_level == "scholar":
            raise DocumentReviewError(
                "DOCUMENT_REVIEW_ACCESS_DENIED",
                "Scholar approval requires senior scholar or admin role.",
                status_code=403,
            )
        if actor_user_id in {document.created_by, task.created_by}:
            raise DocumentReviewError(
                "DOCUMENT_REVIEW_SELF_APPROVAL_DENIED",
                "Uploader or task creator cannot approve their own review task.",
                status_code=403,
            )

    @staticmethod
    def _validate_transitions(
        *,
        task: ReviewTask,
        document: Document,
        next_task_status: ReviewTaskStatus,
        next_document_status: DocumentStatus,
        actor_user_id: UUID,
        reason: str,
    ) -> None:
        metadata = TransitionMetadata(actor_id=str(actor_user_id), reason=reason)
        try:
            ReviewTaskStateMachine.validate_transition(
                ReviewTaskStatus(task.status), next_task_status, metadata
            )
            DocumentStateMachine.validate_transition(
                DocumentStatus(document.review_status), next_document_status, metadata
            )
        except (InvalidStateTransitionError, ValueError) as exc:
            raise DocumentReviewError(
                "DOCUMENT_REVIEW_INVALID_STATUS",
                "Decision does not follow the configured state machine.",
            ) from exc

    @staticmethod
    def _latest_revision(session: Any, review_task_id: UUID) -> ReviewRevision | None:
        return session.execute(
            select(ReviewRevision)
            .where(ReviewRevision.review_task_id == review_task_id)
            .order_by(ReviewRevision.revision_number.desc())
            .limit(1)
        ).scalar_one_or_none()

    @staticmethod
    def _next_revision_number(session: Any, review_task_id: UUID) -> int:
        value = session.execute(
            select(func.max(ReviewRevision.revision_number)).where(
                ReviewRevision.review_task_id == review_task_id
            )
        ).scalar_one_or_none()
        return int(value or 0) + 1

    @staticmethod
    def _audit(
        session: Any,
        *,
        action: str,
        outcome: str,
        actor_user_id: UUID | None = None,
        resource_id: UUID | None = None,
        before_summary: dict[str, Any] | None = None,
        after_summary: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> None:
        session.add(
            AuditLog(
                id=uuid4(),
                actor_user_id=actor_user_id,
                action=action,
                resource_type="document_review",
                resource_id=resource_id,
                outcome=outcome,
                before_summary=before_summary,
                after_summary=after_summary,
                request_id=trace_id,
                trace_id=trace_id,
                source_context={},
            )
        )

    def _session(self) -> Any:
        if self.uow.session is None:
            raise RuntimeError("Database session not initialised in UoW.")
        return self.uow.session


def _editable_metadata(document: Document | None, version: DocumentVersion) -> dict[str, Any]:
    metadata = dict(version.metadata_json or {})
    if document is not None:
        metadata.update(
            {
                "title": document.title,
                "author": document.author,
                "translator": document.translator,
                "publisher": document.publisher,
                "edition": document.edition,
                "language": document.language,
                "madhhab": document.madhhab,
                "document_type": document.document_type,
            }
        )
    return metadata


def _changed_metadata_fields(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    keys = set(before) | set(after)
    return sorted(key for key in keys if before.get(key) != after.get(key))


def _diff_summary(
    *,
    before_text: str | None,
    after_text: str | None,
    before_metadata: dict[str, Any],
    after_metadata: dict[str, Any],
) -> dict[str, Any]:
    diff_lines = list(
        unified_diff(
            (before_text or "").splitlines(),
            (after_text or "").splitlines(),
            fromfile="before.txt",
            tofile="after.txt",
            lineterm="",
        )
    )
    changed_fields = _changed_metadata_fields(before_metadata, after_metadata)
    return {
        "text_changed": before_text != after_text,
        "metadata_changed_fields": changed_fields,
        "diff_text": "\n".join(diff_lines[:400]),
        "diff_truncated": len(diff_lines) > 400,
    }


def _revision_public(revision: ReviewRevision) -> ReviewRevisionPublic:
    diff_summary = revision.diff_summary or {}
    return ReviewRevisionPublic(
        id=revision.id,
        review_task_id=revision.review_task_id,
        document_version_id=revision.document_version_id,
        actor_user_id=revision.actor_user_id,
        revision_number=revision.revision_number,
        base_task_row_version=revision.base_task_row_version,
        text_changed=bool(diff_summary.get("text_changed", False)),
        metadata_changed_fields=list(diff_summary.get("metadata_changed_fields", [])),
        diff_text=str(diff_summary.get("diff_text", "")),
        created_at=revision.created_at,
    )


def _comment_public(comment: ReviewComment) -> ReviewCommentPublic:
    return ReviewCommentPublic(
        id=comment.id,
        review_task_id=comment.review_task_id,
        author_id=comment.author_id,
        body=comment.body,
        anchor=dict(comment.anchor_json or {}),
        created_at=comment.created_at,
    )


def _decision_public(decision: ReviewDecisionRecord) -> ReviewDecisionPublic:
    return ReviewDecisionPublic(
        id=decision.id,
        review_task_id=decision.review_task_id,
        document_version_id=decision.document_version_id,
        actor_user_id=decision.actor_user_id,
        decision=decision.decision,
        reason=decision.reason,
        resulting_task_status=decision.resulting_task_status,
        resulting_document_status=decision.resulting_document_status,
        created_at=decision.created_at,
    )
