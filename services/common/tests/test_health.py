from zayd_common.health import HealthStatus


def test_health_status_defaults() -> None:
    status = HealthStatus(service="api")
    assert status.status == "ok"
