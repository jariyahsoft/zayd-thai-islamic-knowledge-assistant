import os
from hashlib import sha256
from unittest.mock import patch

import pytest
from pydantic import SecretStr
from zayd_common.settings import EnvironmentConfigurationError, ServiceSettings, mask_secret


def test_settings_validation() -> None:
    settings = ServiceSettings(app_name="api")
    assert settings.app_name == "api"
    assert settings.environment == "local"


def test_secret_redaction() -> None:
    settings = ServiceSettings(
        app_name="api",
        provider_token=SecretStr("super-secret"),
    )
    dumped = repr(settings)
    assert "super-secret" not in dumped
    assert "**********" in dumped


def test_runtime_settings_missing_required_value() -> None:
    with patch.dict(os.environ, {"APP_URL": ""}, clear=False):
        with pytest.raises(EnvironmentConfigurationError, match="APP_URL is required"):
            ServiceSettings.from_runtime_env(app_name="api")


def test_runtime_settings_invalid_provider() -> None:
    with patch.dict(os.environ, {"LLM_PROVIDER": "invalid-provider"}, clear=False):
        with pytest.raises(
            EnvironmentConfigurationError,
            match="llm_provider",
        ):
            ServiceSettings.from_runtime_env(app_name="api")


def test_runtime_settings_invalid_url() -> None:
    with patch.dict(os.environ, {"DATABASE_URL": "not-a-url"}, clear=False):
        with pytest.raises(
            EnvironmentConfigurationError,
            match="database_url",
        ):
            ServiceSettings.from_runtime_env(app_name="api")


def test_mask_secret_helper() -> None:
    masked = mask_secret("super-secret-value")
    assert "super-secret-value" not in masked
    assert "[redacted]" in masked


def test_production_rejects_development_credentials() -> None:
    with patch.dict(
        os.environ,
        {
            "APP_ENV": "production",
            "AUTH_JWT_SECRET": "dev-jwt-secret-change-me",
            "AUTH_SESSION_SECRET": "dev-session-secret-change-me",
        },
        clear=False,
    ):
        with pytest.raises(
            EnvironmentConfigurationError,
            match="development placeholder",
        ):
            ServiceSettings.from_runtime_env(app_name="api")


def test_pilot_mode_requires_hashed_allowlist_and_disables_guests() -> None:
    invite_hash = sha256(b"pilot@example.test").hexdigest()
    settings = ServiceSettings(
        app_name="api",
        pilot_mode=True,
        enable_guest_mode=False,
        pilot_invite_email_hashes=SecretStr(invite_hash),
        pilot_invite_allowlist_version="pilot-invites-v1",
    )
    assert settings.pilot_invite_hashes() == frozenset({invite_hash})
    with pytest.raises(ValueError, match="ENABLE_GUEST_MODE"):
        ServiceSettings(
            app_name="api",
            pilot_mode=True,
            enable_guest_mode=True,
            pilot_invite_email_hashes=SecretStr(invite_hash),
            pilot_invite_allowlist_version="pilot-invites-v1",
        )
