from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from zayd_common.auth import AuthService
from zayd_common.database.models import Base
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.prompt_registry import PromptRegistryService, bootstrap_registry_defaults
from zayd_service_api import create_app
from zayd_service_orchestrator.answer_orchestration import (
    AnswerOrchestrator,
    StaticAnswerRetriever,
    TemplateAnswerGenerator,
)
from zayd_service_orchestrator.chat_streaming import ChatStreamingService
from zayd_service_orchestrator.question_classification import QuestionClassifier
from zayd_service_orchestrator.risk_policy_engine import RiskPolicyEngine
from zayd_service_retrieval.evidence_sufficiency import (
    EvidenceCandidate,
    EvidenceSufficiencyService,
)


def test_streaming_chat_routes_are_registered(monkeypatch) -> None:
    monkeypatch.setattr("zayd_service_api.app.get_sessionmaker", lambda database_url: object())
    app = create_app()
    route_paths = {route.path for route in app.routes}
    assert "/chat/stream" in route_paths
    assert "/chat/streams/{stream_id}" in route_paths


def test_authenticated_user_receives_sse_stream(monkeypatch) -> None:
    app, _session_factory, _auth_service, token = _app_with_streaming(
        monkeypatch,
        db_name="zayd_streaming_chat_api_auth",
    )
    response = _request(
        app,
        "POST",
        "/chat/stream",
        json_body={"question": "ละหมาดคืออะไร"},
        headers={"authorization": f"Bearer {token}"},
    )

    assert response["status"] == 200
    assert _header_value(response["headers"], b"content-type").startswith(b"text/event-stream")
    assert b"event: status" in response["body"]
    assert b"event: complete" in response["body"]
    assert b"chain_of_thought" not in response["body"]


def test_unauthenticated_chat_stream_is_rejected(monkeypatch) -> None:
    app, _session_factory, _auth_service, _token = _app_with_streaming(
        monkeypatch,
        db_name="zayd_streaming_chat_api_unauth",
    )
    response = _request(
        app,
        "POST",
        "/chat/stream",
        json_body={"question": "ละหมาดคืออะไร"},
    )

    assert response["status"] == 401
    assert response["json"]["error"]["code"] == "CHAT_AUTH_REQUIRED"


def test_guest_quota_blocks_streaming_when_exhausted(monkeypatch) -> None:
    engine = create_engine(
        "sqlite:///file:zayd_streaming_guest_api?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://zayd_dev:zayd_dev@postgres:5432/zayd_dev")
    monkeypatch.setenv("AUTH_JWT_SECRET", "test-secret")
    monkeypatch.setenv("ENABLE_GUEST_MODE", "true")
    monkeypatch.setenv("GUEST_MESSAGE_QUOTA", "0")
    monkeypatch.setattr(
        "zayd_service_api.app.get_sessionmaker",
        lambda database_url: session_factory,
    )
    _patch_chat_service(monkeypatch, session_factory)
    app = create_app()

    guest_response = _request(app, "POST", "/auth/guest/start")
    guest_token = guest_response["json"]["guest_token"]
    response = _request(
        app,
        "POST",
        "/chat/stream",
        json_body={"question": "ละหมาดคืออะไร", "guest_token": guest_token},
    )

    assert response["status"] == 429
    assert response["json"]["error"]["code"] == "GUEST_QUOTA_EXCEEDED"


def _app_with_streaming(
    monkeypatch,
    *,
    db_name: str = "zayd_streaming_chat_api",
) -> tuple[FastAPI, sessionmaker[Session], AuthService, str]:
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
    _patch_chat_service(monkeypatch, session_factory)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    user = auth_service.register(
        email="chat-user@example.com",
        password="very-strong-password",
        display_name="Chat User",
    )
    return create_app(), session_factory, auth_service, user.tokens.access_token


def _patch_chat_service(monkeypatch, session_factory: sessionmaker[Session]) -> None:
    registry = PromptRegistryService(SQLAlchemyUnitOfWork(session_factory))
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    actor = auth_service.register(
        email="chat-bootstrap@example.com",
        password="very-strong-password",
        display_name="Bootstrap",
    )
    bootstrap_registry_defaults(registry, actor_user_id=actor.user.id)
    prompt, policy_version_id, model_configuration_id = registry.resolve_answer_dependencies(
        prompt_name="answer-generation",
        policy_name="answer-safety",
    )
    source_id = uuid4()

    def candidate(rank: int) -> EvidenceCandidate:
        return EvidenceCandidate(
            chunk_id=uuid4(),
            document_version_id=uuid4(),
            source_id=source_id,
            canonical_reference=f"ref:{rank}",
            madhhab="shafii",
            source_type="fiqh",
            license_status="persistent_redistributable",
            score_final=0.9,
            score_reranker=0.9,
            score_reliability=1.0,
            rank=rank,
            metadata={},
        )

    orchestrator = AnswerOrchestrator(
        classifier=QuestionClassifier(),
        risk_policy_engine=RiskPolicyEngine(),
        retriever=StaticAnswerRetriever(candidates=(candidate(1), candidate(2))),
        evidence_service=EvidenceSufficiencyService(),
        generator=TemplateAnswerGenerator(),
        prompt_version=prompt.version,
        prompt_version_id=prompt.id,
        policy_version_id=policy_version_id,
        model_configuration_id=model_configuration_id,
    )

    def patched_builder(
        *,
        session_factory,
        prompt_registry_service: PromptRegistryService,
    ) -> ChatStreamingService:
        _ = prompt_registry_service
        return ChatStreamingService(
            uow_factory=lambda: SQLAlchemyUnitOfWork(session_factory),
            orchestrator=orchestrator,
            prompt_registry_factory=lambda: PromptRegistryService(
                SQLAlchemyUnitOfWork(session_factory)
            ),
        )

    monkeypatch.setattr("zayd_service_api.app.build_chat_streaming_service", patched_builder)


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
        response_finished = asyncio.Event()

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
            await response_finished.wait()
            return {"type": "http.disconnect"}

        async def send(message: dict[str, Any]) -> None:
            nonlocal response_status, response_headers
            if message["type"] == "http.response.start":
                response_status = int(message["status"])
                response_headers = list(message.get("headers", []))
            elif message["type"] == "http.response.body":
                response_body.extend(message.get("body", b""))
                if not message.get("more_body", False):
                    response_finished.set()

        await app(scope, receive, send)
        raw_body = bytes(response_body)
        return {
            "status": response_status,
            "headers": response_headers,
            "body": raw_body,
            "json": json.loads(raw_body) if raw_body.startswith(b"{") else None,
        }

    return asyncio.run(run())


def _header_value(headers: list[tuple[bytes, bytes]], name: bytes) -> bytes:
    for key, value in headers:
        if key == name:
            return value
    return b""