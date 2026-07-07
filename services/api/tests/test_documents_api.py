"""Contract and integration tests for the document upload API."""

import asyncio
import base64
import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from zayd_common.auth import AuthService
from zayd_common.database.models import AuditLog, Base, Role, UserRole
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_common.licenses import LicenseCreate, LicenseService
from zayd_common.mfa import MfaService, generate_totp
from zayd_common.sources import SourceService
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


def test_document_routes_are_registered(monkeypatch) -> None:
    monkeypatch.setattr("zayd_service_api.app.get_sessionmaker", lambda database_url: object())
    monkeypatch.setattr(
        "zayd_service_api.app.S3ObjectStorage",
        lambda settings: FakeStorage(uploaded={}),
    )
    app = create_app()

    route_paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert "/documents" in route_paths


def test_document_openapi_documents_contract(monkeypatch) -> None:
    monkeypatch.setattr("zayd_service_api.app.get_sessionmaker", lambda database_url: object())
    monkeypatch.setattr(
        "zayd_service_api.app.S3ObjectStorage",
        lambda settings: FakeStorage(uploaded={}),
    )
    schema = create_app().openapi()

    assert schema["paths"]["/documents"]["post"]["responses"]["201"]
    assert schema["components"]["schemas"]["DocumentUploadRequestModel"]
    assert schema["components"]["schemas"]["DocumentUploadResponse"]
    assert schema["components"]["schemas"]["DocumentUploadDuplicateResponse"]
    assert schema["components"]["schemas"]["SignedUrlResponse"]


def test_document_upload_requires_permission(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    actor = auth_service.register(
        email="user@example.com",
        password="very-strong-password",
        display_name="User",
    )
    source_id, license_id = _seed_source_and_license(session_factory, actor.user.id)

    response = _request(
        app,
        "POST",
        "/documents",
        json_body=_payload(source_id, license_id),
        headers={"authorization": f"Bearer {actor.tokens.access_token}"},
    )

    assert response["status"] == 403
    assert response["json"]["error"]["code"] == "RBAC_FORBIDDEN"


def test_document_upload_success(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    actor = auth_service.register(
        email="operator@example.com",
        password="very-strong-password",
        display_name="Operator",
    )
    _grant_role_directly(session_factory, actor.user.id, "data_operator")
    _enroll_mfa(session_factory, actor.user.id)
    source_id, license_id = _seed_source_and_license(session_factory, actor.user.id)

    response = _request(
        app,
        "POST",
        "/documents",
        json_body=_payload(source_id, license_id),
        headers={
            "authorization": f"Bearer {actor.tokens.access_token}",
            "x-request-id": "trace-document-upload-api",
        },
    )

    assert response["status"] == 201
    assert response["json"]["upload_status"] == "accepted"
    assert response["json"]["duplicate"] is None
    assert response["json"]["content_hash"]
    with session_factory() as session:
        logs = session.execute(select(AuditLog)).scalars().all()
    assert any(
        log.action == "documents.upload.register" and log.trace_id == "trace-document-upload-api"
        for log in logs
    )


def test_document_upload_duplicate_returns_safe_result(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    actor = auth_service.register(
        email="duplicate@example.com",
        password="very-strong-password",
        display_name="Operator",
    )
    _grant_role_directly(session_factory, actor.user.id, "data_operator")
    _enroll_mfa(session_factory, actor.user.id)
    source_id, license_id = _seed_source_and_license(session_factory, actor.user.id)

    first = _request(
        app,
        "POST",
        "/documents",
        json_body=_payload(source_id, license_id),
        headers={"authorization": f"Bearer {actor.tokens.access_token}"},
    )
    second = _request(
        app,
        "POST",
        "/documents",
        json_body=_payload(source_id, license_id, canonical_id="doc-002", title="Duplicate"),
        headers={"authorization": f"Bearer {actor.tokens.access_token}"},
    )

    assert first["status"] == 201
    assert second["status"] == 201
    assert second["json"]["upload_status"] == "duplicate"
    assert second["json"]["duplicate"]["document_id"] == first["json"]["document_id"]


def test_document_upload_rejects_malformed_payload(monkeypatch) -> None:
    app, session_factory = _app(monkeypatch)
    auth_service = AuthService(SQLAlchemyUnitOfWork(session_factory), signing_secret="test-secret")
    actor = auth_service.register(
        email="badpayload@example.com",
        password="very-strong-password",
        display_name="Operator",
    )
    _grant_role_directly(session_factory, actor.user.id, "data_operator")
    _enroll_mfa(session_factory, actor.user.id)
    source_id, license_id = _seed_source_and_license(session_factory, actor.user.id)

    response = _request(
        app,
        "POST",
        "/documents",
        json_body=_payload(source_id, license_id, file_base64="not-base64%%%"),
        headers={"authorization": f"Bearer {actor.tokens.access_token}"},
    )

    assert response["status"] == 400
    assert response["json"]["error"]["code"] == "DOCUMENT_INVALID_FILE_PAYLOAD"


def _app(monkeypatch) -> tuple[FastAPI, sessionmaker[Session]]:
    engine = create_engine(
        "sqlite:///file:zayd_documents_api_tests?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://zayd_dev:zayd_dev@postgres:5432/zayd_dev")
    monkeypatch.setenv("AUTH_JWT_SECRET", "test-secret")
    monkeypatch.setattr(
        "zayd_service_api.app.S3ObjectStorage",
        lambda settings: FakeStorage(uploaded={}),
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


def _seed_source_and_license(
    session_factory: sessionmaker[Session], actor_user_id: Any
) -> tuple[Any, Any]:
    source_service = SourceService(SQLAlchemyUnitOfWork(session_factory))
    license_service = LicenseService(SQLAlchemyUnitOfWork(session_factory))
    source = source_service.create(
        name="Upload Source",
        source_type="book",
        language="th",
        reliability_level=4,
        is_active=True,
        created_by=actor_user_id,
    )
    license_record = license_service.create(
        source_id=source.id,
        data=LicenseCreate(
            license_name="Upload Agreement",
            license_version="2026-01",
            status="persistent_private",
            storage_permission="allowed",
            embedding_permission="allowed",
            commercial_use="conditional",
            redistribution="prohibited",
            attribution_required=True,
            attribution_template="Required attribution.",
            permission_document_key="private/licenses/upload.pdf",
            valid_from=None,
            valid_until=None,
            notes=None,
        ),
        created_by=actor_user_id,
    )
    return source.id, license_record.id


def _payload(source_id: Any, license_id: Any, **overrides: object) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "source_id": str(source_id),
        "source_license_id": str(license_id),
        "canonical_id": "doc-001",
        "document_type": "book",
        "title": "Upload Title",
        "language": "th",
        "filename": "upload.pdf",
        "content_type": "application/pdf",
        "file_base64": base64.b64encode(b"demo content").decode("ascii"),
        "author": "Author",
        "translator": None,
        "publisher": None,
        "edition": None,
        "madhhab": "unknown",
    }
    payload.update(overrides)
    return payload


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
