import asyncio

from httpx import ASGITransport, AsyncClient
from zayd_service_api import create_app


def test_incident_routes_registered_and_protected(monkeypatch) -> None:
    monkeypatch.setattr("zayd_service_api.app.get_sessionmaker", lambda database_url: object())
    app = create_app()
    paths = {route.path for route in app.routes}
    assert "/admin/incidents" in paths
    assert "/admin/incidents/{incident_id}/transition" in paths
    assert "/admin/incidents/{incident_id}/owner" in paths
    assert "/admin/incidents/{incident_id}/timeline" in paths

    async def request() -> int:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            return (await client.post("/admin/incidents", json={})).status_code

    assert asyncio.run(request()) == 401
