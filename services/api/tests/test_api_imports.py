from zayd_service_api import create_app


def test_api_service_imports() -> None:
    app = create_app()
    assert app.title == "Zayd api service"
