from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from zayd_common.database.models import (
    AuditLog,
    AuthPermission,
    Role,
    RolePermission,
    User,
    UserRole,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork


class Permission(StrEnum):
    SESSIONS_REVOKE_OWN = "sessions.revoke_own"
    USERS_READ_SELF = "users.read_self"
    USERS_READ = "users.read"
    USERS_MANAGE = "users.manage"
    USERS_ROLES_MANAGE = "users.roles.manage"
    DOCUMENTS_READ = "documents.read"
    DOCUMENTS_UPLOAD = "documents.upload"
    DOCUMENTS_EDIT = "documents.edit"
    DOCUMENTS_REVIEW = "documents.review"
    DOCUMENTS_APPROVE = "documents.approve"
    DOCUMENTS_PUBLISH = "documents.publish"
    DOCUMENTS_ARCHIVE = "documents.archive"
    ANSWERS_REVIEW = "answers.review"
    ANSWERS_INVALIDATE = "answers.invalidate"
    PROVIDERS_READ = "providers.read"
    PROVIDERS_MANAGE = "providers.manage"
    LICENSES_READ = "licenses.read"
    LICENSES_MANAGE = "licenses.manage"
    PROMPTS_MANAGE = "prompts.manage"
    MODELS_MANAGE = "models.manage"
    AUDIT_READ = "audit.read"
    AUDIT_EXPORT = "audit.export"
    AUDIT_VERIFY = "audit.verify"
    FEEDBACK_CREATE = "feedback.create"
    FEEDBACK_READ = "feedback.read"
    FEEDBACK_MANAGE = "feedback.manage"
    CONVERSATIONS_MANAGE_OWN = "conversations.manage_own"


RoleName = Literal[
    "guest",
    "user",
    "data_operator",
    "translator",
    "reviewer",
    "senior_scholar",
    "admin",
    "auditor",
    "maintainer",
]

RbacErrorCode = Literal[
    "RBAC_FORBIDDEN",
    "RBAC_UNKNOWN_PERMISSION",
    "RBAC_UNKNOWN_ROLE",
    "RBAC_UNKNOWN_USER",
    "RBAC_SEPARATION_OF_DUTIES",
    "RBAC_LAST_ADMIN",
]

ROLE_DESCRIPTIONS: dict[RoleName, str] = {
    "guest": "Anonymous session with no privileged back-office access.",
    "user": "Registered user with own-session, conversation and feedback access.",
    "data_operator": "Imports and prepares documents before review.",
    "translator": "Edits translation-oriented document metadata and text.",
    "reviewer": "Reviews documents, answers and supporting evidence.",
    "senior_scholar": "Approves high-impact religious content and publishing decisions.",
    "admin": "Manages users, roles, providers, licenses, prompts and models.",
    "auditor": "Reads audit and approved operational records without mutation rights.",
    "maintainer": "Maintains provider/model/prompt configuration for releases.",
}

ROLE_PERMISSION_MATRIX: dict[RoleName, set[Permission]] = {
    "guest": set(),
    "user": {
        Permission.SESSIONS_REVOKE_OWN,
        Permission.USERS_READ_SELF,
        Permission.FEEDBACK_CREATE,
        Permission.CONVERSATIONS_MANAGE_OWN,
    },
    "data_operator": {
        Permission.SESSIONS_REVOKE_OWN,
        Permission.USERS_READ_SELF,
        Permission.DOCUMENTS_READ,
        Permission.DOCUMENTS_UPLOAD,
        Permission.DOCUMENTS_EDIT,
        Permission.LICENSES_READ,
    },
    "translator": {
        Permission.SESSIONS_REVOKE_OWN,
        Permission.USERS_READ_SELF,
        Permission.DOCUMENTS_READ,
        Permission.DOCUMENTS_EDIT,
        Permission.DOCUMENTS_REVIEW,
        Permission.LICENSES_READ,
    },
    "reviewer": {
        Permission.SESSIONS_REVOKE_OWN,
        Permission.USERS_READ_SELF,
        Permission.DOCUMENTS_READ,
        Permission.DOCUMENTS_REVIEW,
        Permission.ANSWERS_REVIEW,
        Permission.FEEDBACK_READ,
        Permission.LICENSES_READ,
    },
    "senior_scholar": {
        Permission.SESSIONS_REVOKE_OWN,
        Permission.USERS_READ_SELF,
        Permission.DOCUMENTS_READ,
        Permission.DOCUMENTS_REVIEW,
        Permission.DOCUMENTS_APPROVE,
        Permission.DOCUMENTS_PUBLISH,
        Permission.DOCUMENTS_ARCHIVE,
        Permission.ANSWERS_REVIEW,
        Permission.ANSWERS_INVALIDATE,
        Permission.LICENSES_READ,
    },
    "admin": {
        Permission.SESSIONS_REVOKE_OWN,
        Permission.USERS_READ_SELF,
        Permission.USERS_READ,
        Permission.USERS_MANAGE,
        Permission.USERS_ROLES_MANAGE,
        Permission.DOCUMENTS_READ,
        Permission.DOCUMENTS_UPLOAD,
        Permission.DOCUMENTS_EDIT,
        Permission.DOCUMENTS_REVIEW,
        Permission.DOCUMENTS_APPROVE,
        Permission.DOCUMENTS_PUBLISH,
        Permission.DOCUMENTS_ARCHIVE,
        Permission.ANSWERS_REVIEW,
        Permission.ANSWERS_INVALIDATE,
        Permission.PROVIDERS_READ,
        Permission.PROVIDERS_MANAGE,
        Permission.LICENSES_READ,
        Permission.LICENSES_MANAGE,
        Permission.PROMPTS_MANAGE,
        Permission.MODELS_MANAGE,
        Permission.AUDIT_READ,
        Permission.AUDIT_EXPORT,
        Permission.AUDIT_VERIFY,
        Permission.FEEDBACK_READ,
        Permission.FEEDBACK_MANAGE,
    },
    "auditor": {
        Permission.SESSIONS_REVOKE_OWN,
        Permission.USERS_READ_SELF,
        Permission.USERS_READ,
        Permission.DOCUMENTS_READ,
        Permission.PROVIDERS_READ,
        Permission.LICENSES_READ,
        Permission.AUDIT_READ,
        Permission.AUDIT_EXPORT,
        Permission.AUDIT_VERIFY,
        Permission.FEEDBACK_READ,
    },
    "maintainer": {
        Permission.SESSIONS_REVOKE_OWN,
        Permission.USERS_READ_SELF,
        Permission.PROVIDERS_READ,
        Permission.PROVIDERS_MANAGE,
        Permission.PROMPTS_MANAGE,
        Permission.MODELS_MANAGE,
        Permission.AUDIT_READ,
    },
}

ALL_PERMISSION_VALUES = {permission.value for permission in Permission}


class RbacError(Exception):
    def __init__(self, code: RbacErrorCode, message: str, *, status_code: int = 403) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class UserPrincipal:
    id: UUID
    email: str
    status: str
    roles: frozenset[str]
    permissions: frozenset[str]


def ensure_registered_user_role(session: Session, *, user_id: UUID) -> None:
    _bootstrap_system_roles_in_session(session)
    user_role = session.execute(select(Role).where(Role.name == "user")).scalar_one()
    existing = session.get(UserRole, (user_id, user_role.id))
    if existing is None:
        session.add(UserRole(user_id=user_id, role_id=user_role.id, granted_by=user_id))


class RbacService:
    def __init__(self, uow: SQLAlchemyUnitOfWork) -> None:
        self.uow = uow

    def bootstrap_system_roles(self) -> None:
        with self.uow:
            session = self._session()
            _bootstrap_system_roles_in_session(session)
            self.uow.commit()

    def get_principal(self, user_id: UUID) -> UserPrincipal:
        with self.uow:
            principal = self._get_principal_in_session(user_id)
            self.uow.commit()
            return principal

    def require_permission(
        self,
        *,
        user_id: UUID,
        permission: Permission | str,
        trace_id: str | None = None,
    ) -> UserPrincipal:
        permission_value = _permission_value(permission)
        with self.uow:
            principal = self._get_principal_in_session(user_id)
            if permission_value not in principal.permissions:
                self._audit(
                    action="rbac.permission.check",
                    outcome="denied",
                    actor_user_id=user_id,
                    reason="permission_missing",
                    after_summary={"permission": permission_value},
                    trace_id=trace_id,
                )
                self.uow.commit()
                raise RbacError("RBAC_FORBIDDEN", "Forbidden.", status_code=403)
            self.uow.commit()
            return principal

    def grant_role(
        self,
        *,
        actor_user_id: UUID,
        target_user_id: UUID,
        role_name: str,
        trace_id: str | None = None,
    ) -> bool:
        normalized_role = _normalize_role_name(role_name)
        with self.uow:
            session = self._session()
            _bootstrap_system_roles_in_session(session)
            self._require_permission_in_session(
                actor_user_id,
                Permission.USERS_ROLES_MANAGE,
                trace_id=trace_id,
            )
            target = session.get(User, target_user_id)
            if target is None or target.deleted_at is not None:
                raise RbacError("RBAC_UNKNOWN_USER", "User was not found.", status_code=404)
            role = session.execute(
                select(Role).where(Role.name == normalized_role)
            ).scalar_one_or_none()
            if role is None:
                raise RbacError("RBAC_UNKNOWN_ROLE", "Role was not found.", status_code=404)
            existing = session.get(UserRole, (target_user_id, role.id))
            if existing is not None:
                self.uow.commit()
                return False
            session.add(UserRole(user_id=target_user_id, role_id=role.id, granted_by=actor_user_id))
            self._audit(
                action="rbac.role.grant",
                outcome="success",
                actor_user_id=actor_user_id,
                resource_id=target_user_id,
                after_summary={"role": role.name, "target_user_id": str(target_user_id)},
                trace_id=trace_id,
            )
            self.uow.commit()
            return True

    def revoke_role(
        self,
        *,
        actor_user_id: UUID,
        target_user_id: UUID,
        role_name: str,
        trace_id: str | None = None,
    ) -> bool:
        normalized_role = _normalize_role_name(role_name)
        with self.uow:
            session = self._session()
            _bootstrap_system_roles_in_session(session)
            self._require_permission_in_session(
                actor_user_id,
                Permission.USERS_ROLES_MANAGE,
                trace_id=trace_id,
            )
            target = session.get(User, target_user_id)
            if target is None or target.deleted_at is not None:
                raise RbacError("RBAC_UNKNOWN_USER", "User was not found.", status_code=404)
            role = session.execute(
                select(Role).where(Role.name == normalized_role)
            ).scalar_one_or_none()
            if role is None:
                raise RbacError("RBAC_UNKNOWN_ROLE", "Role was not found.", status_code=404)
            existing = session.get(UserRole, (target_user_id, role.id))
            if existing is None:
                self.uow.commit()
                return False
            if role.name == "admin" and self._active_admin_count_in_session() <= 1:
                self._audit(
                    action="rbac.role.revoke",
                    outcome="denied",
                    actor_user_id=actor_user_id,
                    resource_id=target_user_id,
                    reason="last_admin",
                    after_summary={"role": role.name, "target_user_id": str(target_user_id)},
                    trace_id=trace_id,
                )
                self.uow.commit()
                raise RbacError(
                    "RBAC_LAST_ADMIN",
                    "At least one active admin role assignment is required.",
                    status_code=409,
                )
            session.delete(existing)
            self._audit(
                action="rbac.role.revoke",
                outcome="success",
                actor_user_id=actor_user_id,
                resource_id=target_user_id,
                after_summary={"role": role.name, "target_user_id": str(target_user_id)},
                trace_id=trace_id,
            )
            self.uow.commit()
            return True

    def assert_can_approve_document(
        self,
        *,
        actor_user_id: UUID,
        document_created_by: UUID,
        trace_id: str | None = None,
    ) -> UserPrincipal:
        with self.uow:
            principal = self._require_permission_in_session(
                actor_user_id,
                Permission.DOCUMENTS_APPROVE,
                trace_id=trace_id,
            )
            if actor_user_id == document_created_by:
                self._audit(
                    action="rbac.separation_of_duties.documents.approve",
                    outcome="denied",
                    actor_user_id=actor_user_id,
                    resource_id=document_created_by,
                    reason="actor_uploaded_document",
                    trace_id=trace_id,
                )
                self.uow.commit()
                raise RbacError(
                    "RBAC_SEPARATION_OF_DUTIES",
                    "Uploader cannot approve their own restricted work.",
                    status_code=403,
                )
            self.uow.commit()
            return principal

    def _require_permission_in_session(
        self,
        user_id: UUID,
        permission: Permission | str,
        *,
        trace_id: str | None,
    ) -> UserPrincipal:
        permission_value = _permission_value(permission)
        principal = self._get_principal_in_session(user_id)
        if permission_value not in principal.permissions:
            self._audit(
                action="rbac.permission.check",
                outcome="denied",
                actor_user_id=user_id,
                reason="permission_missing",
                after_summary={"permission": permission_value},
                trace_id=trace_id,
            )
            self.uow.commit()
            raise RbacError("RBAC_FORBIDDEN", "Forbidden.", status_code=403)
        return principal

    def _get_principal_in_session(self, user_id: UUID) -> UserPrincipal:
        session = self._session()
        _bootstrap_system_roles_in_session(session)
        user = session.get(User, user_id)
        if user is None or user.deleted_at is not None or user.status != "active":
            raise RbacError("RBAC_UNKNOWN_USER", "User was not found.", status_code=404)
        roles = frozenset(
            session.execute(
                select(Role.name)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == user_id)
                .where(Role.deleted_at.is_(None))
            )
            .scalars()
            .all()
        )
        permissions = frozenset(
            f"{resource}.{action}"
            for resource, action in session.execute(
                select(AuthPermission.resource, AuthPermission.action)
                .join(RolePermission, RolePermission.permission_id == AuthPermission.id)
                .join(Role, Role.id == RolePermission.role_id)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == user_id)
                .where(Role.deleted_at.is_(None))
            ).all()
        )
        return UserPrincipal(
            id=user.id,
            email=user.email,
            status=user.status,
            roles=roles,
            permissions=permissions,
        )

    def _active_admin_count_in_session(self) -> int:
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

    def _audit(
        self,
        *,
        action: str,
        outcome: str,
        actor_user_id: UUID | None = None,
        resource_id: UUID | None = None,
        reason: str | None = None,
        before_summary: dict[str, Any] | None = None,
        after_summary: dict[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> None:
        self._session().add(
            AuditLog(
                id=uuid4(),
                actor_user_id=actor_user_id,
                action=action,
                resource_type="rbac",
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


def _bootstrap_system_roles_in_session(session: Session) -> None:
    existing_permissions = {
        f"{resource}.{action}"
        for resource, action in session.execute(
            select(AuthPermission.resource, AuthPermission.action)
        ).all()
    }
    for permission in Permission:
        resource, action = permission.value.split(".", 1)
        if permission.value not in existing_permissions:
            session.add(
                AuthPermission(
                    id=uuid4(),
                    resource=resource,
                    action=action,
                    description=f"Allow {permission.value}.",
                )
            )
    existing_roles = set(session.execute(select(Role.name)).scalars().all())
    for role_name, description in ROLE_DESCRIPTIONS.items():
        if role_name not in existing_roles:
            session.add(Role(id=uuid4(), name=role_name, description=description, is_system=True))
    session.flush()

    permissions_by_value = {
        f"{permission.resource}.{permission.action}": permission
        for permission in session.execute(select(AuthPermission)).scalars().all()
    }
    roles_by_name = {role.name: role for role in session.execute(select(Role)).scalars().all()}
    for role_name, permissions in ROLE_PERMISSION_MATRIX.items():
        role = roles_by_name[role_name]
        for permission in permissions:
            permission_record = permissions_by_value[permission.value]
            existing = session.get(RolePermission, (role.id, permission_record.id))
            if existing is None:
                session.add(RolePermission(role_id=role.id, permission_id=permission_record.id))


def _permission_value(permission: Permission | str) -> str:
    permission_value = permission.value if isinstance(permission, Permission) else permission
    if permission_value not in ALL_PERMISSION_VALUES:
        raise RbacError("RBAC_UNKNOWN_PERMISSION", "Permission was not found.", status_code=400)
    return permission_value


def _normalize_role_name(role_name: str) -> str:
    normalized_role = role_name.strip().lower()
    if normalized_role not in ROLE_DESCRIPTIONS:
        raise RbacError("RBAC_UNKNOWN_ROLE", "Role was not found.", status_code=404)
    return normalized_role
