"""End-to-end API coverage for TASK-11-05 incident regression candidates."""

from __future__ import annotations

import asyncio
import base64
import os
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.auth import AuthService
from zayd_common.database.models import (
    AuthMfaSecret,
    Base,
    EvaluationCase,
    EvaluationDataset,
    Incident,
    Role,
    UserRole,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.rbac import _bootstrap_system_roles_in_session
from zayd_service_api import create_app


def _app(monkeypatch) -> tuple[FastAPI, str, UUID, UUID, Any]:
    engine = create_engine(
        "sqlite:///file:zayd_incident_regressions?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://zayd_dev:zayd_dev@postgres:5432/zayd_dev")
    monkeypatch.setenv("AUTH_JWT_SECRET", "test-secret")
    monkeypatch.setattr("zayd_service_api.app.get_sessionmaker", lambda _: factory)
    auth = AuthService(SQLAlchemyUnitOfWork(factory), signing_secret="test-secret")
    registered = auth.register(
        email="incident-regression@example.test",
        password="very-strong-password",
        display_name="Regression Reviewer",
    )
    incident_id, dataset_id = uuid4(), uuid4()
    with factory() as session:
        _bootstrap_system_roles_in_session(session)
        admin = session.execute(select(Role).where(Role.name == "admin")).scalar_one()
        session.add(
            UserRole(
                user_id=registered.user.id,
                role_id=admin.id,
                granted_by=registered.user.id,
            )
        )
        session.add(
            AuthMfaSecret(
                user_id=registered.user.id,
                secret=base64.b32encode(os.urandom(20)).decode("ascii"),
                confirmed_at=datetime.now(UTC),
                recovery_codes_rotated_at=datetime.now(UTC),
            )
        )
        session.add(
            Incident(
                id=incident_id,
                severity="p2",
                status="closed",
                summary="Private reporter statement",
                opened_by=registered.user.id,
                idempotency_key="api-incident-regression",
                policy_version="incident-management-v1",
            )
        )
        session.add(
            EvaluationDataset(
                id=dataset_id,
                name="private-incident-regressions",
                version="1.0.0",
                visibility="private",
                license_status="private",
                created_by=registered.user.id,
            )
        )
        session.commit()
    return create_app(), registered.tokens.access_token, incident_id, dataset_id, factory


def _post(app: FastAPI, token: str | None, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    async def run() -> dict[str, Any]:
        headers = {"authorization": f"Bearer {token}"} if token else {}
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            response = await client.post(path, headers=headers, json=payload)
            return {"status": response.status_code, "json": response.json()}

    return asyncio.run(run())


def test_create_incident_regression_case_is_private_sanitized_and_protected(monkeypatch) -> None:
    app, token, incident_id, dataset_id, factory = _app(monkeypatch)
    payload = {
        "dataset_id": str(dataset_id),
        "case": {
            "case_key": "incident.api-001",
            "case_type": "open_ended",
            "visibility": "private",
            "reviewer_status": "draft",
            "question": "Please contact reporter@example.test",
            "expected_behavior": {"outcome": "answer", "rubric": {"required": "source"}},
            "sources": [
                {
                    "source_id": str(uuid4()),
                    "canonical_reference": "source:1",
                    "license_name": "Private license",
                    "license_status": "private",
                    "redistributable": False,
                }
            ],
        },
    }
    response = _post(app, token, f"/admin/incidents/{incident_id}/regression-cases", payload)
    assert response["status"] == 201
    assert response["json"]["redaction_count"] == 1
    with factory() as session:
        case = session.get(EvaluationCase, UUID(response["json"]["evaluation_case_id"]))
        assert case is not None
        assert "reporter@example.test" not in case.question
        assert case.visibility == "private" and case.reviewer_status == "draft"
        assert "Private reporter statement" not in str(case.provenance_json)

    forbidden = _post(app, None, f"/admin/incidents/{incident_id}/regression-cases", payload)
    assert forbidden["status"] == 401
