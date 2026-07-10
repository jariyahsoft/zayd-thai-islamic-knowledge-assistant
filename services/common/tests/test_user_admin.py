from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from zayd_common.auth import AuthService
from zayd_common.database.models import AuditLog, Base, Role, UserRole
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.user_admin import UserAdminError, UserAdminService


@pytest.fixture
def services() -> tuple[AuthService, UserAdminService, sessionmaker]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return (
        AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret"),
        UserAdminService(SQLAlchemyUnitOfWork(session_factory)),
        session_factory,
    )


def test_disable_user_revokes_active_sessions(services) -> None:
    auth_service, user_admin, _session_factory = services
    admin = auth_service.register(
        email="admin@example.com",
        password="very-strong-password",
        display_name="Admin",
    )
    member = auth_service.register(
        email="member@example.com",
        password="very-strong-password",
        display_name="Member",
    )
    auth_service.login(email="member@example.com", password="very-strong-password")
    _grant_role_directly(_session_factory, admin.user.id, "admin")

    updated = user_admin.set_status(
        user_id=member.user.id,
        status="disabled",
        actor_user_id=admin.user.id,
        trace_id="trace-user-disable",
    )

    assert updated.status == "disabled"
    assert updated.active_session_count == 0


def test_last_admin_disable_is_guarded(services) -> None:
    auth_service, user_admin, session_factory = services
    admin = auth_service.register(
        email="last-admin@example.com",
        password="very-strong-password",
        display_name="Last Admin",
    )
    _grant_role_directly(session_factory, admin.user.id, "admin")

    with pytest.raises(UserAdminError) as exc_info:
        user_admin.set_status(
            user_id=admin.user.id,
            status="disabled",
            actor_user_id=admin.user.id,
        )

    assert exc_info.value.code == "USER_ADMIN_LAST_ADMIN"


def test_admin_session_revocation_is_audited(services) -> None:
    auth_service, user_admin, session_factory = services
    admin = auth_service.register(
        email="root@example.com",
        password="very-strong-password",
        display_name="Root",
    )
    member = auth_service.register(
        email="member2@example.com",
        password="very-strong-password",
        display_name="Member Two",
    )
    auth_service.login(email="member2@example.com", password="very-strong-password")
    _grant_role_directly(session_factory, admin.user.id, "admin")

    revoked = user_admin.revoke_sessions(
        user_id=member.user.id,
        actor_user_id=admin.user.id,
        trace_id="trace-session-revoke",
    )

    assert revoked == 2
    with session_factory() as session:
        logs = session.execute(select(AuditLog)).scalars().all()
        assert any(
            log.action == "users.sessions.revoke"
            and log.trace_id == "trace-session-revoke"
            for log in logs
        )


def _grant_role_directly(session_factory: sessionmaker[Session], user_id, role_name: str) -> None:
    from zayd_common.rbac import RbacService

    rbac_service = RbacService(SQLAlchemyUnitOfWork(session_factory))
    rbac_service.bootstrap_system_roles()
    with session_factory() as session:
        role = session.execute(select(Role).where(Role.name == role_name)).scalar_one()
        if session.get(UserRole, (user_id, role.id)) is None:
            session.add(UserRole(user_id=user_id, role_id=role.id, granted_by=user_id))
        session.commit()
