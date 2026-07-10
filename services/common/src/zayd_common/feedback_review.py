"""Feedback review queue — prioritized, assignable triage for reviewer staff.

Provides the reviewer-facing operations on submitted feedback items:
- Paginated, filterable queue listing with priority ordering
- Assignment to a named reviewer
- Reviewer notes update
- Root-cause classification
- Resolution (close with corrective-action record)

RBAC:
- ``feedback.read``   — list and view feedback
- ``feedback.manage`` — assign, classify, and resolve feedback

All mutations write sanitized audit records; note bodies and reporter user IDs
are omitted from audit summaries to protect reporter privacy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import Select, case, func, select
from sqlalchemy.orm import Session

from zayd_common.database.models import Answer, AuditLog, Feedback, User
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.rbac import Permission

FEEDBACK_REVIEW_POLICY_VERSION = "feedback-review-v1"
MAX_REVIEWER_NOTES_LENGTH = 4000
MAX_RESOLUTION_LENGTH = 4000

FeedbackReviewErrorCode = Literal[
    "FEEDBACK_REVIEW_NOT_FOUND",
    "FEEDBACK_REVIEW_FORBIDDEN",
    "FEEDBACK_REVIEW_INPUT_INVALID",
    "FEEDBACK_REVIEW_ALREADY_RESOLVED",
    "FEEDBACK_REVIEW_STATUS_CONFLICT",
]

FeedbackStatus = Literal["open", "in_review", "resolved", "dismissed"]
FeedbackPriority = Literal["low", "normal", "high", "critical"]
FeedbackSeverity = Literal["p0", "p1", "p2", "p3"]
FeedbackRootCause = Literal[
    "retrieval_quality",
    "model_error",
    "citation_inaccuracy",
    "policy_gap",
    "user_misunderstanding",
    "duplicate",
    "other",
]

ALLOWED_STATUSES: frozenset[str] = frozenset({"open", "in_review", "resolved", "dismissed"})
ALLOWED_PRIORITIES: frozenset[str] = frozenset({"low", "normal", "high", "critical"})
ALLOWED_SEVERITIES: frozenset[str] = frozenset({"p0", "p1", "p2", "p3"})
ALLOWED_ROOT_CAUSES: frozenset[str] = frozenset(
    {
        "retrieval_quality",
        "model_error",
        "citation_inaccuracy",
        "policy_gap",
        "user_misunderstanding",
        "duplicate",
        "other",
    }
)

# Status transitions allowed during normal triage flow.
_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "open": frozenset({"in_review", "resolved", "dismissed"}),
    "in_review": frozenset({"open", "resolved", "dismissed"}),
    "resolved": frozenset(),
    "dismissed": frozenset(),
}

_TERMINAL_STATUSES = frozenset({"resolved", "dismissed"})

# Column ordering map for priority: critical first, then high, normal, low.
_PRIORITY_ORDER = {"critical": 0, "high": 1, "normal": 2, "low": 3}


class FeedbackReviewError(Exception):
    def __init__(
        self,
        code: FeedbackReviewErrorCode,
        message: str,
        *,
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


# ---------------------------------------------------------------------------
# Public data objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FeedbackQueueItem:
    """Privacy-safe summary for queue listings."""

    id: UUID
    category: str
    status: str
    priority: str
    severity: str
    answer_id: UUID | None
    citation_id: UUID | None
    reviewer_id: UUID | None
    root_cause: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class FeedbackReviewDetail:
    """Full reviewer detail — includes reviewer notes but omits reporter note body."""

    id: UUID
    category: str
    status: str
    priority: str
    severity: str
    answer_id: UUID | None
    citation_id: UUID | None
    reviewer_id: UUID | None
    reviewer_notes: str
    root_cause: str | None
    resolution: str | None
    resolved_at: datetime | None
    trace_context: FeedbackTraceContext | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class FeedbackTraceContext:
    """Version identifiers needed to reproduce a reported answer safely."""

    retrieval_run_id: UUID
    model_configuration_id: UUID
    prompt_version_id: UUID
    policy_version_id: UUID


@dataclass(frozen=True)
class FeedbackQueueResult:
    """Paginated queue result."""

    items: list[FeedbackQueueItem]
    total_count: int
    limit: int
    offset: int
    next_offset: int | None


@dataclass(frozen=True)
class FeedbackQueueQuery:
    """Filter and pagination inputs for queue listing."""

    status: str | None = None
    category: str | None = None
    priority: str | None = None
    severity: str | None = None
    reviewer_id: str | None = None
    unassigned_only: bool = False
    limit: int = 20
    offset: int = 0


@dataclass(frozen=True)
class FeedbackAssignRequest:
    reviewer_id: UUID | None  # None = unassign


@dataclass(frozen=True)
class FeedbackClassifyRequest:
    root_cause: str | None = None
    priority: str | None = None
    severity: str | None = None
    reviewer_notes: str | None = None


@dataclass(frozen=True)
class FeedbackResolveRequest:
    resolution: str
    dismissed: bool = False  # True → "dismissed" rather than "resolved"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class FeedbackReviewService:
    """Manages reviewer-side triage operations on submitted feedback."""

    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self.uow = uow

    # -- Queue listing -------------------------------------------------------

    def list_queue(
        self,
        query: FeedbackQueueQuery,
        *,
        actor_user_id: UUID,
        actor_permissions: frozenset[str],
    ) -> FeedbackQueueResult:
        """Return a paginated, prioritized feedback queue."""
        _require(actor_permissions, Permission.FEEDBACK_READ)
        limit = max(1, min(query.limit, 100))
        offset = max(0, query.offset)
        with self.uow:
            session = self._session()
            stmt = _build_queue_stmt(query)
            total: int = (
                session.execute(select(func.count()).select_from(stmt.subquery())).scalar() or 0
            )
            priority_rank = case(_PRIORITY_ORDER, value=Feedback.priority, else_=99)
            rows = (
                session.execute(
                    stmt.order_by(priority_rank, Feedback.created_at.asc())
                    .limit(limit)
                    .offset(offset)
                )
                .scalars()
                .all()
            )
            self.uow.commit()
            return FeedbackQueueResult(
                items=[_queue_item(r) for r in rows],
                total_count=total,
                limit=limit,
                offset=offset,
                next_offset=offset + limit if offset + limit < total else None,
            )

    def get_detail(
        self,
        feedback_id: UUID,
        *,
        actor_permissions: frozenset[str],
    ) -> FeedbackReviewDetail:
        """Return full reviewer detail for a single feedback item."""
        _require(actor_permissions, Permission.FEEDBACK_READ)
        with self.uow:
            session = self._session()
            feedback = _get_active(session, feedback_id)
            detail = _review_detail(
                feedback,
                session.get(Answer, feedback.answer_id) if feedback.answer_id else None,
            )
            self.uow.commit()
            return detail

    # -- Mutations -----------------------------------------------------------

    def assign(
        self,
        feedback_id: UUID,
        req: FeedbackAssignRequest,
        *,
        actor_user_id: UUID,
        actor_permissions: frozenset[str],
        trace_id: str | None = None,
    ) -> FeedbackReviewDetail:
        """Assign or unassign a reviewer for a feedback item."""
        _require(actor_permissions, Permission.FEEDBACK_MANAGE)
        with self.uow:
            session = self._session()
            feedback = _get_active(session, feedback_id)
            _guard_terminal(feedback)
            if req.reviewer_id is not None:
                reviewer = session.get(User, req.reviewer_id)
                if reviewer is None or reviewer.deleted_at is not None:
                    raise FeedbackReviewError(
                        "FEEDBACK_REVIEW_INPUT_INVALID",
                        "Reviewer user was not found.",
                        status_code=404,
                    )
            before_reviewer = str(feedback.reviewer_id) if feedback.reviewer_id else None
            feedback.reviewer_id = req.reviewer_id
            # Auto-transition: assigning moves to in_review; unassigning reverts to open.
            if req.reviewer_id is not None and feedback.status == "open":
                feedback.status = "in_review"
            elif req.reviewer_id is None and feedback.status == "in_review":
                feedback.status = "open"
            session.add(
                AuditLog(
                    id=uuid4(),
                    actor_user_id=actor_user_id,
                    action="feedback.assign",
                    resource_type="feedback",
                    resource_id=feedback.id,
                    outcome="success",
                    request_id=trace_id,
                    trace_id=trace_id,
                    before_summary={"reviewer_id": before_reviewer},
                    after_summary={
                        "feedback_id": str(feedback.id),
                        "reviewer_id": str(req.reviewer_id) if req.reviewer_id else None,
                        "status": feedback.status,
                    },
                    source_context={"policy_version": FEEDBACK_REVIEW_POLICY_VERSION},
                )
            )
            detail = _review_detail(feedback)
            self.uow.commit()
            return detail

    def classify(
        self,
        feedback_id: UUID,
        req: FeedbackClassifyRequest,
        *,
        actor_user_id: UUID,
        actor_permissions: frozenset[str],
        trace_id: str | None = None,
    ) -> FeedbackReviewDetail:
        """Update root-cause, priority, severity, and/or reviewer notes."""
        _require(actor_permissions, Permission.FEEDBACK_MANAGE)
        with self.uow:
            session = self._session()
            feedback = _get_active(session, feedback_id)
            _guard_terminal(feedback)
            if req.root_cause is not None:
                root_cause = req.root_cause.strip().lower()
                if root_cause not in ALLOWED_ROOT_CAUSES:
                    raise FeedbackReviewError(
                        "FEEDBACK_REVIEW_INPUT_INVALID",
                        f"root_cause must be one of: {', '.join(sorted(ALLOWED_ROOT_CAUSES))}.",
                    )
                feedback.root_cause = root_cause
            if req.priority is not None:
                priority = req.priority.strip().lower()
                if priority not in ALLOWED_PRIORITIES:
                    raise FeedbackReviewError(
                        "FEEDBACK_REVIEW_INPUT_INVALID",
                        f"priority must be one of: {', '.join(sorted(ALLOWED_PRIORITIES))}.",
                    )
                feedback.priority = priority
            if req.severity is not None:
                severity = req.severity.strip().lower()
                if severity not in ALLOWED_SEVERITIES:
                    raise FeedbackReviewError(
                        "FEEDBACK_REVIEW_INPUT_INVALID",
                        f"severity must be one of: {', '.join(sorted(ALLOWED_SEVERITIES))}.",
                    )
                feedback.severity = severity
            if req.reviewer_notes is not None:
                notes = req.reviewer_notes.strip()
                if len(notes) > MAX_REVIEWER_NOTES_LENGTH:
                    raise FeedbackReviewError(
                        "FEEDBACK_REVIEW_INPUT_INVALID",
                        f"reviewer_notes must be at most {MAX_REVIEWER_NOTES_LENGTH} characters.",
                    )
                feedback.reviewer_notes = notes
            session.add(
                AuditLog(
                    id=uuid4(),
                    actor_user_id=actor_user_id,
                    action="feedback.classify",
                    resource_type="feedback",
                    resource_id=feedback.id,
                    outcome="success",
                    request_id=trace_id,
                    trace_id=trace_id,
                    before_summary={},
                    after_summary={
                        "feedback_id": str(feedback.id),
                        "root_cause": feedback.root_cause,
                        "priority": feedback.priority,
                        "severity": feedback.severity,
                        "reviewer_notes_length": len(feedback.reviewer_notes),
                    },
                    source_context={"policy_version": FEEDBACK_REVIEW_POLICY_VERSION},
                )
            )
            detail = _review_detail(feedback)
            self.uow.commit()
            return detail

    def resolve(
        self,
        feedback_id: UUID,
        req: FeedbackResolveRequest,
        *,
        actor_user_id: UUID,
        actor_permissions: frozenset[str],
        trace_id: str | None = None,
    ) -> FeedbackReviewDetail:
        """Close the feedback item with a resolution or dismissal record."""
        _require(actor_permissions, Permission.FEEDBACK_MANAGE)
        resolution_text = req.resolution.strip()
        if not resolution_text:
            raise FeedbackReviewError(
                "FEEDBACK_REVIEW_INPUT_INVALID",
                "resolution must not be empty.",
            )
        if len(resolution_text) > MAX_RESOLUTION_LENGTH:
            raise FeedbackReviewError(
                "FEEDBACK_REVIEW_INPUT_INVALID",
                f"resolution must be at most {MAX_RESOLUTION_LENGTH} characters.",
            )
        with self.uow:
            session = self._session()
            feedback = _get_active(session, feedback_id)
            _guard_terminal(feedback)
            target_status: str = "dismissed" if req.dismissed else "resolved"
            feedback.status = target_status
            feedback.resolution = resolution_text
            feedback.resolved_at = datetime.now(UTC)
            session.add(
                AuditLog(
                    id=uuid4(),
                    actor_user_id=actor_user_id,
                    action="feedback.resolve",
                    resource_type="feedback",
                    resource_id=feedback.id,
                    outcome="success",
                    request_id=trace_id,
                    trace_id=trace_id,
                    before_summary={},
                    after_summary={
                        "feedback_id": str(feedback.id),
                        "terminal_status": target_status,
                        "resolution_length": len(resolution_text),
                    },
                    source_context={"policy_version": FEEDBACK_REVIEW_POLICY_VERSION},
                )
            )
            detail = _review_detail(feedback)
            self.uow.commit()
            return detail

    def _session(self) -> Session:
        if self.uow.session is None:
            raise RuntimeError("Database session not initialised in UoW.")
        return self.uow.session


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _require(permissions: frozenset[str], permission: Permission) -> None:
    if permission.value not in permissions:
        raise FeedbackReviewError(
            "FEEDBACK_REVIEW_FORBIDDEN",
            "Forbidden.",
            status_code=403,
        )


def _get_active(session: Session, feedback_id: UUID) -> Feedback:
    feedback = session.get(Feedback, feedback_id)
    if feedback is None or feedback.deleted_at is not None:
        raise FeedbackReviewError(
            "FEEDBACK_REVIEW_NOT_FOUND",
            "Feedback was not found.",
            status_code=404,
        )
    return feedback


def _guard_terminal(feedback: Feedback) -> None:
    if feedback.status in _TERMINAL_STATUSES:
        raise FeedbackReviewError(
            "FEEDBACK_REVIEW_ALREADY_RESOLVED",
            f"Feedback is already {feedback.status} and cannot be modified.",
            status_code=409,
        )


def _build_queue_stmt(query: FeedbackQueueQuery) -> Select[tuple[Feedback]]:
    """Build a filtered SQLAlchemy statement for the feedback queue."""
    stmt = select(Feedback).where(Feedback.deleted_at.is_(None))
    if query.status is not None:
        stmt = stmt.where(Feedback.status == query.status)
    else:
        # Default: exclude terminal statuses so queue shows actionable items.
        stmt = stmt.where(Feedback.status.notin_(list(_TERMINAL_STATUSES)))
    if query.category is not None:
        stmt = stmt.where(Feedback.category == query.category)
    if query.priority is not None:
        stmt = stmt.where(Feedback.priority == query.priority)
    if query.severity is not None:
        stmt = stmt.where(Feedback.severity == query.severity)
    if query.reviewer_id is not None:
        try:
            reviewer_id = UUID(query.reviewer_id)
        except ValueError as exc:
            raise FeedbackReviewError(
                "FEEDBACK_REVIEW_INPUT_INVALID",
                "reviewer_id must be a UUID.",
            ) from exc
        stmt = stmt.where(Feedback.reviewer_id == reviewer_id)
    if query.unassigned_only:
        stmt = stmt.where(Feedback.reviewer_id.is_(None))
    return stmt


def _queue_item(row: Feedback) -> FeedbackQueueItem:
    return FeedbackQueueItem(
        id=row.id,
        category=row.category,
        status=row.status,
        priority=row.priority,
        severity=row.severity,
        answer_id=row.answer_id,
        citation_id=row.citation_id,
        reviewer_id=row.reviewer_id,
        root_cause=row.root_cause,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _review_detail(row: Feedback, answer: Answer | None = None) -> FeedbackReviewDetail:
    return FeedbackReviewDetail(
        id=row.id,
        category=row.category,
        status=row.status,
        priority=row.priority,
        severity=row.severity,
        answer_id=row.answer_id,
        citation_id=row.citation_id,
        reviewer_id=row.reviewer_id,
        reviewer_notes=row.reviewer_notes,
        root_cause=row.root_cause,
        resolution=row.resolution,
        resolved_at=row.resolved_at,
        trace_context=(
            FeedbackTraceContext(
                retrieval_run_id=answer.retrieval_run_id,
                model_configuration_id=answer.model_configuration_id,
                prompt_version_id=answer.prompt_version_id,
                policy_version_id=answer.policy_version_id,
            )
            if answer is not None
            else None
        ),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
