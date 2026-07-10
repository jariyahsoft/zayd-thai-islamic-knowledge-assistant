import asyncio
import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from zayd_common.auth import AuthService
from zayd_common.database.models import AuditLog, Base, Role, UserRole
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.mfa import MfaService, generate_totp
from zayd_service_api import create_app


def test_auth_me_returns_roles_and_permissions(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    auth_result = auth_service.register(
        email="user@example.com",
        password="very-strong-password",
        display_name="User",
    )

    response = _request(
        app,
        "GET",
        "/auth/me",
        headers={"authorization": f"Bearer {auth_result.tokens.access_token}"},
    )

    assert response["status"] == 200
    assert response["json"]["roles"] == ["user"]
    assert "users.read_self" in response["json"]["permissions"]
    assert "users.roles.manage" not in response["json"]["permissions"]


def test_admin_role_grant_endpoint_requires_permission(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
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

    response = _request(
        app,
        "POST",
        "/admin/users/roles/grant",
        json_body={"user_id": str(target.user.id), "role_name": "reviewer"},
        headers={"authorization": f"Bearer {actor.tokens.access_token}"},
    )

    assert response["status"] == 403
    assert response["json"]["error"]["code"] == "RBAC_FORBIDDEN"


def test_admin_can_grant_reviewer_role_through_endpoint(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
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
    _grant_role_directly(session_factory, admin.user.id, "admin")
    _enroll_mfa(session_factory, admin.user.id)

    response = _request(
        app,
        "POST",
        "/admin/users/roles/grant",
        json_body={"user_id": str(reviewer.user.id), "role_name": "reviewer"},
        headers={
            "authorization": f"Bearer {admin.tokens.access_token}",
            "x-request-id": "trace-api-grant",
        },
    )

    assert response["status"] == 200
    assert response["json"] == {"status": "ok", "changed": True}
    with session_factory() as session:
        logs = session.execute(select(AuditLog)).scalars().all()
        assert any(
            log.action == "rbac.role.grant" and log.trace_id == "trace-api-grant" for log in logs
        )


def test_document_approval_endpoint_enforces_separation_of_duties(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    scholar = auth_service.register(
        email="scholar@example.com",
        password="very-strong-password",
        display_name="Scholar",
    )
    _grant_role_directly(session_factory, scholar.user.id, "senior_scholar")

    response = _request(
        app,
        "POST",
        "/authorization/documents/approve",
        json_body={"document_created_by": str(scholar.user.id)},
        headers={"authorization": f"Bearer {scholar.tokens.access_token}"},
    )

    assert response["status"] == 403
    assert response["json"]["error"]["code"] == "RBAC_SEPARATION_OF_DUTIES"


def test_admin_can_manage_provider_and_model_routes(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    admin = auth_service.register(
        email="provider-admin@example.com",
        password="very-strong-password",
        display_name="Provider Admin",
    )
    _grant_role_directly(session_factory, admin.user.id, "admin")
    _enroll_mfa(session_factory, admin.user.id)

    provider_response = _request(
        app,
        "POST",
        "/admin/providers",
        json_body={
            "name": "OpenAI Compatible",
            "provider_type": "llm",
            "status": "enabled",
            "base_url": "https://api.example.com",
            "secret_ref": "vault://providers/openai",
            "terms_url": "https://example.com/terms",
            "data_policy_json": {"classification": "restricted"},
        },
        headers={"authorization": f"Bearer {admin.tokens.access_token}"},
    )

    assert provider_response["status"] == 201
    provider_id = provider_response["json"]["id"]
    assert provider_response["json"]["secret_mask"] == "configured"

    model_response = _request(
        app,
        "POST",
        "/admin/models",
        json_body={
            "provider_id": provider_id,
            "model_name": "gpt-4o-mini",
            "model_type": "llm",
            "configuration": {"temperature": 0},
            "allow_listed": True,
            "fallback_model_id": None,
            "cost_limit_daily_usd": 2.5,
            "is_default": True,
            "status": "enabled",
        },
        headers={"authorization": f"Bearer {admin.tokens.access_token}"},
    )

    assert model_response["status"] == 201
    assert model_response["json"]["is_default"] is True

    connection_response = _request(
        app,
        "POST",
        f"/admin/providers/{provider_id}/test-connection",
        json_body={},
        headers={
            "authorization": f"Bearer {admin.tokens.access_token}",
            "x-request-id": "trace-provider-test",
        },
    )

    assert connection_response["status"] == 200
    assert connection_response["json"]["status"] in {"ok", "degraded"}
    with session_factory() as session:
        logs = session.execute(select(AuditLog)).scalars().all()
        assert any(
            log.action == "providers.connection_test"
            and log.trace_id == "trace-provider-test"
            for log in logs
        )


def test_admin_user_status_disable_revokes_sessions_and_last_admin_is_guarded(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    admin = auth_service.register(
        email="root@example.com",
        password="very-strong-password",
        display_name="Root",
    )
    member = auth_service.register(
        email="member@example.com",
        password="very-strong-password",
        display_name="Member",
    )
    auth_service.login(email="member@example.com", password="very-strong-password")
    _grant_role_directly(session_factory, admin.user.id, "admin")
    _enroll_mfa(session_factory, admin.user.id)

    guarded = _request(
        app,
        "PATCH",
        f"/admin/users/{admin.user.id}/status",
        json_body={"status": "disabled"},
        headers={"authorization": f"Bearer {admin.tokens.access_token}"},
    )

    assert guarded["status"] == 409
    assert guarded["json"]["error"]["code"] == "USER_ADMIN_LAST_ADMIN"

    disabled = _request(
        app,
        "PATCH",
        f"/admin/users/{member.user.id}/status",
        json_body={"status": "disabled"},
        headers={
            "authorization": f"Bearer {admin.tokens.access_token}",
            "x-request-id": "trace-user-disable",
        },
    )

    assert disabled["status"] == 200
    assert disabled["json"]["user"]["status"] == "disabled"
    assert disabled["json"]["user"]["active_session_count"] == 0

    sessions = _request(
        app,
        "POST",
        f"/admin/users/{member.user.id}/sessions/revoke",
        json_body={},
        headers={"authorization": f"Bearer {admin.tokens.access_token}"},
    )

    assert sessions["status"] == 200
    assert sessions["json"]["revoked_sessions"] == 0
    with session_factory() as session:
        logs = session.execute(select(AuditLog)).scalars().all()
        assert any(
            log.action == "users.status.update"
            and log.trace_id == "trace-user-disable"
            for log in logs
        )


def _app(monkeypatch) -> tuple[FastAPI, sessionmaker[Session]]:
    engine = create_engine(
        f"sqlite:///file:zayd_rbac_api_tests_{uuid4()}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://zayd_dev:zayd_dev@postgres:5432/zayd_dev")
    monkeypatch.setenv("AUTH_JWT_SECRET", "test-secret")
    monkeypatch.setattr(
        "zayd_service_api.app.get_sessionmaker",
        lambda database_url: session_factory,
    )
    return create_app(), session_factory


def _request(
    app: FastAPI,
    method: str,
    path: str,
    *,
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    async def run() -> dict[str, Any]:
        body = json.dumps(json_body).encode("utf-8") if json_body is not None else b""
        response_status = 500
        response_headers: list[tuple[bytes, bytes]] = []
        response_body = bytearray()
        sent_request = False

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "headers": [
                (key.lower().encode("latin-1"), value.encode("latin-1"))
                for key, value in (headers or {}).items()
            ]
            + ([(b"content-type", b"application/json")] if json_body is not None else []),
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
        }

        async def receive() -> dict[str, Any]:
            nonlocal sent_request
            if not sent_request:
                sent_request = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.disconnect"}

        async def send(message: dict[str, Any]) -> None:
            nonlocal response_status, response_headers
            if message["type"] == "http.response.start":
                response_status = int(message["status"])
                response_headers = list(message.get("headers", []))
            elif message["type"] == "http.response.body":
                response_body.extend(message.get("body", b""))

        await app(scope, receive, send)
        raw_body = bytes(response_body)
        return {
            "status": response_status,
            "headers": response_headers,
            "body": raw_body,
            "json": json.loads(raw_body) if raw_body else None,
        }

    return asyncio.run(run())


def _grant_role_directly(session_factory: sessionmaker[Session], user_id, role_name: str) -> None:
    from zayd_common.rbac import RbacService

    rbac_service = RbacService(SQLAlchemyUnitOfWork(session_factory))
    rbac_service.bootstrap_system_roles()
    with _session_scope(session_factory) as session:
        role = session.execute(select(Role).where(Role.name == role_name)).scalar_one()
        if session.get(UserRole, (user_id, role.id)) is None:
            session.add(UserRole(user_id=user_id, role_id=role.id, granted_by=user_id))


def _enroll_mfa(session_factory: sessionmaker[Session], user_id) -> None:
    mfa_service = MfaService(SQLAlchemyUnitOfWork(session_factory))
    enrollment = mfa_service.start_enrollment(user_id=user_id)
    code = generate_totp(enrollment.secret, timestamp=int(time.time()))
    mfa_service.confirm_enrollment(user_id=user_id, code=code)


@contextmanager
def _session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    finally:
        session.close()
