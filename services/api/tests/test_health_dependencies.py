from __future__ import annotations

import asyncio

from httpx import ASGITransport, AsyncClient
from zayd_service_api import create_app


def test_dependency_health_reports_each_dependency_without_endpoint_details(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AUTH_JWT_SECRET", "test-jwt-secret")
    monkeypatch.setenv("AUTH_SESSION_SECRET", "test-session-secret")
    statuses = iter(("ok", "ok", "unavailable", "ok"))
    monkeypatch.setattr("zayd_service_api.app._tcp_dependency_status", lambda _url: next(statuses))
    app = create_app()

    async def request() -> tuple[int, dict[str, object]]:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            response = await client.get("/health/dependencies")
            return response.status_code, response.json()

    status_code, payload = asyncio.run(request())
    assert status_code == 200
    assert payload == {
        "service": "api",
        "status": "degraded",
        "dependencies": {
            "database": {"status": "ok"},
            "redis": {"status": "ok"},
            "object_storage": {"status": "unavailable"},
            "llm_provider": {"status": "ok"},
        },
    }
    assert "postgres" not in str(payload) and "minio" not in str(payload)
