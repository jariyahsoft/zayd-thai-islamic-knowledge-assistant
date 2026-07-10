"""Integration tests for /admin/feedback review queue API (TASK-11-02)."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from zayd_common.auth import AuthService
from zayd_common.database.models import Answer, Base, Conversation, Feedback, Message
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_service_api import create_app

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _app_with_feedback_and_reviewer(
    monkeypatch, *, db_name: str
) -> tuple[FastAPI, str, list[Any], Any, UUID]:
    """Create app with pre-seeded feedback items and a reviewer user.

    Returns (app, reviewer_token, [feedback_ids], session_factory, reviewer_user_id).
    """
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
    reviewer = auth_service.register(
        email="reviewer@example.test",
        password="very-strong-password",
        display_name="Reviewer",
    )
    # Bootstrap RBAC and grant reviewer+admin roles directly (skip permission check).
    from zayd_common.database.models import AuthMfaSecret, Role, UserRole
    from zayd_common.rbac import _bootstrap_system_roles_in_session  # noqa: F811

    with session_factory() as session:
        _bootstrap_system_roles_in_session(session)
        reviewer_role = session.execute(select(Role).where(Role.name == "reviewer")).scalar_one()
        admin_role = session.execute(select(Role).where(Role.name == "admin")).scalar_one()
        session.add(
            UserRole(
                user_id=reviewer.user.id, role_id=reviewer_role.id, granted_by=reviewer.user.id
            )
        )
        session.add(
            UserRole(user_id=reviewer.user.id, role_id=admin_role.id, granted_by=reviewer.user.id)
        )
        # Enroll MFA by setting a confirmed TOTP secret directly.
        import base64
        import os  # noqa: A001

        raw_secret = os.urandom(20)
        b32_secret = base64.b32encode(raw_secret).decode("ascii")
        from datetime import UTC, datetime

        session.add(
            AuthMfaSecret(
                user_id=reviewer.user.id,
                secret=b32_secret,
                confirmed_at=datetime.now(UTC),
                recovery_codes_rotated_at=datetime.now(UTC),
            )
        )
        session.commit()
    conversation_id = uuid4()
    message_id = uuid4()
    answer_id = uuid4()
    feedback_ids = []
    with session_factory() as session:
        session.add(
            Conversation(
                id=conversation_id,
                user_id=reviewer.user.id,
                title="test",
                language="th",
                madhhab="shafii",
            )
        )
        session.add(
            Message(
                id=message_id,
                conversation_id=conversation_id,
                sender_type="assistant",
                body="answer body",
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
                answer_json={"summary": "s", "answer_th": "t"},
                confidence_level="high",
                evidence_sufficient=True,
            )
        )
        for i in range(3):
            fb_id = uuid4()
            session.add(
                Feedback(
                    id=fb_id,
                    user_id=reviewer.user.id,
                    answer_id=answer_id,
                    category="incorrect_answer" if i % 2 == 0 else "citation_error",
                    body=f"feedback note {i}",
                    status="open",
                    priority="normal",
                    severity="p3",
                    reviewer_notes="",
                )
            )
            feedback_ids.append(fb_id)
        session.commit()
    return (
        create_app(),
        reviewer.tokens.access_token,
        feedback_ids,
        session_factory,
        reviewer.user.id,
    )


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


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------


def test_feedback_review_routes_are_registered(monkeypatch) -> None:
    monkeypatch.setattr("zayd_service_api.app.get_sessionmaker", lambda database_url: object())
    app = create_app()
    route_paths = {route.path for route in app.routes}
    for path in [
        "/admin/feedback",
        "/admin/feedback/{feedback_id}/review",
        "/admin/feedback/{feedback_id}/assign",
        "/admin/feedback/{feedback_id}/classify",
        "/admin/feedback/{feedback_id}/resolve",
    ]:
        assert path in route_paths, f"Expected route {path} not found"


# ---------------------------------------------------------------------------
# Queue listing
# ---------------------------------------------------------------------------


def test_list_feedback_queue_returns_open_items(monkeypatch) -> None:
    app, token, fb_ids, _sf, _uid = _app_with_feedback_and_reviewer(
        monkeypatch, db_name="zayd_fb_queue_list"
    )
    response = _request(app, "GET", "/admin/feedback", token=token)
    assert response["status"] == 200
    assert response["json"]["total_count"] == 3
    assert len(response["json"]["items"]) == 3


def test_list_feedback_queue_requires_auth(monkeypatch) -> None:
    monkeypatch.setattr("zayd_service_api.app.get_sessionmaker", lambda database_url: object())
    app = create_app()
    response = _request(app, "GET", "/admin/feedback")
    assert response["status"] == 401


def test_list_feedback_queue_filters_by_category(monkeypatch) -> None:
    app, token, fb_ids, _sf, _uid = _app_with_feedback_and_reviewer(
        monkeypatch, db_name="zayd_fb_queue_cat"
    )
    response = _request(app, "GET", "/admin/feedback?category=incorrect_answer", token=token)
    assert response["status"] == 200
    assert len(response["json"]["items"]) == 2  # 2 out of 3 are incorrect_answer


def test_list_feedback_queue_pagination(monkeypatch) -> None:
    app, token, fb_ids, _sf, _uid = _app_with_feedback_and_reviewer(
        monkeypatch, db_name="zayd_fb_queue_page"
    )
    response = _request(app, "GET", "/admin/feedback?limit=2&offset=0", token=token)
    assert response["status"] == 200
    assert len(response["json"]["items"]) == 2
    assert response["json"]["next_offset"] == 2


def test_list_feedback_queue_excludes_resolved(monkeypatch) -> None:
    app, token, fb_ids, session_factory, _uid = _app_with_feedback_and_reviewer(
        monkeypatch, db_name="zayd_fb_queue_res"
    )
    # Mark one feedback as resolved via the fixture's session factory.
    from datetime import UTC, datetime

    with session_factory() as session:
        fb = session.get(Feedback, fb_ids[0])
        if fb is not None:
            fb.status = "resolved"
            fb.resolved_at = datetime.now(UTC)
            session.commit()
    response = _request(app, "GET", "/admin/feedback", token=token)
    # Only 2 items should remain (resolved one excluded)
    assert response["status"] == 200
    active_ids = {item["id"] for item in response["json"]["items"]}
    assert str(fb_ids[0]) not in active_ids


# ---------------------------------------------------------------------------
# Review detail
# ---------------------------------------------------------------------------


def test_get_feedback_review_detail(monkeypatch) -> None:
    app, token, fb_ids, _sf, _uid = _app_with_feedback_and_reviewer(
        monkeypatch, db_name="zayd_fb_detail"
    )
    response = _request(app, "GET", f"/admin/feedback/{fb_ids[0]}/review", token=token)
    assert response["status"] == 200
    assert response["json"]["id"] == str(fb_ids[0])
    assert response["json"]["category"] in {"incorrect_answer", "citation_error"}
    assert response["json"]["reviewer_notes"] is not None


def test_get_feedback_review_detail_not_found(monkeypatch) -> None:
    app, token, _fb_ids, _sf, _uid = _app_with_feedback_and_reviewer(
        monkeypatch, db_name="zayd_fb_detail_nf"
    )
    response = _request(app, "GET", f"/admin/feedback/{uuid4()}/review", token=token)
    assert response["status"] == 404


# ---------------------------------------------------------------------------
# Assign
# ---------------------------------------------------------------------------


def test_assign_reviewer(monkeypatch) -> None:
    app, token, fb_ids, _sf, reviewer_user_id = _app_with_feedback_and_reviewer(
        monkeypatch, db_name="zayd_fb_assign"
    )
    response = _request(
        app,
        "PUT",
        f"/admin/feedback/{fb_ids[0]}/assign",
        token=token,
        json_body={"reviewer_id": str(reviewer_user_id)},
    )
    assert response["status"] == 200
    assert response["json"]["status"] == "in_review"
    assert response["json"]["reviewer_id"] == str(reviewer_user_id)


def test_assign_requires_feedback_manage(monkeypatch) -> None:
    app, token, fb_ids, _sf, _uid = _app_with_feedback_and_reviewer(
        monkeypatch, db_name="zayd_fb_assign_perm"
    )
    # Create a regular user without FEEDBACK_MANAGE
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from zayd_common.auth import AuthService

    engine = create_engine(
        "sqlite:///file:zayd_fb_assign_perm?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(
        "zayd_service_api.app.get_sessionmaker",
        lambda database_url: session_factory,
    )
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    user = auth_service.register(
        email="user@example.test", password="very-strong-password", display_name="User"
    )
    response = _request(
        app,
        "PUT",
        f"/admin/feedback/{fb_ids[0]}/assign",
        token=user.tokens.access_token,
        json_body={"reviewer_id": str(uuid4())},
    )
    assert response["status"] == 403


# ---------------------------------------------------------------------------
# Classify
# ---------------------------------------------------------------------------


def test_classify_feedback(monkeypatch) -> None:
    app, token, fb_ids, _sf, _uid = _app_with_feedback_and_reviewer(
        monkeypatch, db_name="zayd_fb_classify"
    )
    response = _request(
        app,
        "PATCH",
        f"/admin/feedback/{fb_ids[0]}/classify",
        token=token,
        json_body={
            "root_cause": "model_error",
            "priority": "high",
            "severity": "p1",
            "reviewer_notes": "Checked the model output.",
        },
    )
    assert response["status"] == 200
    assert response["json"]["root_cause"] == "model_error"
    assert response["json"]["priority"] == "high"
    assert response["json"]["severity"] == "p1"


def test_classify_invalid_root_cause(monkeypatch) -> None:
    app, token, fb_ids, _sf, _uid = _app_with_feedback_and_reviewer(
        monkeypatch, db_name="zayd_fb_classify_bad"
    )
    response = _request(
        app,
        "PATCH",
        f"/admin/feedback/{fb_ids[0]}/classify",
        token=token,
        json_body={"root_cause": "invalid_value"},
    )
    assert response["status"] == 400


# ---------------------------------------------------------------------------
# Resolve
# ---------------------------------------------------------------------------


def test_resolve_feedback(monkeypatch) -> None:
    app, token, fb_ids, _sf, _uid = _app_with_feedback_and_reviewer(
        monkeypatch, db_name="zayd_fb_resolve"
    )
    response = _request(
        app,
        "POST",
        f"/admin/feedback/{fb_ids[0]}/resolve",
        token=token,
        json_body={"resolution": "Fixed the citation error."},
    )
    assert response["status"] == 200
    assert response["json"]["status"] == "resolved"
    assert response["json"]["resolution"] is not None


def test_resolve_feedback_dismiss(monkeypatch) -> None:
    app, token, fb_ids, _sf, _uid = _app_with_feedback_and_reviewer(
        monkeypatch, db_name="zayd_fb_dismiss"
    )
    response = _request(
        app,
        "POST",
        f"/admin/feedback/{fb_ids[0]}/resolve",
        token=token,
        json_body={"resolution": "Duplicate report.", "dismissed": True},
    )
    assert response["status"] == 200
    assert response["json"]["status"] == "dismissed"


def test_resolve_empty_resolution_rejected(monkeypatch) -> None:
    app, token, fb_ids, _sf, _uid = _app_with_feedback_and_reviewer(
        monkeypatch, db_name="zayd_fb_resolve_empty"
    )
    response = _request(
        app,
        "POST",
        f"/admin/feedback/{fb_ids[0]}/resolve",
        token=token,
        json_body={"resolution": ""},
    )
    # Pydantic min_length=1 catches empty resolution → 422
    assert response["status"] in (400, 422)


def test_resolve_already_resolved_rejected(monkeypatch) -> None:
    app, token, fb_ids, _sf, _uid = _app_with_feedback_and_reviewer(
        monkeypatch, db_name="zayd_fb_resolve_twice"
    )
    # First resolve succeeds
    _request(
        app,
        "POST",
        f"/admin/feedback/{fb_ids[0]}/resolve",
        token=token,
        json_body={"resolution": "Fixed."},
    )
    # Second resolve should be rejected
    response = _request(
        app,
        "POST",
        f"/admin/feedback/{fb_ids[0]}/resolve",
        token=token,
        json_body={"resolution": "Fixed again."},
    )
    assert response["status"] == 409
    assert (
        "already resolved" in (response["json"] or {}).get("error", {}).get("message", "").lower()
    )


# ---------------------------------------------------------------------------
# Full workflow
# ---------------------------------------------------------------------------


def test_full_feedback_review_workflow(monkeypatch) -> None:
    """End-to-end: list → detail → assign → classify → resolve."""
    app, token, fb_ids, _sf, _uid = _app_with_feedback_and_reviewer(
        monkeypatch, db_name="zayd_fb_full"
    )

    # 1. List
    list_resp = _request(app, "GET", "/admin/feedback", token=token)
    assert list_resp["status"] == 200
    assert list_resp["json"]["total_count"] >= 1

    # 2. Detail
    detail_resp = _request(app, "GET", f"/admin/feedback/{fb_ids[0]}/review", token=token)
    assert detail_resp["status"] == 200

    # 3. Assign
    assign_resp = _request(
        app,
        "PUT",
        f"/admin/feedback/{fb_ids[0]}/assign",
        token=token,
        json_body={"reviewer_id": str(_uid)},
    )
    assert assign_resp["status"] == 200
    assert assign_resp["json"]["status"] == "in_review"

    # 4. Classify
    classify_resp = _request(
        app,
        "PATCH",
        f"/admin/feedback/{fb_ids[0]}/classify",
        token=token,
        json_body={
            "root_cause": "model_error",
            "priority": "high",
            "severity": "p1",
            "reviewer_notes": "Reviewed the evidence.",
        },
    )
    assert classify_resp["status"] == 200
    assert classify_resp["json"]["root_cause"] == "model_error"

    # 5. Resolve
    resolve_resp = _request(
        app,
        "POST",
        f"/admin/feedback/{fb_ids[0]}/resolve",
        token=token,
        json_body={"resolution": "Model retrained with corrected dataset."},
    )
    assert resolve_resp["status"] == 200
    assert resolve_resp["json"]["status"] == "resolved"
