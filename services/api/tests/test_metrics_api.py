from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.auth import AuthService
from zayd_common.database.models import (
    AuditLog,
    Base,
    Document,
    DocumentVersion,
    Provider,
    ReviewTask,
    Role,
    User,
    UserRole,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.rbac import RbacService
from zayd_common.telemetry import telemetry_registry
from zayd_service_api import create_app


def test_admin_dashboard_requires_privileged_access_and_returns_bounded_summary(
    monkeypatch,
) -> None:
    telemetry_registry.reset()
    engine = create_engine(
        "sqlite:///file:zayd_metrics_api?mode=memory&cache=shared&uri=true",
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

    with session_factory() as session:
        user = User(email="metrics@example.test", display_name="Metrics User")
        session.add(user)
        session.flush()
        document_id = uuid4()
        version_id = uuid4()
        session.add(
            Provider(
                name="Provider A",
                provider_type="llm",
                status="enabled",
                data_policy_json={},
                created_by=user.id,
            )
        )
        session.add(
            Document(
                id=document_id,
                source_id=uuid4(),
                source_license_id=uuid4(),
                canonical_id="metrics-doc",
                document_type="book",
                title="Metrics",
                language="th",
                madhhab="shafii",
                review_status="draft",
                created_by=user.id,
            )
        )
        session.add(
            DocumentVersion(
                id=version_id,
                document_id=document_id,
                version_number=1,
                status="parsed",
                content_hash="metrics-hash",
                created_by=user.id,
            )
        )
        session.add(
            ReviewTask(
                document_version_id=version_id,
                document_id=document_id,
                review_level="initial",
                status="open",
                priority="high",
                category="book",
                language="th",
                madhhab="shafii",
                created_by=user.id,
            )
        )
        session.add(
            AuditLog(
                action="incident.created",
                outcome="open",
                actor_user_id=user.id,
                resource_type="incident",
                resource_id=str(uuid4()),
            )
        )
        session.commit()

    telemetry_registry.record_counter(
        "provider_health_total",
        provider="provider-a",
        kind="llm",
        status="ok",
    )
    telemetry_registry.record_counter(
        "external_fallback_total",
        path="expanded_retrieval",
        status="attempted",
    )
    telemetry_registry.record_counter(
        "local_rag_hit_total",
        service="retrieval",
        status="hit",
    )
    telemetry_registry.record_counter(
        "citation_verification_total",
        status="needs_revision",
    )
    telemetry_registry.record_counter(
        "orchestrator_answer_total",
        status="failed",
    )
    telemetry_registry.record_histogram(
        "provider_generate_latency_ms",
        42.0,
        provider="provider-a",
        model="gpt-test",
    )
    app = create_app()
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    account = auth_service.register(
        email="dashboard-user@example.test",
        password="very-strong-password",
        display_name="Dashboard User",
    )
    unauthenticated = _request(app, "GET", "/admin/dashboard")
    assert unauthenticated["status"] == 401

    forbidden = _request(app, "GET", "/admin/dashboard", token=account.tokens.access_token)
    assert forbidden["status"] == 403

    _grant_role(session_factory, account.user.id, "auditor")
    response = _request(
        app,
        "GET",
        "/admin/dashboard?window_minutes=15",
        token=account.tokens.access_token,
    )

    assert response["status"] == 200
    assert response["json"]["summary"]["queue_depth"] >= 1
    assert response["json"]["summary"]["registered_user_count"] >= 1
    assert response["json"]["summary"]["incident_open_count"] >= 1
    assert response["json"]["summary"]["provider_count"] >= 1
    assert response["json"]["summary"]["provider_health_ok_count"] >= 1
    assert response["json"]["summary"]["external_fallback_count"] >= 1
    assert response["json"]["summary"]["local_rag_hit_count"] >= 1
    assert response["json"]["summary"]["citation_failure_count"] >= 1
    assert response["json"]["summary"]["error_count"] >= 1
    assert response["json"]["summary"]["api_latency_ms_avg"] >= 0
    assert response["json"]["window_minutes"] == 15


def _grant_role(session_factory, user_id, role_name: str) -> None:
    RbacService(SQLAlchemyUnitOfWork(session_factory)).bootstrap_system_roles()
    with session_factory() as session:
        role = session.execute(select(Role).where(Role.name == role_name)).scalar_one()
        session.add(UserRole(user_id=user_id, role_id=role.id, granted_by=user_id))
        session.commit()


def _request(app: FastAPI, method: str, path: str, token: str | None = None) -> dict[str, Any]:
    async def run() -> dict[str, Any]:
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.request(
                method,
                path,
                headers={"authorization": f"Bearer {token}"} if token else None,
            )
            return {"status": response.status_code, "json": response.json()}

    return asyncio.run(run())
