from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from zayd_common.auth import AuthService
from zayd_common.database.models import Answer, Base, Conversation, Message
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_service_api import create_app


def test_feedback_routes_are_registered(monkeypatch) -> None:
    monkeypatch.setattr("zayd_service_api.app.get_sessionmaker", lambda database_url: object())
    app = create_app()
    route_paths = {route.path for route in app.routes}
    assert "/feedback" in route_paths


def test_signed_in_user_can_submit_and_read_feedback(monkeypatch) -> None:
    app, token, answer_id = _app_with_answer(monkeypatch, db_name="zayd_feedback_api")
    submit_response = _request(
        app,
        "POST",
        "/feedback",
        token=token,
        json_body={
            "answer_id": str(answer_id),
            "category": "incorrect_answer",
            "notes": "คำตอบไม่ถูกต้อง",
        },
    )
    assert submit_response["status"] == 201
    feedback_id = submit_response["json"]["id"]
    assert submit_response["json"]["receipt_message"]
    assert "trace_id" not in submit_response["json"]

    get_response = _request(app, "GET", f"/feedback/{feedback_id}", token=token)
    assert get_response["status"] == 200
    assert get_response["json"]["category"] == "incorrect_answer"


def test_feedback_requires_authentication(monkeypatch) -> None:
    monkeypatch.setattr("zayd_service_api.app.get_sessionmaker", lambda database_url: object())
    app = create_app()
    response = _request(
        app,
        "POST",
        "/feedback",
        json_body={"answer_id": str(uuid4()), "category": "other"},
    )
    assert response["status"] == 401


def _app_with_answer(monkeypatch, *, db_name: str) -> tuple[FastAPI, str, Any]:
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
        email="feedback-user@example.test",
        password="very-strong-password",
        display_name="Feedback User",
    )
    conversation_id = uuid4()
    message_id = uuid4()
    answer_id = uuid4()
    with session_factory() as session:
        session.add(
            Conversation(
                id=conversation_id,
                user_id=user.user.id,
                title="ละหมาด",
                language="th",
                madhhab="shafii",
            )
        )
        session.add(
            Message(
                id=message_id,
                conversation_id=conversation_id,
                sender_type="assistant",
                body="คำตอบ",
                body_hash="hash",
                metadata_json={},
            )
        )
        session.add(
            Answer(
                id=answer_id,
                message_id=message_id,
                retrieval_run_id=uuid4(),
                model_configuration_id=uuid4(),
                prompt_version_id=uuid4(),
                policy_version_id=uuid4(),
                risk_level="low",
                madhhab="shafii",
                answer_json={"summary": "สรุป", "answer_th": "คำตอบ"},
                confidence_level="high",
                evidence_sufficient=True,
            )
        )
        session.commit()
    return create_app(), user.tokens.access_token, answer_id


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
            return {"status": response.status_code, "json": body}

    import asyncio

    return asyncio.run(run())