from zayd_service_evaluation import get_health


def test_evaluation_imports() -> None:
    assert get_health().service == "evaluation"
