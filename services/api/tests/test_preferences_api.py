from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from zayd_common.auth import AuthService
from zayd_common.database.models import Base
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_service_api import create_app


def test_preferences_routes_are_registered(monkeypatch) -> None:
    monkeypatch.setattr("zayd_service_api.app.get_sessionmaker", lambda database_url: object())
    app = create_app()
    route_paths = {route.path for route in app.routes}
    assert "/auth/me/preferences" in route_paths


def test_signed_in_user_can_read_and_update_preferences(monkeypatch) -> None:
    app, token = _app_with_user(monkeypatch, db_name="zayd_preferences_api")
    get_response = _request(app, "GET", "/auth/me/preferences", token=token)
    assert get_response["status"] == 200
    assert get_response["json"]["madhhab"] == "shafii"
    assert get_response["json"]["default_madhhab"] == "shafii"

    patch_response = _request(
        app,
        "PATCH",
        "/auth/me/preferences",
        token=token,
        json_body={"madhhab": "hanafi", "answer_length": "short", "history_mode": "disabled"},
    )
    assert patch_response["status"] == 200
    assert patch_response["json"]["madhhab"] == "hanafi"
    assert patch_response["json"]["answer_length"] == "short"
    assert patch_response["json"]["history_mode"] == "disabled"


def test_invalid_preference_patch_is_rejected(monkeypatch) -> None:
    app, token = _app_with_user(monkeypatch, db_name="zayd_preferences_api_invalid")
    response = _request(
        app,
        "PATCH",
        "/auth/me/preferences",
        token=token,
        json_body={"madhhab": "invalid"},
    )
    assert response["status"] == 422


def _app_with_user(monkeypatch, *, db_name: str) -> tuple[FastAPI, str]:
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
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    user = auth_service.register(
        email="preferences-user@example.test",
        password="very-strong-password",
        display_name="Preferences User",
    )
    return create_app(), user.tokens.access_token


def _request(
    app: FastAPI,
    method: str,
    path: str,
    *,
    token: str | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    async def run() -> dict[str, Any]:
        from httpx import ASGITransport, AsyncClient

        headers = {"authorization": f"Bearer {token}"} if token else {}
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.request(method, path, json=json_body, headers=headers)
            body: Any
            try:
                body = response.json()
            except Exception:
                body = None
            return {
                "status": response.status_code,
                "json": body,
            }

    import asyncio

    return asyncio.run(run())