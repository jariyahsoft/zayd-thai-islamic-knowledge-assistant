"""Admin services for user, role, and session operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from zayd_common.database.models import (
    AuditLog,
    AuthRefreshToken,
    AuthSession,
    Role,
    User,
    UserRole,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork

UserAdminErrorCode = Literal[
    "USER_ADMIN_NOT_FOUND",
    "USER_ADMIN_STATUS_INVALID",
    "USER_ADMIN_LAST_ADMIN",
]

VALID_USER_STATUSES = {"active", "disabled"}


class UserAdminError(Exception):
    """Stable admin user-management error."""

    def __init__(
        self,
        code: UserAdminErrorCode,
        message: str,
        *,
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class AdminUserPublic:
    id: UUID
    email: str
    display_name: str
    status: str
    roles: tuple[str, ...]
    active_session_count: int
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime
    row_version: int
    last_admin_guarded: bool


class UserAdminService:
    """Manage admin-facing user listings, status, and session revocation."""

    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self.uow = uow

    def list_users(
        self,
        *,
        query: str | None = None,
        status: str | None = None,
        role: str | None = None,
    ) -> list[AdminUserPublic]:
        with self.uow:
            statement = select(User).where(User.deleted_at.is_(None))
            if query is not None and query.strip():
                pattern = f"%{query.strip().lower()}%"
                statement = statement.where(
                    User.email.ilike(pattern) | User.display_name.ilike(pattern)
                )
            if status is not None and status.strip():
                normalized_status = _normalize_status(status)
                statement = statement.where(User.status == normalized_status)
            users = list(
                self._session()
                .execute(statement.order_by(User.created_at.desc(), User.id.desc()))
                .scalars()
                .all()
            )
            if role is not None and role.strip():
                normalized_role = role.strip().lower()
                users = [user for user in users if normalized_role in self._roles_for_user(user.id)]
            self.uow.commit()
            return [self._public_user(user) for user in users]

    def get_user(self, *, user_id: UUID) -> AdminUserPublic:
        with self.uow:
            user = self._get_user(user_id)
            self.uow.commit()
            return self._public_user(user)

    def set_status(
        self,
        *,
        user_id: UUID,
        status: str,
        actor_user_id: UUID,
        trace_id: str | None = None,
    ) -> AdminUserPublic:
        normalized_status = _normalize_status(status)
        now = datetime.now(UTC)
        with self.uow:
            user = self._get_user(user_id)
            before = {"status": user.status}
            if user.status == normalized_status:
                self.uow.commit()
                return self._public_user(user)
            if normalized_status == "disabled" and self._is_last_active_admin_candidate(user):
                self._audit(
                    action="users.status.update",
                    actor_user_id=actor_user_id,
                    resource_id=user.id,
                    trace_id=trace_id,
                    outcome="denied",
                    reason="last_admin",
                    after_summary={"status": normalized_status},
                )
                self.uow.commit()
                raise UserAdminError(
                    "USER_ADMIN_LAST_ADMIN",
                    "At least one active admin account must remain enabled.",
                    status_code=409,
                )
            user.status = normalized_status
            user.row_version += 1
            if normalized_status == "disabled":
                revoked_count = self._revoke_sessions_for_user(user_id=user.id, now=now)
            else:
                revoked_count = 0
            self._audit(
                action="users.status.update",
                actor_user_id=actor_user_id,
                resource_id=user.id,
                trace_id=trace_id,
                before_summary=before,
                after_summary={
                    "status": normalized_status,
                    "revoked_session_count": revoked_count,
                },
            )
            self.uow.commit()
            return self._public_user(user)

    def revoke_sessions(
        self,
        *,
        user_id: UUID,
        actor_user_id: UUID,
        trace_id: str | None = None,
    ) -> int:
        now = datetime.now(UTC)
        with self.uow:
            user = self._get_user(user_id)
            revoked = self._revoke_sessions_for_user(user_id=user.id, now=now)
            self._audit(
                action="users.sessions.revoke",
                actor_user_id=actor_user_id,
                resource_id=user.id,
                trace_id=trace_id,
                after_summary={"revoked_session_count": revoked},
            )
            self.uow.commit()
            return revoked

    def _public_user(self, user: User) -> AdminUserPublic:
        roles = self._roles_for_user(user.id)
        return AdminUserPublic(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            status=user.status,
            roles=tuple(sorted(roles)),
            active_session_count=self._active_session_count(user.id),
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
            row_version=user.row_version,
            last_admin_guarded=user.status == "active"
            and "admin" in roles
            and self._active_admin_count() <= 1,
        )

    def _get_user(self, user_id: UUID) -> User:
        user = self._session().get(User, user_id)
        if user is None or user.deleted_at is not None:
            raise UserAdminError(
                "USER_ADMIN_NOT_FOUND",
                "User was not found.",
                status_code=404,
            )
        return user

    def _roles_for_user(self, user_id: UUID) -> set[str]:
        rows = self._session().execute(
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
            .where(Role.deleted_at.is_(None))
        ).scalars().all()
        return set(rows)

    def _active_session_count(self, user_id: UUID) -> int:
        return len(
            self._session()
            .execute(
                select(AuthSession.id)
                .where(AuthSession.user_id == user_id)
                .where(AuthSession.revoked_at.is_(None))
            )
            .all()
        )

    def _revoke_sessions_for_user(self, *, user_id: UUID, now: datetime) -> int:
        sessions = (
            self._session()
            .execute(
                select(AuthSession)
                .where(AuthSession.user_id == user_id)
                .where(AuthSession.revoked_at.is_(None))
            )
            .scalars()
            .all()
        )
        for auth_session in sessions:
            auth_session.revoked_at = now
            tokens = (
                self._session()
                .execute(
                    select(AuthRefreshToken)
                    .where(AuthRefreshToken.session_id == auth_session.id)
                    .where(AuthRefreshToken.revoked_at.is_(None))
                )
                .scalars()
                .all()
            )
            for token in tokens:
                token.revoked_at = now
        return len(sessions)

    def _active_admin_count(self) -> int:
        rows = (
            self._session()
            .execute(
                select(UserRole.user_id)
                .join(Role, Role.id == UserRole.role_id)
                .join(User, User.id == UserRole.user_id)
                .where(Role.name == "admin")
                .where(Role.deleted_at.is_(None))
                .where(User.deleted_at.is_(None))
                .where(User.status == "active")
            )
            .all()
        )
        return len(rows)

    def _is_last_active_admin_candidate(self, user: User) -> bool:
        return (
            "admin" in self._roles_for_user(user.id)
            and user.status == "active"
            and self._active_admin_count() <= 1
        )

    def _audit(
        self,
        *,
        action: str,
        actor_user_id: UUID | None,
        resource_id: UUID | None,
        trace_id: str | None,
        outcome: str = "success",
        reason: str | None = None,
        before_summary: dict[str, Any] | None = None,
        after_summary: dict[str, Any] | None = None,
    ) -> None:
        self._session().add(
            AuditLog(
                id=uuid4(),
                actor_user_id=actor_user_id,
                action=action,
                resource_type="user",
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

    def _session(self) -> Session:
        if self.uow.session is None:
            raise RuntimeError("Database session not initialized in UoW.")
        return self.uow.session


def _normalize_status(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in VALID_USER_STATUSES:
        raise UserAdminError(
            "USER_ADMIN_STATUS_INVALID",
            "Status must be active or disabled.",
            status_code=400,
        )
    return normalized
