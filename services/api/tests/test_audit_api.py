import asyncio
import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from fastapi import FastAPI
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from zayd_common.audit import AuditService
from zayd_common.auth import AuthService
from zayd_common.database.models import Base, Role, UserRole
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.mfa import MfaService, generate_totp
from zayd_service_api import create_app


def test_auditor_can_list_audit_logs(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    audit_service = AuditService(SQLAlchemyUnitOfWork(session_factory))
    auditor = auth_service.register(
        email="auditor@example.com",
        password="very-strong-password",
        display_name="Auditor",
    )
    _grant_role_directly(session_factory, auditor.user.id, "auditor")
    audit_service.record(
        actor_user_id=auditor.user.id,
        action="providers.disable",
        resource_type="provider",
        outcome="success",
        request_id="req-list-audit",
        trace_id="trace-list-audit",
    )

    response = _request(
        app,
        "GET",
        "/admin/audit-logs?request_id=req-list-audit",
        headers={"authorization": f"Bearer {auditor.tokens.access_token}"},
    )

    assert response["status"] == 200
    assert response["json"]["records"][0]["request_id"] == "req-list-audit"
    assert response["json"]["records"][0]["content_hash"]


def test_user_cannot_list_audit_logs(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    user = auth_service.register(
        email="user@example.com",
        password="very-strong-password",
        display_name="User",
    )

    response = _request(
        app,
        "GET",
        "/admin/audit-logs",
        headers={"authorization": f"Bearer {user.tokens.access_token}"},
    )

    assert response["status"] == 403
    assert response["json"]["error"]["code"] == "RBAC_FORBIDDEN"


def test_auditor_can_export_audit_logs_but_cannot_mutate(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    audit_service = AuditService(SQLAlchemyUnitOfWork(session_factory))
    auditor = auth_service.register(
        email="auditor-export@example.com",
        password="very-strong-password",
        display_name="Auditor Export",
    )
    target = auth_service.register(
        email="target@example.com",
        password="very-strong-password",
        display_name="Target",
    )
    _grant_role_directly(session_factory, auditor.user.id, "auditor")
    audit_service.record(action="models.update", resource_type="model", outcome="success")

    export_response = _request(
        app,
        "GET",
        "/admin/audit-logs/export?resource_type=model",
        headers={"authorization": f"Bearer {auditor.tokens.access_token}"},
    )
    grant_response = _request(
        app,
        "POST",
        "/admin/users/roles/grant",
        json_body={"user_id": str(target.user.id), "role_name": "reviewer"},
        headers={"authorization": f"Bearer {auditor.tokens.access_token}"},
    )

    assert export_response["status"] == 200
    assert b"content_hash" in export_response["body"]
    assert grant_response["status"] == 403


def test_admin_with_mfa_can_export_audit_logs(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    audit_service = AuditService(SQLAlchemyUnitOfWork(session_factory))
    admin = auth_service.register(
        email="admin@example.com",
        password="very-strong-password",
        display_name="Admin",
    )
    _grant_role_directly(session_factory, admin.user.id, "admin")
    _enroll_mfa(session_factory, admin.user.id)
    audit_service.record(action="policies.update", resource_type="policy", outcome="success")

    response = _request(
        app,
        "GET",
        "/admin/audit-logs/export?resource_type=policy",
        headers={"authorization": f"Bearer {admin.tokens.access_token}"},
    )

    assert response["status"] == 200
    assert b"policies.update" in response["body"]


def _app(monkeypatch) -> tuple[FastAPI, sessionmaker[Session]]:
    engine = create_engine(
        "sqlite:///file:zayd_audit_api_tests?mode=memory&cache=shared&uri=true",
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
        raw_path, _, raw_query = path.partition("?")

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": raw_path,
            "raw_path": raw_path.encode("ascii"),
            "query_string": raw_query.encode("ascii"),
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
            "json": json.loads(raw_body) if raw_body.startswith(b"{") else None,
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
