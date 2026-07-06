from zayd_service_retrieval import get_health


def test_retrieval_imports() -> None:
    assert get_health().service == "retrieval"
