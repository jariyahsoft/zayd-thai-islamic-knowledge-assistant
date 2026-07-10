"""Integration tests for the document review API.

Covers:
- get draft endpoint
- apply edit draft endpoint
- add comment endpoint
- decide review task endpoint
- optimistic locking concurrency check
- self-approval and RBAC check
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
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
    Citation,
    Document,
    DocumentChunk,
    DocumentVersion,
    RetrievalResult,
    RetrievalRun,
    ReviewApproval,
    ReviewTask,
    Role,
    Source,
    SourceLicense,
    User,
    UserRole,
)
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.mfa import MfaService, generate_totp
from zayd_service_api import create_app


class FakeStorage:
    def __init__(self, uploaded=None) -> None:
        self.uploaded = uploaded or {}

    def get_private_bytes(self, *, key: str) -> bytes:
        return b"file bytes content"

    def put_private_bytes(self, **kwargs) -> Any:
        return None


def test_scholar_approval_routes_are_registered(monkeypatch) -> None:
    app, _session_factory = _app(monkeypatch)

    route_paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert "/reviews/{review_task_id}/approvals" in route_paths
    assert "/documents/{document_version_id}/approval-requirements" in route_paths
    assert "/review-approvals/{approval_id}/revoke" in route_paths
    assert "/documents/{document_version_id}/publish" in route_paths
    assert "/documents/{document_id}/suspend" in route_paths
    assert "/documents/{document_id}/archive" in route_paths
    assert "/documents/{document_id}/rollback" in route_paths


def test_scholar_approval_openapi_contract(monkeypatch) -> None:
    app, _session_factory = _app(monkeypatch)
    schema = app.openapi()

    paths = schema["paths"]
    assert paths["/reviews/{review_task_id}/approvals"]["post"]["responses"]["200"]
    assert paths["/documents/{document_version_id}/approval-requirements"]["get"]["responses"][
        "200"
    ]
    assert paths["/documents/{document_version_id}/approvals"]["get"]["responses"]["200"]
    assert paths["/review-approvals/{approval_id}/revoke"]["post"]["responses"]["200"]
    assert paths["/documents/{document_version_id}/publish"]["post"]["responses"]["200"]
    assert paths["/documents/{document_id}/suspend"]["post"]["responses"]["200"]
    assert paths["/documents/{document_id}/archive"]["post"]["responses"]["200"]
    assert paths["/documents/{document_id}/rollback"]["post"]["responses"]["200"]
    assert schema["components"]["schemas"]["ScholarApprovalRequest"]
    assert schema["components"]["schemas"]["ApprovalRequirementResponse"]
    assert schema["components"]["schemas"]["ApprovalListResponse"]
    assert schema["components"]["schemas"]["ScholarApprovalActionResponse"]
    assert schema["components"]["schemas"]["DocumentPublishRequest"]
    assert schema["components"]["schemas"]["DocumentPublishResponse"]
    assert schema["components"]["schemas"]["DocumentLifecycleResponse"]


def test_get_review_draft_requires_permission(monkeypatch) -> None:
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
        f"/reviews/{uuid4()}/draft",
        headers={"authorization": f"Bearer {actor.tokens.access_token}"},
    )

    assert response["status"] == 403
    assert response["json"]["error"]["code"] == "RBAC_FORBIDDEN"


def test_get_review_draft_success(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    actor = auth_service.register(
        email="reviewer@example.com",
        password="very-strong-password",
        display_name="Reviewer",
    )
    _grant_role_directly(session_factory, actor.user.id, "reviewer")
    _enroll_mfa(session_factory, actor.user.id)
    _set_user_preferences(session_factory, actor.user.id)

    task_id, version_id = _seed_draft_task(session_factory, assigned_to=actor.user.id)

    response = _request(
        app,
        "GET",
        f"/reviews/{task_id}/draft",
        headers={"authorization": f"Bearer {actor.tokens.access_token}"},
    )

    assert response["status"] == 200
    assert response["json"]["review_task_id"] == str(task_id)
    assert response["json"]["document_version_id"] == str(version_id)
    assert UUID(response["json"]["document_id"])
    assert UUID(response["json"]["source_id"])
    assert UUID(response["json"]["source_license_id"])
    assert response["json"]["canonical_id"].startswith("doc-")
    assert response["json"]["document_title"] == "API Test Doc Title"
    assert response["json"]["document_type"] == "book"
    assert response["json"]["language"] == "th"
    assert response["json"]["madhhab"] == "shafii"
    assert response["json"]["editable_text"] == "Old content lines"
    assert response["json"]["editable_metadata"]["title"] == "API Test Doc Title"
    assert response["json"]["task_row_version"] == 1
    assert response["json"]["revisions"] == []


def test_apply_edit_validation_errors(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    actor = auth_service.register(
        email="reviewer-edit-val@example.com",
        password="very-strong-password",
        display_name="Reviewer",
    )
    _grant_role_directly(session_factory, actor.user.id, "reviewer")
    _enroll_mfa(session_factory, actor.user.id)
    _set_user_preferences(session_factory, actor.user.id)

    task_id, _ = _seed_draft_task(session_factory, assigned_to=actor.user.id)

    # Missing row version
    response = _request(
        app,
        "PATCH",
        f"/reviews/{task_id}/draft",
        json_body={"text": "New content"},
        headers={"authorization": f"Bearer {actor.tokens.access_token}"},
    )
    assert response["status"] == 422

    # Empty edit
    response = _request(
        app,
        "PATCH",
        f"/reviews/{task_id}/draft",
        json_body={"base_task_row_version": 1},
        headers={"authorization": f"Bearer {actor.tokens.access_token}"},
    )
    assert response["status"] == 400
    assert response["json"]["error"]["code"] == "DOCUMENT_REVIEW_EMPTY_EDIT"


def test_apply_edit_success(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    actor = auth_service.register(
        email="reviewer-edit-ok@example.com",
        password="very-strong-password",
        display_name="Reviewer",
    )
    _grant_role_directly(session_factory, actor.user.id, "reviewer")
    _enroll_mfa(session_factory, actor.user.id)
    _set_user_preferences(session_factory, actor.user.id)

    task_id, _ = _seed_draft_task(session_factory, assigned_to=actor.user.id)

    response = _request(
        app,
        "PATCH",
        f"/reviews/{task_id}/draft",
        json_body={
            "base_task_row_version": 1,
            "text": "New and updated content lines",
            "metadata_updates": {"title": "Updated API Test Doc Title", "author": "New Author"},
        },
        headers={
            "authorization": f"Bearer {actor.tokens.access_token}",
            "x-request-id": "trace-edit-1",
        },
    )

    assert response["status"] == 200
    assert response["json"]["task_row_version"] == 2
    assert response["json"]["editable_text"] == "New and updated content lines"
    assert response["json"]["editable_metadata"]["title"] == "Updated API Test Doc Title"
    assert response["json"]["revision"]["text_changed"] is True
    assert set(response["json"]["revision"]["metadata_changed_fields"]) == {"title", "author"}

    # Verify audit
    with session_factory() as session:
        logs = session.execute(
            select(AuditLog).where(AuditLog.action == "document_review.revision.created")
        ).scalars().all()
    assert any(log.trace_id == "trace-edit-1" for log in logs)


def test_add_comment_success(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    actor = auth_service.register(
        email="reviewer-comment@example.com",
        password="very-strong-password",
        display_name="Reviewer",
    )
    _grant_role_directly(session_factory, actor.user.id, "reviewer")
    _enroll_mfa(session_factory, actor.user.id)
    _set_user_preferences(session_factory, actor.user.id)

    task_id, _ = _seed_draft_task(session_factory, assigned_to=actor.user.id)

    response = _request(
        app,
        "POST",
        f"/reviews/{task_id}/comments",
        json_body={"body": "This is a test comment", "anchor": {"line": 10}},
        headers={
            "authorization": f"Bearer {actor.tokens.access_token}",
            "x-request-id": "trace-comment-1",
        },
    )

    assert response["status"] == 200
    assert response["json"]["body"] == "This is a test comment"
    assert response["json"]["anchor"] == {"line": 10}

    # Verify audit
    with session_factory() as session:
        logs = session.execute(
            select(AuditLog).where(AuditLog.action == "document_review.comment.created")
        ).scalars().all()
    assert any(log.trace_id == "trace-comment-1" for log in logs)


def test_decide_request_changes_success(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    actor = auth_service.register(
        email="reviewer-decide@example.com",
        password="very-strong-password",
        display_name="Reviewer",
    )
    _grant_role_directly(session_factory, actor.user.id, "reviewer")
    _enroll_mfa(session_factory, actor.user.id)
    _set_user_preferences(session_factory, actor.user.id)

    task_id, _ = _seed_draft_task(session_factory, assigned_to=actor.user.id)

    response = _request(
        app,
        "POST",
        f"/reviews/{task_id}/decision",
        json_body={
            "decision": "request_changes",
            "reason": "Missing secondary references",
            "base_task_row_version": 1,
        },
        headers={
            "authorization": f"Bearer {actor.tokens.access_token}",
            "x-request-id": "trace-decide-1",
        },
    )

    assert response["status"] == 200
    assert response["json"]["status"] == "ok"
    assert response["json"]["task_row_version"] == 2
    assert response["json"]["decision"]["resulting_task_status"] == "completed"
    assert response["json"]["decision"]["resulting_document_status"] == "changes_requested"

    # Verify audit
    with session_factory() as session:
        logs = session.execute(
            select(AuditLog).where(AuditLog.action == "document_review.decision.request_changes")
        ).scalars().all()
    assert any(log.trace_id == "trace-decide-1" for log in logs)


def test_decide_approve_separation_of_duties(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    actor = auth_service.register(
        email="uploader-reviewer@example.com",
        password="very-strong-password",
        display_name="UploaderReviewer",
    )
    _grant_role_directly(session_factory, actor.user.id, "reviewer")
    _enroll_mfa(session_factory, actor.user.id)
    _set_user_preferences(session_factory, actor.user.id)

    task_id, _ = _seed_draft_task(
        session_factory,
        created_by=actor.user.id,
        assigned_to=actor.user.id,
    )

    response = _request(
        app,
        "POST",
        f"/reviews/{task_id}/decision",
        json_body={
            "decision": "approve",
            "reason": "Looks good",
            "base_task_row_version": 1,
        },
        headers={"authorization": f"Bearer {actor.tokens.access_token}"},
    )

    assert response["status"] == 403
    assert response["json"]["error"]["code"] == "DOCUMENT_REVIEW_SELF_APPROVAL_DENIED"


def test_scholar_approval_api_two_level_success(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    reviewer = auth_service.register(
        email="approval-reviewer@example.com",
        password="very-strong-password",
        display_name="Reviewer",
    )
    scholar = auth_service.register(
        email="approval-scholar@example.com",
        password="very-strong-password",
        display_name="Scholar",
    )
    _grant_role_directly(session_factory, reviewer.user.id, "reviewer")
    _grant_role_directly(session_factory, scholar.user.id, "senior_scholar")
    _enroll_mfa(session_factory, reviewer.user.id)
    _enroll_mfa(session_factory, scholar.user.id)
    _set_user_preferences(session_factory, reviewer.user.id)
    _set_user_preferences(session_factory, scholar.user.id)
    task_id, version_id = _seed_draft_task(
        session_factory,
        assigned_to=scholar.user.id,
        review_level="scholar",
        document_status="scholar_review",
    )

    initial = _request(
        app,
        "POST",
        f"/reviews/{task_id}/approvals",
        json_body={
            "content_risk": "sensitive",
            "approval_level": "initial",
            "reason": "Initial reviewer approval.",
        },
        headers={
            "authorization": f"Bearer {reviewer.tokens.access_token}",
            "x-request-id": "trace-approval-initial",
        },
    )
    scholar_response = _request(
        app,
        "POST",
        f"/reviews/{task_id}/approvals",
        json_body={
            "content_risk": "sensitive",
            "approval_level": "scholar",
            "reason": "Senior scholar approval.",
        },
        headers={
            "authorization": f"Bearer {scholar.tokens.access_token}",
            "x-request-id": "trace-approval-scholar",
        },
    )
    requirements = _request(
        app,
        "GET",
        f"/documents/{version_id}/approval-requirements?content_risk=sensitive",
        headers={"authorization": f"Bearer {scholar.tokens.access_token}"},
    )

    assert initial["status"] == 200
    assert initial["json"]["approval"]["approval_level"] == "initial"
    assert scholar_response["status"] == 200
    assert scholar_response["json"]["approval"]["approval_level"] == "scholar"
    assert requirements["status"] == 200
    assert requirements["json"]["ready_for_publish"] is True
    assert requirements["json"]["missing_levels"] == []
    with session_factory() as session:
        logs = session.execute(
            select(AuditLog).where(AuditLog.action == "scholar_approval.created")
        ).scalars().all()
    assert any(log.trace_id == "trace-approval-scholar" for log in logs)


def test_scholar_approval_api_blocks_self_approval(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    actor = auth_service.register(
        email="approval-uploader@example.com",
        password="very-strong-password",
        display_name="UploaderScholar",
    )
    _grant_role_directly(session_factory, actor.user.id, "senior_scholar")
    _enroll_mfa(session_factory, actor.user.id)
    _set_user_preferences(session_factory, actor.user.id)
    task_id, _ = _seed_draft_task(
        session_factory,
        created_by=actor.user.id,
        assigned_to=actor.user.id,
        review_level="scholar",
        document_status="scholar_review",
    )

    response = _request(
        app,
        "POST",
        f"/reviews/{task_id}/approvals",
        json_body={
            "content_risk": "sensitive",
            "approval_level": "scholar",
            "reason": "Self approval attempt.",
        },
        headers={"authorization": f"Bearer {actor.tokens.access_token}"},
    )

    assert response["status"] == 403
    assert response["json"]["error"]["code"] == "SCHOLAR_APPROVAL_SELF_APPROVAL_DENIED"


def test_scholar_approval_api_revoke_marks_requirement_missing(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    reviewer = auth_service.register(
        email="approval-revoke-reviewer@example.com",
        password="very-strong-password",
        display_name="Reviewer",
    )
    scholar = auth_service.register(
        email="approval-revoke-scholar@example.com",
        password="very-strong-password",
        display_name="Scholar",
    )
    _grant_role_directly(session_factory, reviewer.user.id, "reviewer")
    _grant_role_directly(session_factory, scholar.user.id, "senior_scholar")
    _enroll_mfa(session_factory, reviewer.user.id)
    _enroll_mfa(session_factory, scholar.user.id)
    _set_user_preferences(session_factory, reviewer.user.id)
    _set_user_preferences(session_factory, scholar.user.id)
    task_id, version_id = _seed_draft_task(session_factory, assigned_to=reviewer.user.id)
    with session_factory() as session:
        approval = ReviewApproval(
            id=uuid4(),
            document_version_id=version_id,
            review_task_id=task_id,
            approver_id=reviewer.user.id,
            approval_level="initial",
            content_risk="routine",
            status="active",
            reason="Routine approval.",
        )
        session.add(approval)
        approval_id = approval.id
        session.commit()

    revoked = _request(
        app,
        "POST",
        f"/review-approvals/{approval_id}/revoke",
        json_body={"reason": "Citation issue found."},
        headers={
            "authorization": f"Bearer {scholar.tokens.access_token}",
            "x-request-id": "trace-approval-revoke",
        },
    )
    requirements = _request(
        app,
        "GET",
        f"/documents/{version_id}/approval-requirements?content_risk=routine",
        headers={"authorization": f"Bearer {scholar.tokens.access_token}"},
    )

    assert revoked["status"] == 200
    assert revoked["json"]["approval"]["status"] == "revoked"
    assert requirements["status"] == 200
    assert requirements["json"]["ready_for_publish"] is False
    assert requirements["json"]["missing_levels"] == ["initial"]


def test_scholar_approval_api_lists_history(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    reviewer = auth_service.register(
        email="approval-history-reviewer@example.com",
        password="very-strong-password",
        display_name="Reviewer",
    )
    scholar = auth_service.register(
        email="approval-history-scholar@example.com",
        password="very-strong-password",
        display_name="Scholar",
    )
    _grant_role_directly(session_factory, reviewer.user.id, "reviewer")
    _grant_role_directly(session_factory, scholar.user.id, "senior_scholar")
    _enroll_mfa(session_factory, reviewer.user.id)
    _enroll_mfa(session_factory, scholar.user.id)
    _set_user_preferences(session_factory, reviewer.user.id)
    _set_user_preferences(session_factory, scholar.user.id)
    task_id, version_id = _seed_draft_task(
        session_factory,
        assigned_to=scholar.user.id,
        review_level="scholar",
        document_status="scholar_review",
    )

    initial = _request(
        app,
        "POST",
        f"/reviews/{task_id}/approvals",
        json_body={
            "content_risk": "sensitive",
            "approval_level": "initial",
            "reason": "Initial approval recorded.",
        },
        headers={"authorization": f"Bearer {reviewer.tokens.access_token}"},
    )
    scholar_response = _request(
        app,
        "POST",
        f"/reviews/{task_id}/approvals",
        json_body={
            "content_risk": "sensitive",
            "approval_level": "scholar",
            "reason": "Scholar approval recorded.",
        },
        headers={"authorization": f"Bearer {scholar.tokens.access_token}"},
    )
    revoke = _request(
        app,
        "POST",
        f"/review-approvals/{initial['json']['approval']['id']}/revoke",
        json_body={"reason": "Evidence gap."},
        headers={"authorization": f"Bearer {scholar.tokens.access_token}"},
    )
    history = _request(
        app,
        "GET",
        f"/documents/{version_id}/approvals",
        headers={"authorization": f"Bearer {scholar.tokens.access_token}"},
    )

    assert scholar_response["status"] == 200
    assert revoke["status"] == 200
    assert history["status"] == 200
    assert history["json"]["document_version_id"] == str(version_id)
    assert [item["approval_level"] for item in history["json"]["approvals"]] == [
        "scholar",
        "initial",
    ]
    assert history["json"]["approvals"][1]["status"] == "revoked"
    assert history["json"]["approvals"][1]["revoke_reason"] == "Evidence gap."


def test_document_publish_api_success_and_retry(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    reviewer = auth_service.register(
        email="publish-reviewer@example.com",
        password="very-strong-password",
        display_name="Reviewer",
    )
    scholar = auth_service.register(
        email="publish-scholar@example.com",
        password="very-strong-password",
        display_name="Scholar",
    )
    _grant_role_directly(session_factory, reviewer.user.id, "reviewer")
    _grant_role_directly(session_factory, scholar.user.id, "senior_scholar")
    _enroll_mfa(session_factory, reviewer.user.id)
    _enroll_mfa(session_factory, scholar.user.id)
    _set_user_preferences(session_factory, reviewer.user.id)
    _set_user_preferences(session_factory, scholar.user.id)
    task_id, version_id = _seed_draft_task(
        session_factory,
        created_by=reviewer.user.id,
        assigned_to=scholar.user.id,
        review_level="scholar",
        document_status="scholar_approved",
        version_status="scholar_approved",
    )
    _seed_api_approval(
        session_factory,
        task_id=task_id,
        version_id=version_id,
        approver_id=reviewer.user.id,
        level="initial",
    )
    _seed_api_approval(
        session_factory,
        task_id=task_id,
        version_id=version_id,
        approver_id=scholar.user.id,
        level="scholar",
    )

    published = _request(
        app,
        "POST",
        f"/documents/{version_id}/publish",
        json_body={"content_risk": "sensitive", "reason": "Approved for retrieval."},
        headers={
            "authorization": f"Bearer {scholar.tokens.access_token}",
            "x-request-id": "trace-publish-api",
        },
    )
    retried = _request(
        app,
        "POST",
        f"/documents/{version_id}/publish",
        json_body={"content_risk": "sensitive", "reason": "Retry publish."},
        headers={"authorization": f"Bearer {scholar.tokens.access_token}"},
    )

    assert published["status"] == 200
    assert published["json"]["document_version_id"] == str(version_id)
    assert published["json"]["document_status"] == "published"
    assert published["json"]["chunk_count"] == 1
    assert published["json"]["idempotent"] is False
    assert published["json"]["embedding_pipeline_version"] == "embedding-record-v1"
    assert retried["status"] == 200
    assert retried["json"]["idempotent"] is True
    with session_factory() as session:
        chunks = session.execute(
            select(DocumentChunk).where(DocumentChunk.document_version_id == version_id)
        ).scalars().all()
        logs = session.execute(
            select(AuditLog).where(AuditLog.action == "documents.publish")
        ).scalars().all()
    assert len(chunks) == 1
    assert chunks[0].is_published is True
    assert any(log.trace_id == "trace-publish-api" for log in logs)


def test_document_publish_api_requires_publish_permission(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    reviewer = auth_service.register(
        email="publish-forbidden-reviewer@example.com",
        password="very-strong-password",
        display_name="Reviewer",
    )
    _grant_role_directly(session_factory, reviewer.user.id, "reviewer")
    _enroll_mfa(session_factory, reviewer.user.id)
    _set_user_preferences(session_factory, reviewer.user.id)

    response = _request(
        app,
        "POST",
        f"/documents/{uuid4()}/publish",
        json_body={"content_risk": "routine", "reason": "Not allowed."},
        headers={"authorization": f"Bearer {reviewer.tokens.access_token}"},
    )

    assert response["status"] == 403
    assert response["json"]["error"]["code"] == "RBAC_FORBIDDEN"


def test_document_publish_api_license_failure_leaves_chunks_hidden(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    reviewer = auth_service.register(
        email="publish-license-reviewer@example.com",
        password="very-strong-password",
        display_name="Reviewer",
    )
    scholar = auth_service.register(
        email="publish-license-scholar@example.com",
        password="very-strong-password",
        display_name="Scholar",
    )
    _grant_role_directly(session_factory, reviewer.user.id, "reviewer")
    _grant_role_directly(session_factory, scholar.user.id, "senior_scholar")
    _enroll_mfa(session_factory, reviewer.user.id)
    _enroll_mfa(session_factory, scholar.user.id)
    _set_user_preferences(session_factory, reviewer.user.id)
    _set_user_preferences(session_factory, scholar.user.id)
    task_id, version_id = _seed_draft_task(
        session_factory,
        created_by=reviewer.user.id,
        assigned_to=scholar.user.id,
        review_level="scholar",
        document_status="scholar_approved",
        version_status="scholar_approved",
        embedding_permission="prohibited",
    )
    _seed_api_approval(
        session_factory,
        task_id=task_id,
        version_id=version_id,
        approver_id=reviewer.user.id,
        level="initial",
    )
    _seed_api_approval(
        session_factory,
        task_id=task_id,
        version_id=version_id,
        approver_id=scholar.user.id,
        level="scholar",
    )

    response = _request(
        app,
        "POST",
        f"/documents/{version_id}/publish",
        json_body={"content_risk": "sensitive", "reason": "Attempt publish."},
        headers={"authorization": f"Bearer {scholar.tokens.access_token}"},
    )

    assert response["status"] == 409
    assert response["json"]["error"]["code"] == "DOCUMENT_PUBLISH_LICENSE_BLOCKED"
    with session_factory() as session:
        chunks = session.execute(
            select(DocumentChunk).where(DocumentChunk.document_version_id == version_id)
        ).scalars().all()
    assert chunks == []


def test_document_suspend_api_hides_chunks_and_invalidates_answer(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    scholar = auth_service.register(
        email="lifecycle-api-scholar@example.com",
        password="very-strong-password",
        display_name="Scholar",
    )
    _grant_role_directly(session_factory, scholar.user.id, "senior_scholar")
    _enroll_mfa(session_factory, scholar.user.id)
    _set_user_preferences(session_factory, scholar.user.id)
    task_id, version_id = _seed_draft_task(
        session_factory,
        created_by=scholar.user.id,
        assigned_to=scholar.user.id,
        review_level="initial",
        document_status="scholar_approved",
        version_status="scholar_approved",
    )
    _seed_api_approval(
        session_factory,
        task_id=task_id,
        version_id=version_id,
        approver_id=scholar.user.id,
        level="initial",
        content_risk="routine",
    )
    published = _request(
        app,
        "POST",
        f"/documents/{version_id}/publish",
        json_body={"content_risk": "routine", "reason": "Publish for lifecycle test."},
        headers={"authorization": f"Bearer {scholar.tokens.access_token}"},
    )
    assert published["status"] == 200
    document_id = UUID(published["json"]["document_id"])
    answer_id = _seed_api_answer_for_version(session_factory, version_id=version_id)

    response = _request(
        app,
        "POST",
        f"/documents/{document_id}/suspend",
        json_body={"reason": "Post-publication issue.", "base_row_version": 2},
        headers={
            "authorization": f"Bearer {scholar.tokens.access_token}",
            "x-request-id": "trace-suspend-api",
        },
    )

    assert response["status"] == 200
    assert response["json"]["document_status"] == "suspended"
    assert response["json"]["current_published_version_id"] == str(version_id)
    assert response["json"]["affected_chunk_count"] == 1
    assert response["json"]["affected_answer_count"] == 1
    with session_factory() as session:
        chunk = session.execute(
            select(DocumentChunk).where(DocumentChunk.document_version_id == version_id)
        ).scalar_one()
        answer = session.get(Answer, answer_id)
        logs = session.execute(
            select(AuditLog).where(AuditLog.action == "documents.suspend")
        ).scalars().all()
    assert chunk.is_published is False
    assert answer is not None
    assert answer.invalidated_at is not None
    assert "suspended" in answer.answer_json["invalidation_warning"]
    assert any(log.trace_id == "trace-suspend-api" for log in logs)


def test_document_suspend_api_requires_archive_permission(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    reviewer = auth_service.register(
        email="lifecycle-api-reviewer@example.com",
        password="very-strong-password",
        display_name="Reviewer",
    )
    _grant_role_directly(session_factory, reviewer.user.id, "reviewer")
    _enroll_mfa(session_factory, reviewer.user.id)
    _set_user_preferences(session_factory, reviewer.user.id)

    response = _request(
        app,
        "POST",
        f"/documents/{uuid4()}/suspend",
        json_body={"reason": "Not allowed."},
        headers={"authorization": f"Bearer {reviewer.tokens.access_token}"},
    )

    assert response["status"] == 403
    assert response["json"]["error"]["code"] == "RBAC_FORBIDDEN"


def test_document_rollback_api_restores_previous_version(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    scholar = auth_service.register(
        email="lifecycle-api-rollback@example.com",
        password="very-strong-password",
        display_name="Scholar",
    )
    _grant_role_directly(session_factory, scholar.user.id, "senior_scholar")
    _enroll_mfa(session_factory, scholar.user.id)
    _set_user_preferences(session_factory, scholar.user.id)
    task_id, current_version_id = _seed_draft_task(
        session_factory,
        created_by=scholar.user.id,
        assigned_to=scholar.user.id,
        review_level="initial",
        document_status="scholar_approved",
        version_status="scholar_approved",
    )
    _seed_api_approval(
        session_factory,
        task_id=task_id,
        version_id=current_version_id,
        approver_id=scholar.user.id,
        level="initial",
        content_risk="routine",
    )
    old_version_id = _seed_api_previous_version_chunk(
        session_factory,
        current_version_id=current_version_id,
        actor_id=scholar.user.id,
    )
    published = _request(
        app,
        "POST",
        f"/documents/{current_version_id}/publish",
        json_body={"content_risk": "routine", "reason": "Publish for rollback."},
        headers={"authorization": f"Bearer {scholar.tokens.access_token}"},
    )
    assert published["status"] == 200
    document_id = UUID(published["json"]["document_id"])

    response = _request(
        app,
        "POST",
        f"/documents/{document_id}/rollback",
        json_body={
            "target_document_version_id": str(old_version_id),
            "reason": "Rollback after review.",
            "base_row_version": 2,
        },
        headers={"authorization": f"Bearer {scholar.tokens.access_token}"},
    )

    assert response["status"] == 200
    assert response["json"]["document_status"] == "published"
    assert response["json"]["previous_published_version_id"] == str(current_version_id)
    assert response["json"]["current_published_version_id"] == str(old_version_id)
    with session_factory() as session:
        old_chunk = session.execute(
            select(DocumentChunk).where(DocumentChunk.document_version_id == old_version_id)
        ).scalar_one()
        current_chunk = session.execute(
            select(DocumentChunk).where(DocumentChunk.document_version_id == current_version_id)
        ).scalar_one()
    assert old_chunk.is_published is True
    assert current_chunk.is_published is False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_draft_task(
    session_factory: sessionmaker[Session],
    *,
    created_by: UUID | None = None,
    assigned_to: UUID | None = None,
    review_level: str = "initial",
    document_status: str = "in_review",
    version_status: str = "parsed",
    embedding_permission: str = "allowed",
) -> tuple[UUID, UUID]:
    creator = created_by or uuid4()
    source_id = uuid4()
    license_id = uuid4()
    doc_id = uuid4()
    ver_id = uuid4()
    task_id = uuid4()
    uow = SQLAlchemyUnitOfWork(session_factory)
    with uow:
        uow.sources.create(
            Source(
                id=source_id,
                name="API Test Source",
                source_type="book",
                language="th",
                reliability_level=5,
                created_by=creator,
            )
        )
        uow.sources.add_license(
            SourceLicense(
                id=license_id,
                source_id=source_id,
                license_name="API Test License",
                license_version="2026-07",
                status="persistent_redistributable",
                storage_permission="allowed",
                embedding_permission=embedding_permission,
                commercial_use="allowed",
                redistribution="allowed",
                attribution_required=False,
                created_by=creator,
            )
        )
        uow.documents.create(
            Document(
                id=doc_id,
                source_id=source_id,
                source_license_id=license_id,
                canonical_id=f"doc-{uuid4().hex[:8]}",
                document_type="book",
                title="API Test Doc Title",
                author="API Author",
                language="th",
                madhhab="shafii",
                review_status=document_status,
                created_by=creator,
            )
        )
        uow.documents.add_version(
            DocumentVersion(
                id=ver_id,
                document_id=doc_id,
                version_number=1,
                status=version_status,
                content_hash="contenthash1",
                original_file_key="uploads/test1.txt",
                extracted_text="Old content lines",
                metadata_json={"filename": "test1.txt", "content_type": "text/plain"},
                created_by=creator,
            )
        )
        uow.commit()

    with session_factory() as session:
        session.add(
            ReviewTask(
                id=task_id,
                document_version_id=ver_id,
                document_id=doc_id,
                assigned_to=assigned_to,
                review_level=review_level,
                status="open",
                priority="normal",
                category="book",
                language="th",
                madhhab="shafii",
                created_by=creator,
            )
        )
        session.commit()
    return task_id, ver_id


def _seed_api_approval(
    session_factory: sessionmaker[Session],
    *,
    task_id: UUID,
    version_id: UUID,
    approver_id: UUID,
    level: str,
    content_risk: str = "sensitive",
) -> None:
    with session_factory() as session:
        session.add(
            ReviewApproval(
                id=uuid4(),
                document_version_id=version_id,
                review_task_id=task_id,
                approver_id=approver_id,
                approval_level=level,
                content_risk=content_risk,
                status="active",
                reason=f"{level} approval.",
            )
        )
        session.commit()


def _seed_api_answer_for_version(
    session_factory: sessionmaker[Session],
    *,
    version_id: UUID,
) -> UUID:
    with session_factory() as session:
        chunk = session.execute(
            select(DocumentChunk).where(DocumentChunk.document_version_id == version_id)
        ).scalar_one()
        citation_id = uuid4()
        session.add(
            Citation(
                id=citation_id,
                canonical_reference=chunk.reference or f"chunk-{chunk.id}",
                document_version_id=version_id,
                chunk_id=chunk.id,
                citation_type="book",
                display_title="API Test Doc Title",
                verified=True,
            )
        )
        run_id = uuid4()
        session.add(
            RetrievalRun(
                id=run_id,
                request_id=f"request-{uuid4().hex}",
                query_original="question",
                query_normalized="question",
                query_expansions={},
                filters={},
                retriever_version="test-retriever-v1",
                evidence_sufficient=True,
            )
        )
        session.add(
            RetrievalResult(
                id=uuid4(),
                retrieval_run_id=run_id,
                document_version_id=version_id,
                chunk_id=chunk.id,
                citation_id=citation_id,
                rank=1,
                score_final=1.0,
                metadata_json={},
            )
        )
        answer_id = uuid4()
        session.add(
            Answer(
                id=answer_id,
                message_id=uuid4(),
                retrieval_run_id=run_id,
                model_configuration_id=uuid4(),
                prompt_version_id=uuid4(),
                policy_version_id=uuid4(),
                risk_level="low",
                madhhab="shafii",
                answer_json={"text": "synthetic test answer"},
                confidence_level="high",
                evidence_sufficient=True,
            )
        )
        session.commit()
        return answer_id


def _seed_api_previous_version_chunk(
    session_factory: sessionmaker[Session],
    *,
    current_version_id: UUID,
    actor_id: UUID,
) -> UUID:
    with session_factory() as session:
        current = session.get(DocumentVersion, current_version_id)
        assert current is not None
        old_version_id = uuid4()
        session.add(
            DocumentVersion(
                id=old_version_id,
                document_id=current.document_id,
                version_number=0,
                status="scholar_approved",
                content_hash=f"old-{uuid4().hex}",
                extracted_text="Previous reviewed content",
                metadata_json={"review": {"status": "approved"}},
                created_by=actor_id,
            )
        )
        session.add(
            DocumentChunk(
                id=uuid4(),
                document_version_id=old_version_id,
                chunk_index=0,
                content="Previous reviewed content",
                content_normalized="Previous reviewed content",
                token_count=3,
                reference="old-version:chunk-1",
                metadata_json={"publishing_policy_version": "document-publish-v1"},
                is_published=False,
                chunking_strategy_version="publish-chunker-v1",
                content_hash=f"chunk-{uuid4().hex}",
            )
        )
        session.commit()
        return old_version_id


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


def _app(monkeypatch: Any) -> tuple[FastAPI, sessionmaker[Session]]:
    engine = create_engine(
        "sqlite:///file:zayd_review_api_tests?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://zayd_dev:zayd_dev@postgres:5432/zayd_dev")
    monkeypatch.setenv("AUTH_JWT_SECRET", "test-secret")
    monkeypatch.setattr(
        "zayd_service_api.app.S3ObjectStorage",
        lambda settings: FakeStorage(),
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
