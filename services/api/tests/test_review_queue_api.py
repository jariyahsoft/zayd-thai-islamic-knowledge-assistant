"""Integration tests for the review queue API.

Covers route registration, queue listing, detail, claim, release,
assign, and escalate endpoints with authentication and RBAC.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from zayd_common.auth import AuthService
from zayd_common.database.models import (
    Answer,
    AuditLog,
    Base,
    Conversation,
    Document,
    DocumentVersion,
    Feedback,
    Message,
    ReviewTask,
    Role,
    User,
    UserRole,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.mfa import MfaService, generate_totp
from zayd_common.storage import SignedUrl
from zayd_service_api import create_app


@dataclass
class FakeStorage:
    uploaded: dict[str, bytes]

    def put_private_bytes(
        self,
        *,
        key: str,
        content: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> object:
        self.uploaded[key] = content
        return object()

    def get_private_bytes(self, *, key: str) -> bytes:
        return self.uploaded[key]

    def delete_object(self, *, key: str) -> None:
        self.uploaded.pop(key, None)

    def create_signed_get_url(
        self,
        *,
        key: str,
        filename: str,
        content_type: str,
        expires_in_seconds: int = 300,
    ) -> SignedUrl:
        return SignedUrl(
            method="GET",
            url=f"https://example.local/{key}",
            expires_at=1_700_000_000,
            expires_in_seconds=expires_in_seconds,
        )


def test_review_queue_routes_are_registered(monkeypatch) -> None:
    monkeypatch.setattr("zayd_service_api.app.get_sessionmaker", lambda database_url: object())
    monkeypatch.setattr(
        "zayd_service_api.app.S3ObjectStorage",
        lambda settings: FakeStorage(uploaded={}),
    )
    app = create_app()

    route_paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert "/reviews/queue" in route_paths
    assert "/reviews/{review_task_id}" in route_paths
    assert "/reviews/{review_task_id}/claim" in route_paths
    assert "/reviews/{review_task_id}/release" in route_paths
    assert "/reviews/{review_task_id}/assign" in route_paths
    assert "/reviews/{review_task_id}/escalate" in route_paths


def test_review_queue_openapi_contract(monkeypatch) -> None:
    monkeypatch.setattr("zayd_service_api.app.get_sessionmaker", lambda database_url: object())
    monkeypatch.setattr(
        "zayd_service_api.app.S3ObjectStorage",
        lambda settings: FakeStorage(uploaded={}),
    )
    schema = create_app().openapi()

    paths = schema["paths"]
    assert paths["/reviews/queue"]["get"]["responses"]["200"]
    assert paths["/reviews/{review_task_id}"]["get"]["responses"]["200"]
    assert paths["/reviews/{review_task_id}/claim"]["post"]["responses"]["200"]
    assert paths["/reviews/{review_task_id}/release"]["post"]["responses"]["200"]
    assert paths["/reviews/{review_task_id}/assign"]["post"]["responses"]["200"]
    assert paths["/reviews/{review_task_id}/escalate"]["post"]["responses"]["200"]
    assert schema["components"]["schemas"]["ReviewQueueListResponse"]
    assert schema["components"]["schemas"]["ReviewTaskDetailResponse"]
    assert schema["components"]["schemas"]["ReviewTaskActionResponse"]
    assert schema["components"]["schemas"]["ReviewTaskAssignRequest"]


def test_list_queue_requires_review_permission(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    actor = auth_service.register(
        email="user@example.com",
        password="very-strong-password",
        display_name="User",
    )

    response = _request(
        app,
        "GET",
        "/reviews/queue",
        headers={"authorization": f"Bearer {actor.tokens.access_token}"},
    )

    assert response["status"] == 403
    assert response["json"]["error"]["code"] == "RBAC_FORBIDDEN"


def test_list_queue_success(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    actor = auth_service.register(
        email="reviewer@example.com",
        password="very-strong-password",
        display_name="Reviewer",
    )
    _grant_role_directly(session_factory, actor.user.id, "reviewer")
    _enroll_mfa(session_factory, actor.user.id)
    _set_user_preferences(session_factory, actor.user.id, language="th", madhhab="shafii")

    _seed_queue_task(session_factory, title="Task A", language="th", madhhab="shafii")
    _seed_queue_task(session_factory, title="Task B", language="th", madhhab="unknown")

    response = _request(
        app,
        "GET",
        "/reviews/queue",
        headers={"authorization": f"Bearer {actor.tokens.access_token}"},
    )

    assert response["status"] == 200
    assert len(response["json"]["tasks"]) >= 2
    assert response["json"]["total_count"] >= 2


def test_list_queue_filters_by_language(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    actor = auth_service.register(
        email="admin-review@example.com",
        password="very-strong-password",
        display_name="Admin",
    )
    _grant_role_directly(session_factory, actor.user.id, "admin")
    _enroll_mfa(session_factory, actor.user.id)
    _set_user_preferences(session_factory, actor.user.id)

    _seed_queue_task(session_factory, title="Thai", language="th")
    _seed_queue_task(session_factory, title="Arabic", language="ar")

    response = _request(
        app,
        "GET",
        "/reviews/queue?language=ar",
        headers={"authorization": f"Bearer {actor.tokens.access_token}"},
    )
    assert response["status"] == 200
    assert all(t["language"] == "ar" for t in response["json"]["tasks"])


def test_reviewer_dashboard_returns_counts_and_feedback_for_reviewer(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    actor = auth_service.register(
        email="dashboard-reviewer@example.com",
        password="very-strong-password",
        display_name="Reviewer",
    )
    _grant_role_directly(session_factory, actor.user.id, "reviewer")
    _enroll_mfa(session_factory, actor.user.id)
    _set_user_preferences(session_factory, actor.user.id, language="th", madhhab="shafii")

    _seed_queue_task(session_factory, title="คิวเปิด", language="th", madhhab="shafii", status="open")
    _seed_feedback_record(session_factory, user_id=actor.user.id)

    response = _request(
        app,
        "GET",
        "/reviews/dashboard",
        headers={"authorization": f"Bearer {actor.tokens.access_token}"},
    )

    assert response["status"] == 200
    assert response["json"]["summary"]["total_visible_count"] >= 1
    assert response["json"]["summary"]["feedback_open_count"] == 1
    assert len(response["json"]["feedback_items"]) == 1


def test_reviewer_dashboard_hides_feedback_for_translator(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    actor = auth_service.register(
        email="dashboard-translator@example.com",
        password="very-strong-password",
        display_name="Translator",
    )
    _grant_role_directly(session_factory, actor.user.id, "translator")
    _enroll_mfa(session_factory, actor.user.id)
    _set_user_preferences(session_factory, actor.user.id, language="th", madhhab="shafii")

    _seed_queue_task(session_factory, title="คิวแปล", language="th", madhhab="shafii", status="open")
    _seed_feedback_record(session_factory, user_id=actor.user.id)

    response = _request(
        app,
        "GET",
        "/reviews/dashboard",
        headers={"authorization": f"Bearer {actor.tokens.access_token}"},
    )

    assert response["status"] == 200
    assert response["json"]["summary"]["total_visible_count"] >= 1
    assert response["json"]["summary"]["feedback_open_count"] == 0
    assert response["json"]["feedback_items"] == []


def test_claim_task_success(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    actor = auth_service.register(
        email="claim@example.com",
        password="very-strong-password",
        display_name="Claimer",
    )
    _grant_role_directly(session_factory, actor.user.id, "reviewer")
    _enroll_mfa(session_factory, actor.user.id)
    _set_user_preferences(session_factory, actor.user.id)

    task_id = _seed_queue_task(session_factory)

    response = _request(
        app,
        "POST",
        f"/reviews/{task_id}/claim",
        headers={
            "authorization": f"Bearer {actor.tokens.access_token}",
            "x-request-id": "trace-claim",
        },
    )

    assert response["status"] == 200
    assert response["json"]["status"] == "ok"
    assert response["json"]["task"]["status"] == "in_progress"
    assert UUID(response["json"]["task"]["assigned_to"]) == actor.user.id

    # Verify audit
    with session_factory() as session:
        logs = session.execute(
            select(AuditLog).where(AuditLog.action == "review_task.claimed")
        ).scalars().all()
    assert any(log.trace_id == "trace-claim" for log in logs)


def test_release_task_success(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    actor = auth_service.register(
        email="release@example.com",
        password="very-strong-password",
        display_name="Releaser",
    )
    _grant_role_directly(session_factory, actor.user.id, "reviewer")
    _enroll_mfa(session_factory, actor.user.id)
    _set_user_preferences(session_factory, actor.user.id)

    task_id = _seed_queue_task(session_factory)

    _request(
        app,
        "POST",
        f"/reviews/{task_id}/claim",
        headers={"authorization": f"Bearer {actor.tokens.access_token}"},
    )

    response = _request(
        app,
        "POST",
        f"/reviews/{task_id}/release",
        headers={
            "authorization": f"Bearer {actor.tokens.access_token}",
            "x-request-id": "trace-release",
        },
    )

    assert response["status"] == 200
    assert response["json"]["task"]["status"] == "open"
    assert response["json"]["task"]["assigned_to"] is None

    with session_factory() as session:
        logs = session.execute(
            select(AuditLog).where(AuditLog.action == "review_task.released")
        ).scalars().all()
    assert any(log.trace_id == "trace-release" for log in logs)


def test_assign_task_by_admin(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    admin = auth_service.register(
        email="admin-assign@example.com",
        password="very-strong-password",
        display_name="Admin",
    )
    _grant_role_directly(session_factory, admin.user.id, "admin")
    _enroll_mfa(session_factory, admin.user.id)

    reviewer = auth_service.register(
        email="assign-target@example.com",
        password="very-strong-password",
        display_name="Assignee",
    )
    _grant_role_directly(session_factory, reviewer.user.id, "reviewer")

    task_id = _seed_queue_task(session_factory)

    response = _request(
        app,
        "POST",
        f"/reviews/{task_id}/assign",
        json_body={"assignee_user_id": str(reviewer.user.id)},
        headers={
            "authorization": f"Bearer {admin.tokens.access_token}",
            "x-request-id": "trace-assign",
        },
    )

    assert response["status"] == 200
    assert UUID(response["json"]["task"]["assigned_to"]) == reviewer.user.id

    with session_factory() as session:
        logs = session.execute(
            select(AuditLog).where(AuditLog.action == "review_task.assigned")
        ).scalars().all()
    assert any(log.trace_id == "trace-assign" for log in logs)


def test_escalate_task_creates_scholar(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    actor = auth_service.register(
        email="escalate@example.com",
        password="very-strong-password",
        display_name="Escalator",
    )
    _grant_role_directly(session_factory, actor.user.id, "admin")
    _enroll_mfa(session_factory, actor.user.id)

    # Create document version and initial review task via service
    from zayd_common.review_tasks import ReviewTaskService

    uow = SQLAlchemyUnitOfWork(session_factory)
    doc_id = uuid4()
    ver_id = uuid4()
    with uow:
        uow.documents.create(
            Document(
                id=doc_id,
                source_id=uuid4(),
                source_license_id=uuid4(),
                canonical_id="escalate-doc",
                document_type="book",
                title="Escalate Test",
                language="th",
                madhhab="shafii",
                review_status="draft",
                created_by=actor.user.id,
            )
        )
        uow.documents.add_version(
            DocumentVersion(
                id=ver_id,
                document_id=doc_id,
                version_number=1,
                status="scanned_clean",
                content_hash="abc",
                created_by=actor.user.id,
            )
        )
        uow.commit()

    svc = ReviewTaskService(SQLAlchemyUnitOfWork(session_factory))
    initial = svc.create_review_task(
        document_version_id=ver_id,
        actor_user_id=actor.user.id,
        review_level="initial",
    )

    # Claim the task
    _request(
        app,
        "POST",
        f"/reviews/{initial.id}/claim",
        headers={"authorization": f"Bearer {actor.tokens.access_token}"},
    )

    # Escalate
    response = _request(
        app,
        "POST",
        f"/reviews/{initial.id}/escalate",
        headers={
            "authorization": f"Bearer {actor.tokens.access_token}",
            "x-request-id": "trace-escalate",
        },
    )
    assert response["status"] == 200

    # Verify scholar task exists
    with session_factory() as session:
        scholar_tasks = session.execute(
            select(ReviewTask).where(ReviewTask.review_level == "scholar")
        ).scalars().all()
    assert len(scholar_tasks) == 1
    assert str(scholar_tasks[0].document_version_id) == str(ver_id)


def test_get_detail_success(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    actor = auth_service.register(
        email="detail@example.com",
        password="very-strong-password",
        display_name="DetailViewer",
    )
    _grant_role_directly(session_factory, actor.user.id, "admin")
    _enroll_mfa(session_factory, actor.user.id)

    task_id = _seed_queue_task(session_factory)

    response = _request(
        app,
        "GET",
        f"/reviews/{task_id}",
        headers={"authorization": f"Bearer {actor.tokens.access_token}"},
    )

    assert response["status"] == 200
    assert response["json"]["id"] == str(task_id)
    assert response["json"]["document_title"] == "API Test Doc"
    assert "original_file_key" in response["json"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_queue_task(
    session_factory: sessionmaker[Session],
    *,
    title: str = "API Test Doc",
    language: str = "th",
    madhhab: str = "shafii",
    status: str = "open",
    review_level: str = "initial",
    priority: str = "normal",
) -> str:
    """Seed a document, version, and review task for API tests."""
    doc_id = uuid4()
    ver_id = uuid4()
    task_id = uuid4()
    actor = uuid4()
    uow = SQLAlchemyUnitOfWork(session_factory)
    with uow:
        uow.documents.create(
            Document(
                id=doc_id,
                source_id=uuid4(),
                source_license_id=uuid4(),
                canonical_id=f"api-{uuid4().hex[:8]}",
                document_type="book",
                title=title,
                language=language,
                madhhab=madhhab,
                review_status="draft",
                created_by=actor,
            )
        )
        uow.documents.add_version(
            DocumentVersion(
                id=ver_id,
                document_id=doc_id,
                version_number=1,
                status="scanned_clean",
                content_hash="abc123",
                original_file_key="uploads/api-test.txt",
                extracted_text="API test extracted content.",
                metadata_json={"filename": "api-test.txt", "content_type": "text/plain"},
                created_by=actor,
            )
        )
        uow.commit()

    with session_factory() as session:
        session.add(
            ReviewTask(
                id=task_id,
                document_version_id=ver_id,
                document_id=doc_id,
                assigned_to=None,
                review_level=review_level,
                status=status,
                priority=priority,
                category="book",
                language=language,
                madhhab=madhhab,
                created_by=actor,
            )
        )
        session.commit()
    return str(task_id)


def _set_user_preferences(
    session_factory: sessionmaker[Session],
    user_id: Any,
    *,
    language: str = "th",
    madhhab: str = "shafii",
) -> None:
    with session_factory() as session:
        user = session.get(User, user_id)
        if user:
            user.preferred_language = language
            user.preferred_madhhab = madhhab
            session.commit()


def _seed_feedback_record(
    session_factory: sessionmaker[Session],
    *,
    user_id: UUID,
) -> str:
    conversation_id = uuid4()
    message_id = uuid4()
    answer_id = uuid4()
    feedback_id = uuid4()
    with session_factory() as session:
        session.add(
            Conversation(
                id=conversation_id,
                user_id=user_id,
                title="ถาม",
                language="th",
                madhhab="shafii",
            )
        )
        session.add(
            Message(
                id=message_id,
                conversation_id=conversation_id,
                sender_type="assistant",
                body="answer",
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
                answer_json={"answer": "ตอบ"},
                confidence_level="high",
                evidence_sufficient=True,
            )
        )
        session.add(
            Feedback(
                id=feedback_id,
                user_id=user_id,
                answer_id=answer_id,
                citation_id=None,
                category="incorrect_answer",
                body="note",
                status="open",
            )
        )
        session.commit()
    return str(feedback_id)


def _app(monkeypatch: Any) -> tuple[FastAPI, sessionmaker[Session]]:
    engine = create_engine(
        "sqlite:///file:zayd_queue_api_tests?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://zayd_dev:zayd_dev@postgres:5432/zayd_dev")
    monkeypatch.setenv("AUTH_JWT_SECRET", "test-secret")
    storage = FakeStorage(uploaded={})
    monkeypatch.setattr(
        "zayd_service_api.app.S3ObjectStorage",
        lambda settings: storage,
    )
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

        # Split query string from path for ASGI scope
        if "?" in path:
            base_path, qs = path.split("?", 1)
            query_bytes = qs.encode("latin-1")
        else:
            base_path = path
            query_bytes = b""

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": base_path,
            "raw_path": base_path.encode("ascii"),
            "query_string": query_bytes,
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


def _grant_role_directly(
    session_factory: sessionmaker[Session], user_id: Any, role_name: str
) -> None:
    from zayd_common.rbac import RbacService

    rbac_service = RbacService(SQLAlchemyUnitOfWork(session_factory))
    rbac_service.bootstrap_system_roles()
    with _session_scope(session_factory) as session:
        role = session.execute(select(Role).where(Role.name == role_name)).scalar_one()
        if session.get(UserRole, (user_id, role.id)) is None:
            session.add(UserRole(user_id=user_id, role_id=role.id, granted_by=user_id))


def _enroll_mfa(session_factory: sessionmaker[Session], user_id: Any) -> None:
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
