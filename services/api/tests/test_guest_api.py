from zayd_service_api import create_app


def test_guest_routes_are_registered(monkeypatch) -> None:
    monkeypatch.setattr("zayd_service_api.app.get_sessionmaker", lambda database_url: object())
    app = create_app()

    route_paths = {route.path for route in app.routes}
    assert "/auth/guest/start" in route_paths
    assert "/auth/guest/convert" in route_paths


def test_guest_openapi_documents_error_responses(monkeypatch) -> None:
    monkeypatch.setattr("zayd_service_api.app.get_sessionmaker", lambda database_url: object())
    schema = create_app().openapi()

    assert schema["paths"]["/auth/guest/start"]["post"]["responses"]["200"]
    assert schema["components"]["schemas"]["GuestSessionResponse"]
    assert schema["components"]["schemas"]["GuestConversionRequest"]
