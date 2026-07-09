from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from zayd_common.database.models import Base, Source
from zayd_common.database.unit_of_work import SQLAlchemyUnitOfWork
from zayd_service_api import create_app
from zayd_service_orchestrator.citation_registry import (
    CitationRegistrationRequest,
    CitationRegistryService,
    CitationType,
    citation_token,
)


def test_citation_routes_are_registered(monkeypatch) -> None:
    monkeypatch.setattr("zayd_service_api.app.get_sessionmaker", lambda database_url: object())
    app = create_app()
    route_paths = {route.path for route in app.routes}
    assert "/citations/{citation_id}" in route_paths
    assert "/sources/{source_id}" in route_paths


def test_get_citation_detail_returns_metadata_and_warnings(monkeypatch) -> None:
    app, session_factory, citation_id, source_id = _app_with_registered_citation(
        monkeypatch,
        db_name="zayd_citations_api_detail",
    )
    with session_factory() as session:
        source = session.get(Source, source_id)
        assert source is not None
        source.is_active = False
        session.commit()

    response = _request(app, "GET", f"/citations/{citation_token(citation_id)}")
    assert response["status"] == 200
    payload = response["json"]
    assert payload["citation"]["citation_type"] == "quran"
    assert payload["citation"]["arabic_text"] == "بِسْمِ اللَّهِ"
    assert payload["source_text"] == "reviewed citation content"
    assert "source_suspended" in payload["warnings"]


def test_get_citation_detail_not_found(monkeypatch) -> None:
    app, _session_factory, _citation_id, _source_id = _app_with_registered_citation(
        monkeypatch,
        db_name="zayd_citations_api_not_found",
    )
    response = _request(app, "GET", f"/citations/{uuid4()}")
    assert response["status"] == 404
    assert response["json"]["error"]["code"] == "CITATION_NOT_REGISTERED"


def test_get_public_source_detail_returns_warning_when_suspended(monkeypatch) -> None:
    app, session_factory, _citation_id, source_id = _app_with_registered_citation(
        monkeypatch,
        db_name="zayd_citations_api_source_warning",
    )
    with session_factory() as session:
        source = session.get(Source, source_id)
        assert source is not None
        source.is_active = False
        session.commit()

    response = _request(app, "GET", f"/sources/{source_id}")
    assert response["status"] == 200
    assert response["json"]["source"]["is_active"] is False
    assert response["json"]["warnings"] == ["source_suspended"]


def _app_with_registered_citation(
    monkeypatch,
    *,
    db_name: str = "zayd_citations_api",
) -> tuple[FastAPI, sessionmaker[Session], Any, Any]:
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

    fixture = _bootstrap_registry_fixture(session_factory)
    registered = fixture["service"].register_citation(
        CitationRegistrationRequest(
            document_version_id=fixture["version_id"],
            chunk_id=fixture["chunk_id"],
            citation_type=CitationType.QURAN,
            canonical_reference="quran:1:1",
            display_title="Al-Fatihah 1:1",
            actor_user_id=fixture["actor_id"],
            arabic_text="بِسْمِ اللَّهِ",
            thai_translation="ด้วยพระนามของอัลลอฮฺ",
            volume="1",
            page="1",
            trace_id="trace-citation-api",
        )
    )
    return create_app(), session_factory, registered.citation.id, fixture["source_id"]


def _bootstrap_registry_fixture(session_factory: sessionmaker[Session]) -> dict[str, Any]:
    from zayd_common.database.models import (
        Document,
        DocumentChunk,
        DocumentVersion,
        SourceLicense,
        User,
    )

    actor_id = uuid4()
    email_suffix = uuid4().hex[:8]
    source_id = uuid4()
    license_id = uuid4()
    document_id = uuid4()
    version_id = uuid4()
    chunk_id = uuid4()

    with session_factory() as session:
        session.add(
            User(
                id=actor_id,
                email=f"citation-api-{email_suffix}@example.test",
                display_name="Citation API",
            )
        )
        session.add(
            Source(
                id=source_id,
                name="Reviewed Source",
                source_type="fiqh",
                language="th",
                reliability_level=5,
                created_by=actor_id,
            )
        )
        session.add(
            SourceLicense(
                id=license_id,
                source_id=source_id,
                license_name="Reviewed License",
                status="persistent_redistributable",
                storage_permission="allowed",
                embedding_permission="allowed",
                commercial_use="allowed",
                redistribution="allowed",
                created_by=actor_id,
            )
        )
        session.add(
            Document(
                id=document_id,
                source_id=source_id,
                source_license_id=license_id,
                canonical_id="doc:reviewed",
                document_type="book",
                title="Reviewed Book",
                language="th",
                review_status="approved",
                created_by=actor_id,
            )
        )
        session.add(
            DocumentVersion(
                id=version_id,
                document_id=document_id,
                version_number=1,
                status="published",
                content_hash="version-hash",
                metadata_json={},
                created_by=actor_id,
            )
        )
        session.add(
            DocumentChunk(
                id=chunk_id,
                document_version_id=version_id,
                chunk_index=0,
                content="reviewed citation content",
                content_normalized="reviewed citation content",
                token_count=3,
                reference="quran:1:1",
                metadata_json={"citation": {"canonical_reference": "quran:1:1"}},
                is_published=True,
                chunking_strategy_version="test-v1",
                content_hash="chunk-hash-0",
            )
        )
        session.commit()

    service = CitationRegistryService(SQLAlchemyUnitOfWork(session_factory))
    return {
        "service": service,
        "actor_id": actor_id,
        "source_id": source_id,
        "version_id": version_id,
        "chunk_id": chunk_id,
    }


def _request(
    app: FastAPI,
    method: str,
    path: str,
) -> dict[str, Any]:
    async def run() -> dict[str, Any]:
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.request(method, path)
            body: Any
            try:
                body = response.json()
            except Exception:
                body = None
            return {
                "status": response.status_code,
                "json": body,
                "headers": dict(response.headers),
            }

    import asyncio

    return asyncio.run(run())