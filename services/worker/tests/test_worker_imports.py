from zayd_service_worker import get_health


def test_worker_imports() -> None:
    assert get_health().service == "worker"
