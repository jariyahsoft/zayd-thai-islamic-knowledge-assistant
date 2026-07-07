"""Contract tests for License API endpoints."""

from zayd_service_api import create_app


def test_license_routes_are_registered(monkeypatch) -> None:
    monkeypatch.setattr("zayd_service_api.app.get_sessionmaker", lambda database_url: object())
    app = create_app()

    route_paths = {route.path for route in app.routes}
    assert "/admin/sources/{source_id}/licenses" in route_paths
    assert "/admin/licenses/{license_id}" in route_paths
    assert "/admin/licenses/{license_id}/replace" in route_paths
    assert "/admin/licenses/{license_id}/permission-document" in route_paths
    assert "/admin/licenses/{license_id}/publication-authorization" in route_paths
    assert "/admin/licenses/{license_id}/policy-decision" in route_paths


def test_license_openapi_documents_contract(monkeypatch) -> None:
    monkeypatch.setattr("zayd_service_api.app.get_sessionmaker", lambda database_url: object())
    schema = create_app().openapi()

    assert schema["paths"]["/admin/sources/{source_id}/licenses"]["post"]["responses"]["201"]
    assert schema["paths"]["/admin/sources/{source_id}/licenses"]["get"]["responses"]["200"]
    assert schema["paths"]["/admin/licenses/{license_id}"]["get"]["responses"]["200"]
    assert schema["paths"]["/admin/licenses/{license_id}/replace"]["post"]["responses"]["201"]
    assert schema["paths"]["/admin/licenses/{license_id}/permission-document"]["get"]["responses"][
        "200"
    ]
    assert schema["paths"]["/admin/licenses/{license_id}/publication-authorization"]["post"][
        "responses"
    ]["200"]
    assert schema["paths"]["/admin/licenses/{license_id}/policy-decision"]["get"]["responses"][
        "200"
    ]
    assert schema["components"]["schemas"]["LicenseCreateRequest"]
    assert schema["components"]["schemas"]["LicenseResponse"]
    assert schema["components"]["schemas"]["LicenseListResponse"]
    assert schema["components"]["schemas"]["PermissionDocumentResponse"]
    assert schema["components"]["schemas"]["PublicationAuthorizationResponse"]
    assert schema["components"]["schemas"]["LicensePolicyActionResponse"]
    assert schema["components"]["schemas"]["LicensePolicyDecisionResponse"]
