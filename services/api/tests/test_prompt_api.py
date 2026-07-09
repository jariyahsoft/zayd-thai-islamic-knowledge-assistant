from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import UUID

from fastapi import FastAPI
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from zayd_common.auth import AuthService
from zayd_common.database.models import Base, Role, UserRole
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.mfa import MfaService, generate_totp
from zayd_common.rbac import RbacService
from zayd_service_api import create_app


def test_admin_can_create_approve_and_compare_prompts(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch, db_name="zayd_prompt_api_tests_a")
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    admin = auth_service.register(
        email="prompt-admin@example.com",
        password="very-strong-password",
        display_name="Prompt Admin",
    )
    _grant_role_directly(session_factory, admin.user.id, "admin")
    _enroll_mfa(session_factory, admin.user.id)
    headers = {"authorization": f"Bearer {admin.tokens.access_token}"}

    create_response = _request(
        app,
        "POST",
        "/admin/prompts",
        json_body={
            "name": "answer-generation",
            "version": "v1",
            "prompt_body": "Create a concise Thai Islamic knowledge answer.",
            "purpose": "Answer generation",
            "owner": "orchestrator",
            "input_schema": {"question": "string"},
            "output_schema": {"answer_th": "string"},
            "changelog": ["Initial draft"],
            "test_cases": [
                {
                    "name": "basic",
                    "input_payload": {"question": "test"},
                    "expected_assertions": ["returns Thai answer"],
                }
            ],
            "status": "approved",
        },
        headers=headers,
    )
    approve_response = _request(
        app,
        "POST",
        f"/admin/prompts/{create_response['json']['id']}/approve",
        headers=headers,
    )
    compare_response = _request(
        app,
        "GET",
        "/admin/prompts/compare?prompt_name=answer-generation&from_version=v1&to_version=v1",
        headers=headers,
    )

    assert create_response["status"] == 201
    assert create_response["json"]["status"] == "draft"
    assert approve_response["status"] == 200
    assert approve_response["json"]["prompt"]["status"] == "approved"
    assert compare_response["status"] == 200
    assert compare_response["json"]["body_changed"] is False


def test_user_without_prompt_permission_cannot_approve_prompt(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch, db_name="zayd_prompt_api_tests_b")
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    admin = auth_service.register(
        email="prompt-admin-2@example.com",
        password="very-strong-password",
        display_name="Prompt Admin 2",
    )
    user = auth_service.register(
        email="prompt-user@example.com",
        password="very-strong-password",
        display_name="Prompt User",
    )
    _grant_role_directly(session_factory, admin.user.id, "admin")
    _enroll_mfa(session_factory, admin.user.id)
    create_response = _request(
        app,
        "POST",
        "/admin/prompts",
        json_body={
            "name": "answer-generation",
            "version": "v2",
            "prompt_body": "Draft prompt body",
            "purpose": "Answer generation",
            "owner": "orchestrator",
            "input_schema": {"question": "string"},
            "output_schema": {"answer_th": "string"},
        },
        headers={"authorization": f"Bearer {admin.tokens.access_token}"},
    )
    prompt_id = create_response["json"]["id"]

    approve_response = _request(
        app,
        "POST",
        f"/admin/prompts/{prompt_id}/approve",
        headers={"authorization": f"Bearer {user.tokens.access_token}"},
    )

    assert approve_response["status"] == 403
    assert approve_response["json"]["error"]["code"] == "RBAC_FORBIDDEN"


def test_admin_can_rollback_prompt_version(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch, db_name="zayd_prompt_api_tests_c")
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    admin = auth_service.register(
        email="prompt-admin-3@example.com",
        password="very-strong-password",
        display_name="Prompt Admin 3",
    )
    _grant_role_directly(session_factory, admin.user.id, "admin")
    _enroll_mfa(session_factory, admin.user.id)
    headers = {"authorization": f"Bearer {admin.tokens.access_token}"}

    v1 = _request(
        app,
        "POST",
        "/admin/prompts",
        json_body={
            "name": "answer-generation",
            "version": "v1",
            "prompt_body": "Prompt v1",
            "purpose": "Answer generation",
            "owner": "orchestrator",
            "input_schema": {"question": "string"},
            "output_schema": {"answer_th": "string"},
        },
        headers=headers,
    )
    v2 = _request(
        app,
        "POST",
        "/admin/prompts",
        json_body={
            "name": "answer-generation",
            "version": "v2",
            "prompt_body": "Prompt v2",
            "purpose": "Answer generation",
            "owner": "orchestrator",
            "input_schema": {"question": "string"},
            "output_schema": {"answer_th": "string"},
        },
        headers=headers,
    )
    _request(app, "POST", f"/admin/prompts/{v1['json']['id']}/approve", headers=headers)
    _request(app, "POST", f"/admin/prompts/{v2['json']['id']}/approve", headers=headers)

    rollback_response = _request(
        app,
        "POST",
        "/admin/prompts/rollback",
        json_body={"prompt_name": "answer-generation", "target_version": "v1"},
        headers=headers,
    )

    assert rollback_response["status"] == 200
    assert rollback_response["json"]["active_prompt"]["version"] == "v1"


def _app(monkeypatch, *, db_name: str = "zayd_prompt_api_tests") -> tuple[FastAPI, sessionmaker[Session]]:
    engine = create_engine(
        f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
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


def _grant_role_directly(session_factory: sessionmaker[Session], user_id: UUID, role_name: str) -> None:
    rbac_service = RbacService(SQLAlchemyUnitOfWork(session_factory))
    rbac_service.bootstrap_system_roles()
    with _session_scope(session_factory) as session:
        role = session.execute(select(Role).where(Role.name == role_name)).scalar_one()
        if session.get(UserRole, (user_id, role.id)) is None:
            session.add(UserRole(user_id=user_id, role_id=role.id, granted_by=user_id))


def _enroll_mfa(session_factory: sessionmaker[Session], user_id: UUID) -> None:
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