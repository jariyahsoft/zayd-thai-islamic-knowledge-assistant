"""Review task creation service.

Creates review tasks after successful parsing/extraction.  Each reviewable
document version gets one active review task per review level.  Failed or
quarantined documents are excluded from review.

Assignment rules are configurable and map document metadata (category,
language, madhhab) to review priority, review level, and optional due dates.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

from zayd_common.database.models import AuditLog, ReviewTask
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

REVIEW_TASK_POLICY_VERSION = "review-task-creation-v1"

ReviewTaskCreationErrorCode = Literal[
    "REVIEW_VERSION_NOT_FOUND",
    "REVIEW_VERSION_NOT_ELIGIBLE",
    "REVIEW_TASK_ALREADY_EXISTS",
]


class ReviewTaskCreationError(Exception):
    """Raised when a review task cannot be created."""

    def __init__(
        self,
        code: ReviewTaskCreationErrorCode,
        message: str,
        *,
        status_code: int = 409,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Assignment rules — configurable mapping
# ---------------------------------------------------------------------------

#: Default review level assigned per document type.
DEFAULT_REVIEW_LEVEL: str = "initial"

#: Priority mapping by madhhab and language (lower = higher priority).
_PRIORITY_MAP: dict[str, str] = {
    # Higher priority for documents in the primary school of thought
    "shafii": "high",
    "hanafi": "high",
    "maliki": "normal",
    "hanbali": "normal",
    "jafari": "normal",
}

#: Default priority when no rule matches.
_DEFAULT_PRIORITY: str = "normal"

#: Due date offset in days by priority.
_DUE_DAYS_BY_PRIORITY: dict[str, int] = {
    "urgent": 3,
    "high": 7,
    "normal": 14,
    "low": 30,
}

#: Document version statuses that are eligible for review creation.
_ELIGIBLE_VERSION_STATUSES: frozenset[str] = frozenset({
    "scanned_clean",
    "parsed",
})

#: Document review statuses that are eligible for review creation.
_ELIGIBLE_REVIEW_STATUSES: frozenset[str] = frozenset({
    "draft",
    "revision_requested",
})


def resolve_priority(madhhab: str | None, language: str | None) -> str:
    """Resolve review priority from document metadata.

    The priority mapping can be extended via configuration.
    """
    del language  # future use: language-based priority
    if madhhab and madhhab.lower() in _PRIORITY_MAP:
        return _PRIORITY_MAP[madhhab.lower()]
    return _DEFAULT_PRIORITY


def resolve_due_at(priority: str) -> datetime | None:
    """Calculate the optional due date based on priority."""
    days = _DUE_DAYS_BY_PRIORITY.get(priority)
    if days is None:
        return None
    return datetime.now(UTC) + timedelta(days=days)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ReviewTaskService:
    """Creates and manages review tasks for document versions."""

    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self.uow = uow

    def create_review_task(
        self,
        *,
        document_version_id: UUID,
        actor_user_id: UUID,
        review_level: str | None = None,
        trace_id: str | None = None,
    ) -> ReviewTask:
        """Create a review task for the given document version.

        Steps:
        1. Load the document version and its document.
        2. Verify the version is eligible (not failed/infected).
        3. Verify no active review task exists (idempotency).
        4. Resolve priority, review level, and due date from rules.
        5. Persist the review task and audit the creation.
        """
        with self.uow:
            version = self.uow.documents.get_version_by_id(document_version_id)
            if version is None:
                raise ReviewTaskCreationError(
                    "REVIEW_VERSION_NOT_FOUND",
                    "Document version not found.",
                    status_code=404,
                )
            document = self.uow.documents.get_by_id(version.document_id)
            if document is None:
                raise ReviewTaskCreationError(
                    "REVIEW_VERSION_NOT_FOUND",
                    "Document not found.",
                    status_code=404,
                )

            # Check eligibility
            if version.status not in _ELIGIBLE_VERSION_STATUSES:
                raise ReviewTaskCreationError(
                    "REVIEW_VERSION_NOT_ELIGIBLE",
                    f"Document version status '{version.status}' is not eligible for review.",
                )
            if document.review_status not in _ELIGIBLE_REVIEW_STATUSES:
                raise ReviewTaskCreationError(
                    "REVIEW_VERSION_NOT_ELIGIBLE",
                    f"Document review status '{document.review_status}'"
                    " is not eligible for review.",
                )

            # Resolve assignment parameters
            level = review_level or DEFAULT_REVIEW_LEVEL
            priority = resolve_priority(document.madhhab, document.language)
            due_at = resolve_due_at(priority)

            # Check idempotency — one active task per version + level
            existing = self.uow.review_tasks.find_active_for_version(
                document_version_id, level
            )
            if existing is not None:
                raise ReviewTaskCreationError(
                    "REVIEW_TASK_ALREADY_EXISTS",
                    f"An active review task already exists for "
                    f"version {document_version_id} at level '{level}'.",
                )

            # Create the review task
            review_task = ReviewTask(
                id=uuid4(),
                document_version_id=version.id,
                document_id=document.id,
                assigned_to=None,
                review_level=level,
                status="open",
                priority=priority,
                category=document.document_type,
                language=document.language,
                madhhab=document.madhhab,
                due_at=due_at,
                created_by=actor_user_id,
            )
            self.uow.review_tasks.create(review_task)

            # Audit the creation
            audit_summary: dict[str, Any] = {
                "document_version_id": str(version.id),
                "document_id": str(document.id),
                "review_level": level,
                "priority": priority,
                "status": "open",
                "policy_version": REVIEW_TASK_POLICY_VERSION,
            }
            if due_at:
                audit_summary["due_at"] = due_at.isoformat()

            self._audit(
                action="review_task.created",
                outcome="success",
                actor_user_id=actor_user_id,
                resource_id=review_task.id,
                document_id=document.id,
                after_summary=audit_summary,
                trace_id=trace_id,
            )
            self.uow.commit()
            return review_task

    def _audit(
        self,
        *,
        action: str,
        outcome: str,
        actor_user_id: UUID | None = None,
        resource_id: UUID | None = None,
        document_id: UUID | None = None,
        after_summary: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> None:
        session = self.uow.session
        assert session is not None, "Session must be initialized within UoW context."
        session.add(
            AuditLog(
                id=uuid4(),
                actor_user_id=actor_user_id,
                action=action,
                resource_type="review_task",
                resource_id=resource_id,
                outcome=outcome,
                after_summary=after_summary,
                request_id=trace_id,
                trace_id=trace_id,
                source_context={},
            )
        )
