"""Integration tests for Source API endpoints."""

from zayd_service_api import create_app


def test_source_routes_are_registered(monkeypatch) -> None:
    monkeypatch.setattr("zayd_service_api.app.get_sessionmaker", lambda database_url: object())
    app = create_app()

    route_paths = {route.path for route in app.routes}
    assert "/admin/sources" in route_paths
    assert "/admin/sources/{source_id}" in route_paths


def test_source_openapi_documents_error_responses(monkeypatch) -> None:
    monkeypatch.setattr("zayd_service_api.app.get_sessionmaker", lambda database_url: object())
    schema = create_app().openapi()

    assert schema["paths"]["/admin/sources"]["post"]["responses"]["201"]
    assert schema["paths"]["/admin/sources"]["get"]["responses"]["200"]
    assert schema["paths"]["/admin/sources/{source_id}"]["get"]["responses"]["200"]
    assert schema["paths"]["/admin/sources/{source_id}"]["patch"]["responses"]["200"]
    assert schema["paths"]["/admin/sources/{source_id}/suspend"]["post"]["responses"]["200"]
    assert schema["components"]["schemas"]["SourceCreateRequest"]
    assert schema["components"]["schemas"]["SourceUpdateRequest"]
    assert schema["components"]["schemas"]["SourceResponse"]
    assert schema["components"]["schemas"]["SourceListResponse"]
