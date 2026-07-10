from __future__ import annotations

import asyncio
from hashlib import sha256
from typing import Any

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.database.models import AuditLog, Base
from zayd_service_api import create_app


def _app(monkeypatch) -> tuple[FastAPI, Any]:
    engine = create_engine(
        "sqlite:///file:zayd_pilot_access?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    invited_email = "invited@example.test"
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AUTH_JWT_SECRET", "test-pilot-jwt-secret")
    monkeypatch.setenv("AUTH_SESSION_SECRET", "test-pilot-session-secret")
    monkeypatch.setenv("PILOT_MODE", "true")
    monkeypatch.setenv("ENABLE_GUEST_MODE", "false")
    monkeypatch.setenv("PILOT_INVITE_EMAIL_HASHES", sha256(invited_email.encode()).hexdigest())
    monkeypatch.setenv("PILOT_INVITE_ALLOWLIST_VERSION", "pilot-invites-v1")
    monkeypatch.setattr("zayd_service_api.app.get_sessionmaker", lambda _url: factory)
    return create_app(), factory


def _register(app: FastAPI, email: str) -> dict[str, Any]:
    async def request() -> dict[str, Any]:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            response = await client.post(
                "/auth/register",
                json={
                    "email": email,
                    "password": "very-strong-pilot-password",
                    "display_name": "Pilot User",
                },
            )
            return {"status": response.status_code, "json": response.json()}

    return asyncio.run(request())


def test_pilot_registration_is_invite_only_and_auditable(monkeypatch) -> None:
    app, factory = _app(monkeypatch)
    denied = _register(app, "not-invited@example.test")
    assert denied == {
        "status": 403,
        "json": {
            "error": {
                "code": "PILOT_INVITE_REQUIRED",
                "message": "Registration is available by invitation only.",
            }
        },
    }
    invited = _register(app, "invited@example.test")
    assert invited["status"] == 201
    with factory() as session:
        audit_rows = list(
            session.scalars(
                select(AuditLog)
                .where(AuditLog.action == "pilot.invite.consume")
                .order_by(AuditLog.created_at)
            )
        )
        assert [row.outcome for row in audit_rows] == ["denied", "success"]
        assert all("email" not in str(row.after_summary).lower() for row in audit_rows)
        assert audit_rows[1].actor_user_id is not None
