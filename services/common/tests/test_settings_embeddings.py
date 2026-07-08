import os
from unittest.mock import patch

import pytest
from zayd_common.settings import EnvironmentConfigurationError, ServiceSettings


def test_runtime_settings_parse_embedding_configuration() -> None:
    with patch.dict(
        os.environ,
        {
            "ENABLE_EXTERNAL_PROVIDERS": "true",
            "EMBEDDING_PROVIDER": "openai_compatible",
            "EMBEDDING_BASE_URL": "https://embeddings.example.com/v1",
            "EMBEDDING_MODEL": "text-embedding-demo",
            "EMBEDDING_REVISION": "2026-07",
            "EMBEDDING_DIMENSIONS": "384",
            "EMBEDDING_BATCH_SIZE": "24",
            "EMBEDDING_TIMEOUT_SECONDS": "11",
            "EMBEDDING_MAX_RETRIES": "2",
        },
        clear=False,
    ):
        settings = ServiceSettings.from_runtime_env(app_name="retrieval")

    assert settings.embedding_provider == "openai_compatible"
    assert settings.embedding_base_url == "https://embeddings.example.com/v1"
    assert settings.embedding_model == "text-embedding-demo"
    assert settings.embedding_revision == "2026-07"
    assert settings.embedding_dimensions == 384
    assert settings.embedding_batch_size == 24
    assert settings.embedding_timeout_seconds == 11
    assert settings.embedding_max_retries == 2


def test_runtime_settings_require_embedding_base_url_for_openai_mode() -> None:
    with patch.dict(
        os.environ,
        {
            "ENABLE_EXTERNAL_PROVIDERS": "true",
            "EMBEDDING_PROVIDER": "openai_compatible",
            "EMBEDDING_MODEL": "text-embedding-demo",
            "EMBEDDING_BASE_URL": "",
        },
        clear=False,
    ):
        with pytest.raises(EnvironmentConfigurationError, match="EMBEDDING_BASE_URL"):
            ServiceSettings.from_runtime_env(app_name="retrieval")
