"""Review queue service.

Provides paginated review queue listing with filtering, assignment, claim,
release, and escalation operations, together with RBAC enforcement and
reviewer-specialization visibility rules.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal, cast
from uuid import UUID, uuid4

from sqlalchemy import func, select

from zayd_common.database.models import (
    AuditLog,
    Document,
    DocumentVersion,
    Feedback,
    ReviewTask,
    User,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.rbac import ROLE_PERMISSION_MATRIX, Permission
from zayd_common.review_tasks import ReviewTaskCreationError, ReviewTaskService

REVIEW_QUEUE_POLICY_VERSION = "review-queue-v1"

ReviewQueueErrorCode = Literal[
    "REVIEW_TASK_NOT_FOUND",
    "REVIEW_TASK_INVALID_STATUS",
    "REVIEW_TASK_NOT_ASSIGNED",
    "REVIEW_QUEUE_ACCESS_DENIED",
    "REVIEW_QUEUE_ESCALATION_EXISTS",
    "REVIEW_USER_NOT_FOUND",
    "REVIEW_QUEUE_ALREADY_ASSIGNED",
]

_ACTIVE_STATUSES = frozenset({"open", "in_progress"})

_PRIVILEGED_ROLES = frozenset({"admin", "senior_scholar"})


def _normalize_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class ReviewQueueError(Exception):
    """Raised when a review queue operation cannot be completed."""

    def __init__(
        self,
        code: ReviewQueueErrorCode,
        message: str,
        *,
        status_code: int = 409,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Public data objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReviewTaskSummary:
    """Lightweight summary for queue listings."""

    id: UUID
    document_version_id: UUID
    document_id: UUID
    review_level: str
    status: str
    priority: str
    category: str | None
    language: str | None
    madhhab: str | None
    assigned_to: UUID | None
    due_at: datetime | None
    created_at: datetime
    updated_at: datetime
    document_title: str | None = None
    document_type: str | None = None


@dataclass(frozen=True)
class ReviewTaskDetail:
    """Full detail including document version content references."""

    id: UUID
    document_version_id: UUID
    document_id: UUID
    review_level: str
    status: str
    priority: str
    category: str | None = None
    language: str | None = None
    madhhab: str | None = None
    assigned_to: UUID | None = None
    due_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    document_title: str | None = None
    document_type: str | None = None
    created_by: UUID = field(default_factory=uuid4)
    original_file_key: str | None = None
    extracted_text_preview: str | None = None
    filename: str | None = None
    content_type: str | None = None


@dataclass
class ReviewQueueQuery:
    """Filters and pagination for queue listing."""

    language: str | None = None
    madhhab: str | None = None
    content_type: str | None = None
    status: str | None = None
    priority: str | None = None
    assigned_to: UUID | None = None
    review_level: str | None = None
    due_before: datetime | None = None
    due_after: datetime | None = None
    limit: int = 50
    offset: int = 0


@dataclass
class ReviewQueueResult:
    """Paginated review queue result."""

    tasks: list[ReviewTaskSummary]
    total_count: int
    limit: int
    offset: int
    next_offset: int | None


@dataclass(frozen=True)
class ReviewerDashboardSummary:
    """Authorized dashboard counters for reviewer work."""

    total_visible_count: int
    pending_count: int
    assigned_count: int
    overdue_count: int
    changes_requested_count: int
    feedback_open_count: int


@dataclass(frozen=True)
class ReviewerFeedbackWorkItem:
    """Privacy-safe feedback work item for reviewer triage."""

    id: UUID
    category: str
    status: str
    answer_id: UUID | None
    citation_id: UUID | None
    created_at: datetime


@dataclass(frozen=True)
class ReviewerDashboardResult:
    """Reviewer dashboard snapshot with queue page and feedback work."""

    summary: ReviewerDashboardSummary
    queue: ReviewQueueResult
    feedback_items: list[ReviewerFeedbackWorkItem]


@dataclass(frozen=True)
class _QueuePage:
    tasks: list[ReviewTask]
    total_count: int
    limit: int
    offset: int
    next_offset: int | None


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ReviewQueueService:
    """Review queue with filtering, claim, release, assign and escalate."""

    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self.uow = uow

    # -- Queue listing -------------------------------------------------------

    def list_queue(
        self,
        query: ReviewQueueQuery,
        *,
        actor_user_id: UUID,
        principal_roles: frozenset[str],
    ) -> ReviewQueueResult:
        """List review tasks visible to the caller."""
        with self.uow:
            session = self._session()
            stmt = self._build_queue_stmt(
                session,
                actor_user_id=actor_user_id,
                principal_roles=principal_roles,
                query=query,
            )
            result = self._paginate_queue(session, stmt, query)
            doc_map = self._load_document_map(session, result.tasks)
            self.uow.commit()
            return ReviewQueueResult(
                tasks=[_task_summary(t, doc_map.get(t.document_id)) for t in result.tasks],
                total_count=result.total_count,
                limit=result.limit,
                offset=result.offset,
                next_offset=result.next_offset,
            )

    def get_dashboard(
        self,
        query: ReviewQueueQuery,
        *,
        actor_user_id: UUID,
        principal_roles: frozenset[str],
        feedback_limit: int = 5,
    ) -> ReviewerDashboardResult:
        """Return reviewer dashboard counters, queue page, and feedback work."""
        with self.uow:
            session = self._session()
            base_stmt = self._build_queue_stmt(
                session,
                actor_user_id=actor_user_id,
                principal_roles=principal_roles,
            )
            visible_tasks = list(session.execute(base_stmt).scalars().all())
            doc_map = self._load_document_map(session, visible_tasks)
            now = datetime.now(UTC)

            summary = ReviewerDashboardSummary(
                total_visible_count=len(visible_tasks),
                pending_count=sum(
                    1
                    for task in visible_tasks
                    if task.status == "open" and task.assigned_to is None
                ),
                assigned_count=sum(
                    1
                    for task in visible_tasks
                    if task.assigned_to == actor_user_id and task.status in _ACTIVE_STATUSES
                ),
                overdue_count=sum(
                    1
                    for task in visible_tasks
                    if (due_at := _normalize_utc(task.due_at)) is not None
                    and due_at < now
                    and task.status in _ACTIVE_STATUSES
                ),
                changes_requested_count=sum(
                    1
                    for task in visible_tasks
                    if (
                        (document := doc_map.get(task.document_id)) is not None
                        and document.review_status == "changes_requested"
                    )
                ),
                feedback_open_count=(
                    self._count_open_feedback(session)
                    if self._can_read_feedback(principal_roles)
                    else 0
                ),
            )

            filtered_stmt = self._build_queue_stmt(
                session,
                actor_user_id=actor_user_id,
                principal_roles=principal_roles,
                query=query,
            )
            queue_page = self._paginate_queue(session, filtered_stmt, query)
            queue_doc_map = self._load_document_map(session, queue_page.tasks)
            can_read_feedback = self._can_read_feedback(principal_roles)
            feedback_items = (
                self._list_feedback_work(
                    session,
                    limit=min(max(feedback_limit, 1), 20),
                )
                if can_read_feedback
                else []
            )
            self.uow.commit()
            return ReviewerDashboardResult(
                summary=summary,
                queue=ReviewQueueResult(
                    tasks=[
                        _task_summary(task, queue_doc_map.get(task.document_id))
                        for task in queue_page.tasks
                    ],
                    total_count=queue_page.total_count,
                    limit=queue_page.limit,
                    offset=queue_page.offset,
                    next_offset=queue_page.next_offset,
                ),
                feedback_items=feedback_items,
            )

    # -- Detail view ---------------------------------------------------------

    def get_task_detail(
        self,
        review_task_id: UUID,
        *,
        actor_user_id: UUID,
        principal_roles: frozenset[str],
    ) -> ReviewTaskDetail:
        """Get full review task detail including version references.

        Returns document-version metadata so the caller can render a
        detail view or generate signed download URLs.
        """
        with self.uow:
            session = self._session()
            task = self._get_visible_task(
                session, review_task_id, actor_user_id, principal_roles
            )
            doc = session.get(Document, task.document_id)
            version = session.get(DocumentVersion, task.document_version_id)
            meta = (version.metadata_json or {}) if version else {}

            self.uow.commit()
            return _task_detail(task, doc, version, meta)

    # -- Claim ---------------------------------------------------------------

    def claim_task(
        self,
        review_task_id: UUID,
        *,
        actor_user_id: UUID,
        trace_id: str | None = None,
    ) -> ReviewTaskSummary:
        """Claim an open unassigned task, or reclaim one already assigned."""
        with self.uow:
            session = self._session()
            task = self._get_mutable_task(session, review_task_id)

            if task.assigned_to is not None and task.assigned_to != actor_user_id:
                raise ReviewQueueError(
                    "REVIEW_QUEUE_ACCESS_DENIED",
                    "This task is assigned to another reviewer.",
                    status_code=403,
                )

            if task.status not in _ACTIVE_STATUSES:
                raise ReviewQueueError(
                    "REVIEW_TASK_INVALID_STATUS",
                    f"Cannot claim task with status '{task.status}'.",
                )

            now = datetime.now(UTC)
            if task.status == "open":
                task.status = "in_progress"
            task.assigned_to = actor_user_id
            task.updated_at = now
            session.flush()

            self._audit(
                session,
                action="review_task.claimed",
                outcome="success",
                actor_user_id=actor_user_id,
                resource_id=task.id,
                after_summary={
                    "status": task.status,
                    "assigned_to": str(actor_user_id),
                },
                trace_id=trace_id,
            )
            self.uow.commit()
            return _task_summary(task, None)

    # -- Release -------------------------------------------------------------

    def release_task(
        self,
        review_task_id: UUID,
        *,
        actor_user_id: UUID,
        principal_roles: frozenset[str],
        trace_id: str | None = None,
    ) -> ReviewTaskSummary:
        """Release a claimed task back to the open pool."""
        with self.uow:
            session = self._session()
            task = self._get_mutable_task(session, review_task_id)

            is_privileged = bool(_PRIVILEGED_ROLES & principal_roles)
            if task.assigned_to != actor_user_id and not is_privileged:
                raise ReviewQueueError(
                    "REVIEW_TASK_NOT_ASSIGNED",
                    "Task is not assigned to you.",
                    status_code=403,
                )

            if task.status not in _ACTIVE_STATUSES:
                raise ReviewQueueError(
                    "REVIEW_TASK_INVALID_STATUS",
                    f"Cannot release task with status '{task.status}'.",
                )

            now = datetime.now(UTC)
            task.status = "open"
            task.assigned_to = None
            task.updated_at = now
            session.flush()

            self._audit(
                session,
                action="review_task.released",
                outcome="success",
                actor_user_id=actor_user_id,
                resource_id=task.id,
                after_summary={"status": "open", "assigned_to": None},
                trace_id=trace_id,
            )
            self.uow.commit()
            return _task_summary(task, None)

    # -- Assign --------------------------------------------------------------

    def assign_task(
        self,
        review_task_id: UUID,
        *,
        assignee_user_id: UUID,
        actor_user_id: UUID,
        principal_roles: frozenset[str],
        trace_id: str | None = None,
    ) -> ReviewTaskSummary:
        """Assign (or re-assign) a task to a specific reviewer."""
        if not (_PRIVILEGED_ROLES & principal_roles):
            # Non-privileged users can only assign to themselves via claim
            raise ReviewQueueError(
                "REVIEW_QUEUE_ACCESS_DENIED",
                "Only admins and senior scholars can assign tasks.",
                status_code=403,
            )

        with self.uow:
            session = self._session()
            task = self._get_mutable_task(session, review_task_id)

            if task.status not in _ACTIVE_STATUSES:
                raise ReviewQueueError(
                    "REVIEW_TASK_INVALID_STATUS",
                    f"Cannot assign task with status '{task.status}'.",
                )

            # Verify assignee exists
            assignee = session.get(User, assignee_user_id)
            if assignee is None or assignee.deleted_at is not None or assignee.status != "active":
                raise ReviewQueueError(
                    "REVIEW_USER_NOT_FOUND",
                    "Assignee user was not found or is not active.",
                    status_code=404,
                )

            now = datetime.now(UTC)
            before_assigned_to = task.assigned_to
            task.assigned_to = assignee_user_id
            if task.status == "open":
                task.status = "in_progress"
            task.updated_at = now
            session.flush()

            self._audit(
                session,
                action="review_task.assigned",
                outcome="success",
                actor_user_id=actor_user_id,
                resource_id=task.id,
                before_summary=(
                    {"assigned_to": str(before_assigned_to)}
                    if before_assigned_to else None
                ),
                after_summary={
                    "assigned_to": str(assignee_user_id),
                    "status": task.status,
                },
                trace_id=trace_id,
            )
            self.uow.commit()
            return _task_summary(task, None)

    # -- Escalate ------------------------------------------------------------

    def escalate_task(
        self,
        review_task_id: UUID,
        *,
        actor_user_id: UUID,
        principal_roles: frozenset[str],
        trace_id: str | None = None,
    ) -> ReviewTaskSummary:
        """Escalate a task by creating a scholar-level review task.

        The original task is not modified; a separate scholar-level task
        is created for the same document version.  If one already exists
        the operation raises REVIEW_QUEUE_ESCALATION_EXISTS.
        """
        # Only privileged users or the assigned reviewer can escalate
        with self.uow:
            session = self._session()
            task = self._get_mutable_task(session, review_task_id)

            if task.status not in _ACTIVE_STATUSES:
                raise ReviewQueueError(
                    "REVIEW_TASK_INVALID_STATUS",
                    f"Cannot escalate task with status '{task.status}'.",
                )

            is_privileged = bool(_PRIVILEGED_ROLES & principal_roles)
            if task.assigned_to != actor_user_id and not is_privileged:
                raise ReviewQueueError(
                    "REVIEW_QUEUE_ACCESS_DENIED",
                    "Only the assigned reviewer or a privileged user can escalate.",
                    status_code=403,
                )

            self.uow.commit()

        # Create scholar-level task via existing service
        try:
            creator = ReviewTaskService(self.uow)
            doc_version_id = task.document_version_id
            _ = creator.create_review_task(
                document_version_id=doc_version_id,
                actor_user_id=actor_user_id,
                review_level="scholar",
                trace_id=trace_id,
            )
        except ReviewTaskCreationError as exc:
            if exc.code == "REVIEW_TASK_ALREADY_EXISTS":
                raise ReviewQueueError(
                    "REVIEW_QUEUE_ESCALATION_EXISTS",
                    "A scholar-level review task already exists for this version.",
                    status_code=409,
                ) from exc
            raise

        return _task_summary(task, None)

    # -- Internal helpers ----------------------------------------------------

    def _apply_visibility_filter(
        self,
        stmt: Any,
        session: Any,
        actor_user_id: UUID,
        principal_roles: frozenset[str],
    ) -> Any:
        """Filter tasks based on the caller's role and specialization."""
        is_privileged = bool(_PRIVILEGED_ROLES & principal_roles)
        if is_privileged:
            return stmt  # all tasks visible

        # Non-privileged: restrict by specialization
        user = session.get(User, actor_user_id)
        if user is None:
            return stmt.where(False)  # unknown user → no tasks

        filters: list[Any] = [ReviewTask.review_level != "scholar"]

        if "translator" in principal_roles or "reviewer" in principal_roles:
            # Language match: task language is None or matches preferred
            lang_cond = (ReviewTask.language.is_(None)) | (
                ReviewTask.language == user.preferred_language
            )
            filters.append(lang_cond)

        if "reviewer" in principal_roles:
            # Madhhab match: task madhhab is unset/unknown/general/other or matches preferred
            madhhab_cond = (ReviewTask.madhhab.is_(None)) | (
                ReviewTask.madhhab.in_(["unknown", "general", "other"])
            ) | (ReviewTask.madhhab == user.preferred_madhhab)
            filters.append(madhhab_cond)

        return stmt.where(*filters)

    def _build_queue_stmt(
        self,
        session: Any,
        *,
        actor_user_id: UUID,
        principal_roles: frozenset[str],
        query: ReviewQueueQuery | None = None,
    ) -> Any:
        stmt = self._apply_visibility_filter(
            select(ReviewTask),
            session,
            actor_user_id,
            principal_roles,
        )
        return self._apply_query_filters(stmt, query)

    @staticmethod
    def _apply_query_filters(stmt: Any, query: ReviewQueueQuery | None) -> Any:
        if query is None:
            return stmt
        if query.language is not None:
            stmt = stmt.where(ReviewTask.language == query.language)
        if query.madhhab is not None:
            stmt = stmt.where(ReviewTask.madhhab == query.madhhab)
        if query.content_type is not None:
            stmt = stmt.where(ReviewTask.category == query.content_type)
        if query.status is not None:
            stmt = stmt.where(ReviewTask.status == query.status)
        if query.priority is not None:
            stmt = stmt.where(ReviewTask.priority == query.priority)
        if query.assigned_to is not None:
            stmt = stmt.where(ReviewTask.assigned_to == query.assigned_to)
        if query.review_level is not None:
            stmt = stmt.where(ReviewTask.review_level == query.review_level)
        if query.due_before is not None:
            stmt = stmt.where(ReviewTask.due_at <= query.due_before)
        if query.due_after is not None:
            stmt = stmt.where(ReviewTask.due_at >= query.due_after)
        return stmt

    @staticmethod
    def _paginate_queue(
        session: Any,
        stmt: Any,
        query: ReviewQueueQuery,
    ) -> _QueuePage:
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_count = session.execute(count_stmt).scalar() or 0
        limit = min(max(query.limit, 1), 200)
        offset = max(query.offset, 0)
        ordered = (
            stmt.order_by(ReviewTask.created_at.desc())
            .limit(limit + 1)
            .offset(offset)
        )
        rows = list(session.execute(ordered).scalars().all())
        has_more = len(rows) > limit
        tasks = rows[:limit]
        return _QueuePage(
            tasks=tasks,
            total_count=total_count,
            limit=limit,
            offset=offset,
            next_offset=offset + len(tasks) if has_more else None,
        )

    @staticmethod
    def _count_open_feedback(session: Any) -> int:
        stmt = (
            select(func.count())
            .select_from(Feedback)
            .where(Feedback.deleted_at.is_(None))
            .where(Feedback.status == "open")
        )
        return session.execute(stmt).scalar() or 0

    @staticmethod
    def _can_read_feedback(principal_roles: frozenset[str]) -> bool:
        return any(
            Permission.FEEDBACK_READ
            in ROLE_PERMISSION_MATRIX[cast("Any", role_name)]
            for role_name in principal_roles
            if role_name in ROLE_PERMISSION_MATRIX
        )

    @staticmethod
    def _list_feedback_work(session: Any, *, limit: int) -> list[ReviewerFeedbackWorkItem]:
        rows = session.execute(
            select(Feedback)
            .where(Feedback.deleted_at.is_(None))
            .where(Feedback.status == "open")
            .order_by(Feedback.created_at.desc())
            .limit(limit)
        ).scalars().all()
        return [
            ReviewerFeedbackWorkItem(
                id=row.id,
                category=row.category,
                status=row.status,
                answer_id=row.answer_id,
                citation_id=row.citation_id,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def _get_visible_task(
        self,
        session: Any,
        review_task_id: UUID,
        actor_user_id: UUID,
        principal_roles: frozenset[str],
    ) -> ReviewTask:
        """Load a task and verify the caller is authorized to see it."""
        stmt = self._apply_visibility_filter(
            select(ReviewTask), session, actor_user_id, principal_roles
        )
        stmt = stmt.where(ReviewTask.id == review_task_id)
        task = session.execute(stmt).scalar_one_or_none()
        if task is None:
            # Also try by direct lookup in case visibility filter excluded it
            task = session.get(ReviewTask, review_task_id)
            if task is None:
                raise ReviewQueueError(
                    "REVIEW_TASK_NOT_FOUND",
                    "Review task not found.",
                    status_code=404,
                )
            raise ReviewQueueError(
                "REVIEW_QUEUE_ACCESS_DENIED",
                "You are not authorized to view this task.",
                status_code=403,
            )
        return task  # type: ignore[no-any-return]

    def _get_mutable_task(self, session: Any, review_task_id: UUID) -> ReviewTask:
        """Load a review task that exists and is mutable (not terminal)."""
        task = session.get(ReviewTask, review_task_id)
        if task is None:
            raise ReviewQueueError(
                "REVIEW_TASK_NOT_FOUND",
                "Review task not found.",
                status_code=404,
            )
        return task  # type: ignore[no-any-return]

    @staticmethod
    def _load_document_map(session: Any, tasks: Sequence[ReviewTask]) -> dict[UUID, Document]:
        """Load Document records for a list of review tasks."""
        doc_ids = {t.document_id for t in tasks}
        if not doc_ids:
            return {}
        docs = session.execute(
            select(Document).where(Document.id.in_(doc_ids))
        ).scalars().all()
        return {d.id: d for d in docs}

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
                resource_type="review_task",
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


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------


def _task_summary(task: ReviewTask, doc: Document | None) -> ReviewTaskSummary:
    return ReviewTaskSummary(
        id=task.id,
        document_version_id=task.document_version_id,
        document_id=task.document_id,
        review_level=task.review_level,
        status=task.status,
        priority=task.priority,
        category=task.category,
        language=task.language,
        madhhab=task.madhhab,
        assigned_to=task.assigned_to,
        due_at=task.due_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
        document_title=doc.title if doc else None,
        document_type=doc.document_type if doc else None,
    )


def _task_detail(
    task: ReviewTask,
    doc: Document | None,
    version: DocumentVersion | None,
    version_metadata: dict[str, Any],
) -> ReviewTaskDetail:
    extracted = (version.extracted_text or "") if version else ""
    preview = extracted[:500] if extracted else None
    return ReviewTaskDetail(
        id=task.id,
        document_version_id=task.document_version_id,
        document_id=task.document_id,
        review_level=task.review_level,
        status=task.status,
        priority=task.priority,
        category=task.category,
        language=task.language,
        madhhab=task.madhhab,
        assigned_to=task.assigned_to,
        due_at=task.due_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
        document_title=doc.title if doc else None,
        document_type=doc.document_type if doc else None,
        created_by=task.created_by,
        original_file_key=version.original_file_key if version else None,
        extracted_text_preview=preview,
        filename=version_metadata.get("filename"),
        content_type=version_metadata.get("content_type"),
    )
