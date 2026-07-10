from __future__ import annotations

import asyncio
from typing import Any

from fastapi import FastAPI
from zayd_common.telemetry import telemetry_registry
from zayd_service_api import create_app


def test_health_response_returns_request_and_trace_headers(monkeypatch) -> None:
    telemetry_registry.reset()
    monkeypatch.setenv("AUTH_JWT_SECRET", "test-secret")
    monkeypatch.setattr("zayd_service_api.app.get_sessionmaker", lambda database_url: object())
    app = create_app()

    response = _request(
        app,
        "GET",
        "/health",
        headers={"x-request-id": "incoming-request-1"},
    )

    assert response["status"] == 200
    assert response["headers"]["x-request-id"] == "incoming-request-1"
    assert response["headers"]["x-trace-id"] == "incoming-request-1"
    assert "api_request_total" in telemetry_registry.export_prometheus_text()


def test_health_response_generates_request_id_when_missing(monkeypatch) -> None:
    telemetry_registry.reset()
    monkeypatch.setenv("AUTH_JWT_SECRET", "test-secret")
    monkeypatch.setattr("zayd_service_api.app.get_sessionmaker", lambda database_url: object())
    app = create_app()

    response = _request(app, "GET", "/health")

    assert response["status"] == 200
    assert response["headers"]["x-request-id"].startswith("req-")
    assert response["headers"]["x-trace-id"] == response["headers"]["x-request-id"]


def _request(
    app: FastAPI,
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    async def run() -> dict[str, Any]:
        from httpx import ASGITransport, AsyncClient

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.request(method, path, headers=headers)
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

    return asyncio.run(run())
