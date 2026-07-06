from zayd_service_orchestrator import get_health


def test_orchestrator_imports() -> None:
    assert get_health().service == "orchestrator"
