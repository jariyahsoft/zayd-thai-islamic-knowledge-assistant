from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from zayd_common.auth import AuthService
from zayd_common.database.models import Base, Conversation, Message
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_service_api import create_app


def test_conversation_history_routes_are_registered(monkeypatch) -> None:
    monkeypatch.setattr("zayd_service_api.app.get_sessionmaker", lambda database_url: object())
    app = create_app()
    route_paths = {route.path for route in app.routes}
    assert "/chat/conversations" in route_paths
    assert "/chat/conversations/delete-all" in route_paths


def test_signed_in_user_can_list_open_and_delete_conversations(monkeypatch) -> None:
    app, token, conversation_id = _app_with_conversation(monkeypatch, db_name="zayd_history_api")

    list_response = _request(app, "GET", "/chat/conversations", token=token)
    assert list_response["status"] == 200
    assert list_response["json"]["total_count"] == 1
    assert list_response["json"]["conversations"][0]["id"] == str(conversation_id)

    detail_response = _request(
        app,
        "GET",
        f"/chat/conversations/{conversation_id}",
        token=token,
    )
    assert detail_response["status"] == 200
    assert len(detail_response["json"]["messages"]) == 2
    assert detail_response["json"]["messages"][0]["sender_type"] == "user"

    delete_response = _request(
        app,
        "DELETE",
        f"/chat/conversations/{conversation_id}",
        token=token,
    )
    assert delete_response["status"] == 200
    assert delete_response["json"]["status"] == "ok"

    missing_response = _request(
        app,
        "GET",
        f"/chat/conversations/{conversation_id}",
        token=token,
    )
    assert missing_response["status"] == 404


def test_conversation_history_requires_authentication(monkeypatch) -> None:
    monkeypatch.setattr("zayd_service_api.app.get_sessionmaker", lambda database_url: object())
    app = create_app()
    response = _request(app, "GET", "/chat/conversations")
    assert response["status"] == 401


def _app_with_conversation(monkeypatch, *, db_name: str) -> tuple[FastAPI, str, Any]:
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
        email="history-user@example.test",
        password="very-strong-password",
        display_name="History User",
    )
    conversation_id = uuid4()
    with session_factory() as session:
        session.add(
            Conversation(
                id=conversation_id,
                user_id=user.user.id,
                title="ละหมาดคืออะไร",
                language="th",
                madhhab="shafii",
            )
        )
        session.add(
            Message(
                conversation_id=conversation_id,
                sender_type="user",
                body="ละหมาดคืออะไร",
                body_hash="hash-user",
                metadata_json={},
            )
        )
        session.add(
            Message(
                conversation_id=conversation_id,
                sender_type="assistant",
                body="ละหมาดคือการเคารพอัลลอฮ",
                body_hash="hash-assistant",
                metadata_json={"status": "completed"},
            )
        )
        session.commit()
    return create_app(), user.tokens.access_token, conversation_id


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