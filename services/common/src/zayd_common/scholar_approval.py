"""Scholar approval workflow service.

Provides explicit senior-scholar and board approval records with separation of
 duties, expiry, revocation, and publishing requirement checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from sqlalchemy import select

from zayd_common.database.models import (
    AuditLog,
    Document,
    DocumentVersion,
    ReviewApproval,
    ReviewDecisionRecord,
    ReviewTask,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

SCHOLAR_APPROVAL_POLICY_VERSION = "scholar-approval-v1"

ApprovalErrorCode = Literal[
    "SCHOLAR_APPROVAL_TASK_NOT_FOUND",
    "SCHOLAR_APPROVAL_VERSION_NOT_FOUND",
    "SCHOLAR_APPROVAL_ACCESS_DENIED",
    "SCHOLAR_APPROVAL_INVALID_STATUS",
    "SCHOLAR_APPROVAL_SELF_APPROVAL_DENIED",
    "SCHOLAR_APPROVAL_DUPLICATE_ACTIVE",
    "SCHOLAR_APPROVAL_NOT_FOUND",
    "SCHOLAR_APPROVAL_ALREADY_TERMINAL",
]

ContentRisk = Literal["routine", "sensitive", "restricted"]
ApprovalLevel = Literal["initial", "scholar", "board"]

_PRIVILEGED_APPROVERS = frozenset({"admin", "senior_scholar"})
_BOARD_APPROVERS = frozenset({"admin"})
_REQUIRED_BY_RISK: dict[str, tuple[str, ...]] = {
    "routine": ("initial",),
    "sensitive": ("initial", "scholar"),
    "restricted": ("initial", "scholar", "board"),
}


class ScholarApprovalError(Exception):
    """Raised when scholar approval workflow cannot continue."""

    def __init__(
        self,
        code: ApprovalErrorCode,
        message: str,
        *,
        status_code: int = 409,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class ApprovalRequirement:
    document_version_id: UUID
    content_risk: str
    required_levels: list[str]
    satisfied_levels: list[str]
    missing_levels: list[str]
    ready_for_publish: bool


@dataclass(frozen=True)
class ApprovalPublic:
    id: UUID
    document_version_id: UUID
    review_task_id: UUID
    approver_id: UUID
    approval_level: str
    content_risk: str
    status: str
    reason: str
    valid_until: datetime | None
    revoked_at: datetime | None
    revoked_by: UUID | None
    revoke_reason: str | None
    created_at: datetime


@dataclass(frozen=True)
class ApprovalListResult:
    document_version_id: UUID
    approvals: list[ApprovalPublic]


class ScholarApprovalService:
    """Manages senior-scholar and board approvals for document versions."""

    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self.uow = uow

    def get_requirements(
        self,
        *,
        document_version_id: UUID,
        content_risk: str,
    ) -> ApprovalRequirement:
        """Return approval completeness for a content-risk tier."""
        normalized_risk = _normalize_risk(content_risk)
        with self.uow:
            session = self._session()
            version = session.get(DocumentVersion, document_version_id)
            if version is None:
                raise ScholarApprovalError(
                    "SCHOLAR_APPROVAL_VERSION_NOT_FOUND",
                    "Document version not found.",
                    status_code=404,
                )
            required = list(_REQUIRED_BY_RISK[normalized_risk])
            approvals = self._active_approvals_for_version(session, document_version_id)
            active_levels = {approval.approval_level for approval in approvals}
            satisfied = [level for level in required if level in active_levels]
            missing = [level for level in required if level not in satisfied]
            self.uow.commit()
            return ApprovalRequirement(
                document_version_id=document_version_id,
                content_risk=normalized_risk,
                required_levels=required,
                satisfied_levels=satisfied,
                missing_levels=missing,
                ready_for_publish=not missing,
            )

    def list_approvals(
        self,
        *,
        document_version_id: UUID,
    ) -> ApprovalListResult:
        """Return recorded approvals for one document version."""
        with self.uow:
            session = self._session()
            version = session.get(DocumentVersion, document_version_id)
            if version is None:
                raise ScholarApprovalError(
                    "SCHOLAR_APPROVAL_VERSION_NOT_FOUND",
                    "Document version not found.",
                    status_code=404,
                )
            approvals = session.execute(
                select(ReviewApproval)
                .where(ReviewApproval.document_version_id == document_version_id)
                .order_by(ReviewApproval.created_at.desc(), ReviewApproval.id.desc())
            ).scalars().all()
            self.uow.commit()
            return ApprovalListResult(
                document_version_id=document_version_id,
                approvals=[_approval_public(approval) for approval in approvals],
            )

    def approve(
        self,
        *,
        review_task_id: UUID,
        actor_user_id: UUID,
        principal_roles: frozenset[str],
        content_risk: str,
        approval_level: str,
        reason: str,
        valid_until: datetime | None = None,
        trace_id: str | None = None,
    ) -> ApprovalPublic:
        """Create an explicit approval record for a document version."""
        normalized_risk = _normalize_risk(content_risk)
        normalized_level = _normalize_level(approval_level)
        normalized_reason = reason.strip()
        if not normalized_reason:
            raise ScholarApprovalError(
                "SCHOLAR_APPROVAL_INVALID_STATUS",
                "Approval reason is required.",
                status_code=400,
            )
        with self.uow:
            session = self._session()
            task = session.get(ReviewTask, review_task_id)
            if task is None:
                raise ScholarApprovalError(
                    "SCHOLAR_APPROVAL_TASK_NOT_FOUND",
                    "Review task not found.",
                    status_code=404,
                )
            document = session.get(Document, task.document_id)
            if document is None:
                raise ScholarApprovalError(
                    "SCHOLAR_APPROVAL_VERSION_NOT_FOUND",
                    "Document was not found for this review task.",
                    status_code=404,
                )
            self._assert_level_role(normalized_level, principal_roles)
            self._assert_task_allows_approval(task, normalized_level)
            self._assert_separation_of_duties(session, task, document, actor_user_id)
            existing = self._active_approval_for_level(
                session, task.document_version_id, normalized_level
            )
            if existing is not None:
                raise ScholarApprovalError(
                    "SCHOLAR_APPROVAL_DUPLICATE_ACTIVE",
                    "An active approval already exists for this level.",
                )
            now = datetime.now(UTC)
            approval = ReviewApproval(
                id=uuid4(),
                document_version_id=task.document_version_id,
                review_task_id=task.id,
                approver_id=actor_user_id,
                approval_level=normalized_level,
                content_risk=normalized_risk,
                status="active",
                reason=normalized_reason,
                valid_until=valid_until,
                created_at=now,
                updated_at=now,
            )
            session.add(approval)
            self._audit(
                session,
                action="scholar_approval.created",
                outcome="success",
                actor_user_id=actor_user_id,
                resource_id=approval.id,
                after_summary={
                    "document_version_id": str(task.document_version_id),
                    "review_task_id": str(task.id),
                    "approval_level": normalized_level,
                    "content_risk": normalized_risk,
                    "valid_until": valid_until.isoformat() if valid_until else None,
                    "policy_version": SCHOLAR_APPROVAL_POLICY_VERSION,
                },
                trace_id=trace_id,
            )
            public = _approval_public(approval)
            self.uow.commit()
            return public

    def revoke(
        self,
        *,
        approval_id: UUID,
        actor_user_id: UUID,
        principal_roles: frozenset[str],
        reason: str,
        trace_id: str | None = None,
    ) -> ApprovalPublic:
        """Revoke an active approval."""
        normalized_reason = reason.strip()
        if not normalized_reason:
            raise ScholarApprovalError(
                "SCHOLAR_APPROVAL_INVALID_STATUS",
                "Revocation reason is required.",
                status_code=400,
            )
        if not principal_roles & _PRIVILEGED_APPROVERS:
            raise ScholarApprovalError(
                "SCHOLAR_APPROVAL_ACCESS_DENIED",
                "Only senior scholars or admins can revoke approvals.",
                status_code=403,
            )
        with self.uow:
            session = self._session()
            approval = session.get(ReviewApproval, approval_id)
            if approval is None:
                raise ScholarApprovalError(
                    "SCHOLAR_APPROVAL_NOT_FOUND",
                    "Approval record not found.",
                    status_code=404,
                )
            if approval.status != "active":
                raise ScholarApprovalError(
                    "SCHOLAR_APPROVAL_ALREADY_TERMINAL",
                    "Approval is already expired or revoked.",
                )
            now = datetime.now(UTC)
            approval.status = "revoked"
            approval.revoked_at = now
            approval.revoked_by = actor_user_id
            approval.revoke_reason = normalized_reason
            approval.updated_at = now
            session.flush()
            self._audit(
                session,
                action="scholar_approval.revoked",
                outcome="success",
                actor_user_id=actor_user_id,
                resource_id=approval.id,
                after_summary={
                    "document_version_id": str(approval.document_version_id),
                    "approval_level": approval.approval_level,
                    "status": "revoked",
                    "policy_version": SCHOLAR_APPROVAL_POLICY_VERSION,
                },
                trace_id=trace_id,
            )
            public = _approval_public(approval)
            self.uow.commit()
            return public

    def expire_approvals(
        self,
        *,
        now: datetime | None = None,
        trace_id: str | None = None,
    ) -> int:
        """Mark active approvals past valid_until as expired."""
        current_time = now or datetime.now(UTC)
        with self.uow:
            session = self._session()
            approvals = list(
                session.execute(
                    select(ReviewApproval)
                    .where(ReviewApproval.status == "active")
                    .where(ReviewApproval.valid_until.is_not(None))
                    .where(ReviewApproval.valid_until <= current_time)
                ).scalars().all()
            )
            for approval in approvals:
                approval.status = "expired"
                approval.updated_at = current_time
                self._audit(
                    session,
                    action="scholar_approval.expired",
                    outcome="success",
                    resource_id=approval.id,
                    after_summary={
                        "document_version_id": str(approval.document_version_id),
                        "approval_level": approval.approval_level,
                        "status": "expired",
                        "policy_version": SCHOLAR_APPROVAL_POLICY_VERSION,
                    },
                    trace_id=trace_id,
                )
            self.uow.commit()
            return len(approvals)

    def _assert_level_role(self, level: str, principal_roles: frozenset[str]) -> None:
        if level == "board":
            if not principal_roles & _BOARD_APPROVERS:
                raise ScholarApprovalError(
                    "SCHOLAR_APPROVAL_ACCESS_DENIED",
                    "Board approval requires admin role.",
                    status_code=403,
                )
            return
        if level == "scholar" and not principal_roles & _PRIVILEGED_APPROVERS:
            raise ScholarApprovalError(
                "SCHOLAR_APPROVAL_ACCESS_DENIED",
                "Scholar approval requires senior scholar or admin role.",
                status_code=403,
            )

    @staticmethod
    def _assert_task_allows_approval(task: ReviewTask, level: str) -> None:
        if level == "initial":
            if task.status not in {"open", "in_progress", "completed"}:
                raise ScholarApprovalError(
                    "SCHOLAR_APPROVAL_INVALID_STATUS",
                    "Initial approval requires an active or completed review task.",
                )
            return
        if task.review_level not in {"scholar", "board"} and level in {"scholar", "board"}:
            raise ScholarApprovalError(
                "SCHOLAR_APPROVAL_INVALID_STATUS",
                "Scholar or board approval requires an escalated review task.",
            )
        if task.status not in {"open", "in_progress", "completed"}:
            raise ScholarApprovalError(
                "SCHOLAR_APPROVAL_INVALID_STATUS",
                "Approval requires an active or completed review task.",
            )

    @staticmethod
    def _assert_separation_of_duties(
        session: Any,
        task: ReviewTask,
        document: Document,
        actor_user_id: UUID,
    ) -> None:
        if actor_user_id in {document.created_by, task.created_by}:
            raise ScholarApprovalError(
                "SCHOLAR_APPROVAL_SELF_APPROVAL_DENIED",
                "Uploader or task creator cannot approve their own document version.",
                status_code=403,
            )
        reviewer_ids = set(
            session.execute(
                select(ReviewDecisionRecord.actor_user_id)
                .where(ReviewDecisionRecord.document_version_id == task.document_version_id)
                .where(ReviewDecisionRecord.decision == "approve")
            ).scalars().all()
        )
        if actor_user_id in reviewer_ids:
            raise ScholarApprovalError(
                "SCHOLAR_APPROVAL_SELF_APPROVAL_DENIED",
                "The same reviewer cannot satisfy another approval level.",
                status_code=403,
            )
        approval_actor_ids = set(
            session.execute(
                select(ReviewApproval.approver_id)
                .where(ReviewApproval.document_version_id == task.document_version_id)
                .where(ReviewApproval.status == "active")
            ).scalars().all()
        )
        if actor_user_id in approval_actor_ids:
            raise ScholarApprovalError(
                "SCHOLAR_APPROVAL_SELF_APPROVAL_DENIED",
                "The same approver cannot satisfy multiple approval levels.",
                status_code=403,
            )

    @staticmethod
    def _active_approval_for_level(
        session: Any,
        document_version_id: UUID,
        approval_level: str,
    ) -> ReviewApproval | None:
        approval: ReviewApproval | None = session.execute(
            select(ReviewApproval)
            .where(ReviewApproval.document_version_id == document_version_id)
            .where(ReviewApproval.approval_level == approval_level)
            .where(ReviewApproval.status == "active")
        ).scalar_one_or_none()
        return approval

    @staticmethod
    def _active_approvals_for_version(
        session: Any,
        document_version_id: UUID,
    ) -> list[ReviewApproval]:
        now = datetime.now(UTC)
        return list(
            session.execute(
                select(ReviewApproval)
                .where(ReviewApproval.document_version_id == document_version_id)
                .where(ReviewApproval.status == "active")
                .where(
                    (ReviewApproval.valid_until.is_(None))
                    | (ReviewApproval.valid_until > now)
                )
            ).scalars().all()
        )

    @staticmethod
    def _audit(
        session: Any,
        *,
        action: str,
        outcome: str,
        actor_user_id: UUID | None = None,
        resource_id: UUID | None = None,
        after_summary: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> None:
        session.add(
            AuditLog(
                id=uuid4(),
                actor_user_id=actor_user_id,
                action=action,
                resource_type="scholar_approval",
                resource_id=resource_id,
                outcome=outcome,
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


def _normalize_risk(content_risk: str) -> str:
    normalized = content_risk.strip().lower()
    if normalized not in _REQUIRED_BY_RISK:
        raise ScholarApprovalError(
            "SCHOLAR_APPROVAL_INVALID_STATUS",
            "content_risk must be routine, sensitive, or restricted.",
            status_code=400,
        )
    return normalized


def _normalize_level(approval_level: str) -> str:
    normalized = approval_level.strip().lower()
    if normalized not in {"initial", "scholar", "board"}:
        raise ScholarApprovalError(
            "SCHOLAR_APPROVAL_INVALID_STATUS",
            "approval_level must be initial, scholar, or board.",
            status_code=400,
        )
    return normalized


def _approval_public(approval: ReviewApproval) -> ApprovalPublic:
    return ApprovalPublic(
        id=approval.id,
        document_version_id=approval.document_version_id,
        review_task_id=approval.review_task_id,
        approver_id=approval.approver_id,
        approval_level=approval.approval_level,
        content_risk=approval.content_risk,
        status=approval.status,
        reason=approval.reason,
        valid_until=approval.valid_until,
        revoked_at=approval.revoked_at,
        revoked_by=approval.revoked_by,
        revoke_reason=approval.revoke_reason,
        created_at=approval.created_at,
    )
