from zayd_service_ingestion import get_health


def test_ingestion_imports() -> None:
    assert get_health().service == "ingestion"
