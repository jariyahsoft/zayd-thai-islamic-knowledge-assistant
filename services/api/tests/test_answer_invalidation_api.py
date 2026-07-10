import asyncio

from httpx import ASGITransport, AsyncClient
from zayd_service_api import create_app


def test_answer_invalidation_routes_are_registered_and_protected(monkeypatch) -> None:
    monkeypatch.setattr("zayd_service_api.app.get_sessionmaker", lambda database_url: object())
    app = create_app()
    paths = {route.path for route in app.routes}
    assert "/admin/answers/{answer_id}/invalidate" in paths
    assert "/admin/answers/affected" in paths

    async def request() -> int:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            return (await client.get("/admin/answers/affected")).status_code

    assert asyncio.run(request()) == 401
