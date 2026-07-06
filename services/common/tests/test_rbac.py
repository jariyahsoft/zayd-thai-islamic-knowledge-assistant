import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.auth import AuthService
from zayd_common.database.models import AuditLog, Base, Role, UserRole
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.rbac import ROLE_PERMISSION_MATRIX, Permission, RbacError, RbacService


@pytest.fixture
def services() -> tuple[AuthService, RbacService]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    return (
        AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret"),
        RbacService(SQLAlchemyUnitOfWork(session_factory)),
    )


def test_permission_matrix_covers_core_capabilities() -> None:
    all_permissions = set().union(*ROLE_PERMISSION_MATRIX.values())

    for permission in (
        Permission.DOCUMENTS_UPLOAD,
        Permission.DOCUMENTS_REVIEW,
        Permission.DOCUMENTS_APPROVE,
        Permission.ANSWERS_INVALIDATE,
        Permission.PROVIDERS_MANAGE,
        Permission.LICENSES_MANAGE,
        Permission.USERS_ROLES_MANAGE,
        Permission.AUDIT_READ,
    ):
        assert permission in all_permissions

    assert Permission.AUDIT_EXPORT in ROLE_PERMISSION_MATRIX["auditor"]
    assert Permission.USERS_ROLES_MANAGE not in ROLE_PERMISSION_MATRIX["auditor"]
    assert ROLE_PERMISSION_MATRIX["guest"] == set()


def test_registered_user_gets_least_privilege_user_role(
    services: tuple[AuthService, RbacService],
) -> None:
    auth_service, rbac_service = services
    result = auth_service.register(
        email="user@example.com",
        password="very-strong-password",
        display_name="User",
    )

    principal = rbac_service.get_principal(result.user.id)

    assert principal.roles == frozenset({"user"})
    assert Permission.USERS_READ_SELF.value in principal.permissions
    assert Permission.USERS_ROLES_MANAGE.value not in principal.permissions


def test_horizontal_privilege_escalation_is_forbidden_and_audited(
    services: tuple[AuthService, RbacService],
) -> None:
    auth_service, rbac_service = services
    actor = auth_service.register(
        email="actor@example.com",
        password="very-strong-password",
        display_name="Actor",
    )
    target = auth_service.register(
        email="target@example.com",
        password="very-strong-password",
        display_name="Target",
    )

    with pytest.raises(RbacError) as exc_info:
        rbac_service.grant_role(
            actor_user_id=actor.user.id,
            target_user_id=target.user.id,
            role_name="admin",
        )

    assert exc_info.value.code == "RBAC_FORBIDDEN"
    with rbac_service.uow:
        session = rbac_service.uow.session
        assert session is not None
        audit_logs = session.execute(select(AuditLog)).scalars().all()
        assert any(
            log.action == "rbac.permission.check"
            and log.outcome == "denied"
            and log.reason == "permission_missing"
            for log in audit_logs
        )


def test_admin_can_grant_role_and_role_change_is_audited(
    services: tuple[AuthService, RbacService],
) -> None:
    auth_service, rbac_service = services
    admin = auth_service.register(
        email="admin@example.com",
        password="very-strong-password",
        display_name="Admin",
    )
    reviewer = auth_service.register(
        email="reviewer@example.com",
        password="very-strong-password",
        display_name="Reviewer",
    )
    _grant_admin_directly(rbac_service, admin.user.id)

    changed = rbac_service.grant_role(
        actor_user_id=admin.user.id,
        target_user_id=reviewer.user.id,
        role_name="reviewer",
        trace_id="trace-rbac-grant",
    )

    assert changed is True
    reviewer_principal = rbac_service.get_principal(reviewer.user.id)
    assert "reviewer" in reviewer_principal.roles
    assert Permission.DOCUMENTS_REVIEW.value in reviewer_principal.permissions
    with rbac_service.uow:
        session = rbac_service.uow.session
        assert session is not None
        audit_logs = session.execute(select(AuditLog)).scalars().all()
        assert any(
            log.action == "rbac.role.grant"
            and log.outcome == "success"
            and log.trace_id == "trace-rbac-grant"
            for log in audit_logs
        )


def test_uploader_cannot_approve_own_restricted_document(
    services: tuple[AuthService, RbacService],
) -> None:
    auth_service, rbac_service = services
    scholar = auth_service.register(
        email="scholar@example.com",
        password="very-strong-password",
        display_name="Scholar",
    )
    _grant_role_directly(rbac_service, scholar.user.id, "senior_scholar")

    with pytest.raises(RbacError) as exc_info:
        rbac_service.assert_can_approve_document(
            actor_user_id=scholar.user.id,
            document_created_by=scholar.user.id,
        )

    assert exc_info.value.code == "RBAC_SEPARATION_OF_DUTIES"


def test_last_admin_cannot_be_revoked(services: tuple[AuthService, RbacService]) -> None:
    auth_service, rbac_service = services
    admin = auth_service.register(
        email="admin@example.com",
        password="very-strong-password",
        display_name="Admin",
    )
    _grant_admin_directly(rbac_service, admin.user.id)

    with pytest.raises(RbacError) as exc_info:
        rbac_service.revoke_role(
            actor_user_id=admin.user.id,
            target_user_id=admin.user.id,
            role_name="admin",
        )

    assert exc_info.value.code == "RBAC_LAST_ADMIN"


def _grant_admin_directly(rbac_service: RbacService, user_id) -> None:
    _grant_role_directly(rbac_service, user_id, "admin")


def _grant_role_directly(rbac_service: RbacService, user_id, role_name: str) -> None:
    rbac_service.bootstrap_system_roles()
    with rbac_service.uow:
        session = rbac_service.uow.session
        assert session is not None
        role = session.execute(select(Role).where(Role.name == role_name)).scalar_one()
        if session.get(UserRole, (user_id, role.id)) is None:
            session.add(UserRole(user_id=user_id, role_id=role.id, granted_by=user_id))
        rbac_service.uow.commit()
