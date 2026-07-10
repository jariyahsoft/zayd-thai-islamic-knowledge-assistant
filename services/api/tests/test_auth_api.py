from zayd_service_api import create_app


def test_auth_routes_are_registered(monkeypatch) -> None:
    monkeypatch.setattr("zayd_service_api.app.get_sessionmaker", lambda database_url: object())
    app = create_app()

    route_paths = {route.path for route in app.routes}
    assert "/auth/register" in route_paths
    assert "/auth/login" in route_paths
    assert "/auth/refresh" in route_paths
    assert "/auth/logout" in route_paths
    assert "/auth/password-reset/request" in route_paths
    assert "/auth/password-reset/confirm" in route_paths
    assert "/auth/sessions/revoke-all" in route_paths
    assert "/auth/me" in route_paths
    assert "/admin/rbac/bootstrap" in route_paths
    assert "/admin/users" in route_paths
    assert "/admin/users/{user_id}/status" in route_paths
    assert "/admin/users/{user_id}/sessions/revoke" in route_paths
    assert "/admin/users/roles/grant" in route_paths
    assert "/admin/users/roles/revoke" in route_paths
    assert "/admin/providers" in route_paths
    assert "/admin/providers/{provider_id}/test-connection" in route_paths
    assert "/admin/models" in route_paths
    assert "/authorization/documents/approve" in route_paths


def test_auth_openapi_documents_error_responses(monkeypatch) -> None:
    monkeypatch.setattr("zayd_service_api.app.get_sessionmaker", lambda database_url: object())
    schema = create_app().openapi()

    assert schema["paths"]["/auth/login"]["post"]["responses"]["200"]
    assert schema["paths"]["/auth/me"]["get"]["responses"]["200"]
    assert schema["paths"]["/admin/users"]["get"]["responses"]["200"]
    assert schema["paths"]["/admin/users/roles/grant"]["post"]["responses"]["200"]
    assert schema["paths"]["/admin/providers"]["post"]["responses"]["201"]
    assert schema["paths"]["/admin/models"]["post"]["responses"]["201"]
    assert schema["paths"]["/authorization/documents/approve"]["post"]["responses"]["200"]
    assert schema["components"]["schemas"]["AuthResponse"]
    assert schema["components"]["schemas"]["TokenResponse"]
    assert schema["components"]["schemas"]["PrincipalResponse"]
    assert schema["components"]["schemas"]["RoleAssignmentRequest"]
    assert schema["components"]["schemas"]["ProviderResponse"]
    assert schema["components"]["schemas"]["AdminUserResponse"]
