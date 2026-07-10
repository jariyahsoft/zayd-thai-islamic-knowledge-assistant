"""Integration tests for Evaluation Run Listing and Run Comparison APIs (TASK-12-07)."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.auth import AuthService
from zayd_common.database.models import (
    Base,
    EvaluationCase,
    EvaluationDataset,
    EvaluationResult,
    EvaluationRun,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_service_api import create_app


def _app_setup(
    monkeypatch, *, db_name: str, has_eval_read: bool = True
) -> tuple[FastAPI, str, list[Any], UUID]:
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
    admin = auth_service.register(
        email="admin-eval@example.test",
        password="very-strong-password",
        display_name="Admin",
    )

    # Grant admin / scholar / default roles
    from zayd_common.database.models import AuthMfaSecret, Role, UserRole
    from zayd_common.rbac import _bootstrap_system_roles_in_session  # noqa: F811

    with session_factory() as session:
        _bootstrap_system_roles_in_session(session)
        if has_eval_read:
            admin_role = session.execute(
                select(Role).where(Role.name == "admin")
            ).scalar_one()
            session.add(
                UserRole(
                    user_id=admin.user.id,
                    role_id=admin_role.id,
                    granted_by=admin.user.id,
                )
            )

        # Confirmed MFA secret to pass privileged gate
        import base64
        import os  # noqa: A001
        raw_secret = os.urandom(20)
        b32_secret = base64.b32encode(raw_secret).decode("ascii")
        from datetime import UTC, datetime
        session.add(
            AuthMfaSecret(
                user_id=admin.user.id,
                secret=b32_secret,
                confirmed_at=datetime.now(UTC),
                recovery_codes_rotated_at=datetime.now(UTC),
            )
        )
        session.commit()

    run_ids = []
    dataset_id = uuid4()
    with session_factory() as session:
        session.add(
            EvaluationDataset(
                id=dataset_id,
                name="dataset",
                version="1.0.0",
                license_status="private",
                visibility="private",
                status="ready",
                manifest_json={},
                created_by=admin.user.id,
            )
        )
        cases = [
            EvaluationCase(
                dataset_id=dataset_id,
                case_key="case.public",
                schema_version="evaluation-case-v1",
                case_type="open_ended",
                visibility="public",
                reviewer_status="approved",
                reviewed_by=admin.user.id,
                question="q public",
                choices_json=[],
                expected_citations=[],
                expected_behavior={"outcome": "answer"},
                source_references=[],
                license_metadata={},
                provenance_json={"topic": "taharah", "language": "th", "madhhab": "shafii"},
                risk_level="low",
            ),
            EvaluationCase(
                dataset_id=dataset_id,
                case_key="case.private",
                schema_version="evaluation-case-v1",
                case_type="open_ended",
                visibility="private",
                reviewer_status="approved",
                reviewed_by=admin.user.id,
                question="q private",
                choices_json=[],
                expected_citations=[],
                expected_behavior={"outcome": "answer"},
                source_references=[],
                license_metadata={},
                provenance_json={"topic": "salah", "language": "th", "madhhab": "shafii"},
                risk_level="high",
            ),
        ]
        session.add_all(cases)
        for i in range(2):
            run_id = uuid4()
            session.add(
                EvaluationRun(
                    id=run_id,
                    dataset_id=dataset_id,
                    model_configuration_id=uuid4(),
                    prompt_version_id=uuid4(),
                    policy_version_id=uuid4(),
                    status="passed",
                    metrics_json={},
                    run_config_json={
                        "dataset_name": "dataset",
                        "dataset_version": "1.0.0",
                        "provider_name": "prov",
                        "model_name": f"model_{i}",
                        "retriever_version": "v1",
                    },
                    random_seed=7,
                    git_commit="abc",
                    started_at=datetime.now(UTC),
                )
            )
            session.flush()
            session.add_all(
                [
                    EvaluationResult(
                        evaluation_run_id=run_id,
                        evaluation_case_id=cases[0].id,
                        passed=True if i == 0 else False,  # Regression on second run
                        scores_json={"correctness": 1.0 if i == 0 else 0.0},
                        output_json={"outcome": "answer"},
                    ),
                    EvaluationResult(
                        evaluation_run_id=run_id,
                        evaluation_case_id=cases[1].id,
                        passed=False if i == 0 else True,  # Improvement on second run
                        scores_json={"correctness": 0.0 if i == 0 else 1.0},
                        output_json={"outcome": "answer"},
                    ),
                ]
            )
            run_ids.append(run_id)
        session.commit()

    return create_app(), admin.tokens.access_token, run_ids, dataset_id


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


def test_list_runs_api(monkeypatch) -> None:
    app, token, run_ids, dataset_id = _app_setup(monkeypatch, db_name="zayd_comp_api_list")
    resp = _request(app, "GET", "/admin/evaluation/runs", token=token)
    assert resp["status"] == 200
    assert len(resp["json"]["runs"]) >= 2


def test_get_run_api(monkeypatch) -> None:
    app, token, run_ids, _ = _app_setup(monkeypatch, db_name="zayd_comp_api_get")
    resp = _request(app, "GET", f"/admin/evaluation/runs/{run_ids[0]}", token=token)
    assert resp["status"] == 200
    assert resp["json"]["run_id"] == str(run_ids[0])


def test_compare_runs_api_with_read_permission(monkeypatch) -> None:
    app, token, run_ids, _ = _app_setup(monkeypatch, db_name="zayd_comp_api_compare")
    resp = _request(
        app,
        "GET",
        f"/admin/evaluation/compare?base_run_id={run_ids[0]}&target_run_id={run_ids[1]}",
        token=token,
    )
    assert resp["status"] == 200
    report = resp["json"]
    assert report["base_run"]["run_id"] == str(run_ids[0])
    assert report["target_run"]["run_id"] == str(run_ids[1])
    assert report["regression_count"] == 1
    assert report["improvement_count"] == 1
    assert len(report["comparisons"]) == 2


def test_compare_runs_api_forbidden_without_evals_read(monkeypatch) -> None:
    # Set has_eval_read to False, meaning the token has the 'user' role and lacks evaluations.read
    app, token, run_ids, _ = _app_setup(
        monkeypatch, db_name="zayd_comp_api_forbidden", has_eval_read=False
    )
    resp = _request(app, "GET", "/admin/evaluation/runs", token=token)
    assert resp["status"] == 403
