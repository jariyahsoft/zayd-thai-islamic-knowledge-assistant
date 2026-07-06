import asyncio
import base64
import json
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from zayd_common.auth import AuthService
from zayd_common.database.models import Base, Role, UserRole
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.mfa import generate_totp
from zayd_common.rbac import RbacService
from zayd_service_api import create_app


def test_mfa_enroll_confirm_and_privileged_access(monkeypatch) -> None:
    app, session_factory = _shared_app_and_factory(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    user = auth_service.register(
        email="user@example.com",
        password="very-strong-password",
        display_name="User",
    )
    _grant_role_directly(session_factory, user.user.id, "admin")

    enroll = _request(
        app,
        "POST",
        "/auth/mfa/enroll",
        headers={"authorization": f"Bearer {user.tokens.access_token}"},
    )
    assert enroll["status"] == 200
    body = enroll["json"]
    secret = base64.b32decode(body["secret"].upper() + "=" * (-len(body["secret"]) % 8))
    assert len(body["recovery_codes"]) == 10
    code = generate_totp(secret, timestamp=int(time.time()))

    confirm = _request(
        app,
        "POST",
        "/auth/mfa/confirm",
        json_body={"code": code},
        headers={"authorization": f"Bearer {user.tokens.access_token}"},
    )
    assert confirm["status"] == 200
    assert confirm["json"] == {"status": "ok"}

    privileged = _request(
        app,
        "POST",
        "/admin/users/roles/grant",
        json_body={"user_id": str(user.user.id), "role_name": "reviewer"},
        headers={"authorization": f"Bearer {user.tokens.access_token}"},
    )
    assert privileged["status"] == 200


def test_privileged_endpoint_blocks_user_without_mfa(monkeypatch) -> None:
    app, session_factory = _shared_app_and_factory(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    user = auth_service.register(
        email="user@example.com",
        password="very-strong-password",
        display_name="User",
    )
    _grant_role_directly(session_factory, user.user.id, "admin")

    response = _request(
        app,
        "POST",
        "/admin/users/roles/grant",
        json_body={"user_id": str(user.user.id), "role_name": "reviewer"},
        headers={"authorization": f"Bearer {user.tokens.access_token}"},
    )

    assert response["status"] == 403
    assert response["json"]["error"]["code"] == "MFA_PRIVILEGED_ACCESS_BLOCKED"


def test_recovery_code_consumption_reports_success(monkeypatch) -> None:
    app, session_factory = _shared_app_and_factory(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    user = auth_service.register(
        email="user@example.com",
        password="very-strong-password",
        display_name="User",
    )
    _grant_role_directly(session_factory, user.user.id, "senior_scholar")

    enroll = _request(
        app,
        "POST",
        "/auth/mfa/enroll",
        headers={"authorization": f"Bearer {user.tokens.access_token}"},
    )
    body = enroll["json"]
    secret = base64.b32decode(body["secret"].upper() + "=" * (-len(body["secret"]) % 8))
    code = generate_totp(secret, timestamp=int(time.time()))
    _request(
        app,
        "POST",
        "/auth/mfa/confirm",
        json_body={"code": code},
        headers={"authorization": f"Bearer {user.tokens.access_token}"},
    )

    challenge = _request(
        app,
        "POST",
        "/auth/mfa/challenge/start",
        headers={"authorization": f"Bearer {user.tokens.access_token}"},
    )
    challenge_id = challenge["json"]["challenge_id"]
    recovery_code = body["recovery_codes"][0]
    consume = _request(
        app,
        "POST",
        "/auth/mfa/challenge/recovery",
        json_body={"challenge_id": challenge_id, "recovery_code": recovery_code},
        headers={"authorization": f"Bearer {user.tokens.access_token}"},
    )
    assert consume["status"] == 200
    assert consume["json"] == {"status": "ok"}


def test_mfa_reset_with_recovery_code_returns_new_codes(monkeypatch) -> None:
    app, session_factory = _shared_app_and_factory(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    user = auth_service.register(
        email="user@example.com",
        password="very-strong-password",
        display_name="User",
    )
    _grant_role_directly(session_factory, user.user.id, "admin")

    enroll = _request(
        app,
        "POST",
        "/auth/mfa/enroll",
        headers={"authorization": f"Bearer {user.tokens.access_token}"},
    )
    body = enroll["json"]
    secret = base64.b32decode(body["secret"].upper() + "=" * (-len(body["secret"]) % 8))
    code = generate_totp(secret, timestamp=int(time.time()))
    _request(
        app,
        "POST",
        "/auth/mfa/confirm",
        json_body={"code": code},
        headers={"authorization": f"Bearer {user.tokens.access_token}"},
    )
    recovery_code = body["recovery_codes"][0]

    reset = _request(
        app,
        "POST",
        "/auth/mfa/reset",
        json_body={"channel": "recovery_code", "proof": recovery_code},
        headers={"authorization": f"Bearer {user.tokens.access_token}"},
    )
    assert reset["status"] == 200
    assert reset["json"]["secret"] != body["secret"]
    assert reset["json"]["recovery_codes"]


def test_mfa_status_reports_enrollment_state(monkeypatch) -> None:
    app, session_factory = _shared_app_and_factory(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    user = auth_service.register(
        email="user@example.com",
        password="very-strong-password",
        display_name="User",
    )

    response = _request(
        app,
        "GET",
        "/auth/mfa/status",
        headers={"authorization": f"Bearer {user.tokens.access_token}"},
    )
    assert response["status"] == 200
    assert response["json"] == {"enrolled": False, "privileged_role_required": False}


def test_mfa_routes_are_registered(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    monkeypatch.setenv("DATABASE_URL", "postgresql://zayd_dev:zayd_dev@postgres:5432/zayd_dev")
    monkeypatch.setenv("AUTH_JWT_SECRET", "test-secret")
    monkeypatch.setattr(
        "zayd_service_api.app.get_sessionmaker",
        lambda database_url: session_factory,
    )
    app = create_app()
    paths = {route.path for route in app.routes}
    assert "/auth/mfa/enroll" in paths
    assert "/auth/mfa/confirm" in paths
    assert "/auth/mfa/challenge/start" in paths
    assert "/auth/mfa/challenge/verify" in paths
    assert "/auth/mfa/challenge/recovery" in paths
    assert "/auth/mfa/reset" in paths
    assert "/auth/mfa/recovery/rotate" in paths
    assert "/auth/mfa/status" in paths


def _shared_app_and_factory(
    monkeypatch,
) -> tuple[FastAPI, sessionmaker[Session]]:
    db_file = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    db_path = Path(db_file.name)
    db_file.close()
    engine = create_engine(
        f"sqlite:///{db_path}",
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
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = int(message["status"])
            elif message["type"] == "http.response.body":
                response_body.extend(message.get("body", b""))

        await app(scope, receive, send)
        raw_body = bytes(response_body)
        return {
            "status": response_status,
            "body": raw_body,
            "json": json.loads(raw_body) if raw_body else None,
        }

    return asyncio.run(run())


def _grant_role_directly(session_factory: sessionmaker[Session], user_id, role_name: str) -> None:
    rbac_service = RbacService(SQLAlchemyUnitOfWork(session_factory))
    rbac_service.bootstrap_system_roles()
    with _session_scope(session_factory) as session:
        assert session is not None
        role = session.execute(select(Role).where(Role.name == role_name)).scalar_one()
        if session.get(UserRole, (user_id, role.id)) is None:
            session.add(UserRole(user_id=user_id, role_id=role.id, granted_by=user_id))
        session.commit()


@contextmanager
def _session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
