from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
COMPOSE = ROOT / "infra/compose/minimal.yml"
SCRIPT = ROOT / "scripts/self-host.sh"


def test_minimal_profile_has_required_services_and_private_stateful_network() -> None:
    text = COMPOSE.read_text(encoding="utf-8")
    for service in ("web", "api", "worker", "postgres", "redis", "minio"):
        assert f"  {service}:\n" in text
    assert 'profiles: ["local-ai"]' in text
    assert text.count("ports:") == 2
    assert "internal: true" in text
    assert '"${API_BIND_ADDRESS:-127.0.0.1}:${API_PORT:-8000}:8000"' in text


def test_local_provider_path_has_no_required_proprietary_key() -> None:
    text = COMPOSE.read_text(encoding="utf-8")
    assert "LLM_BASE_URL: ${LLM_BASE_URL:-http://ollama:11434}" in text
    assert "LLM_API_KEY: ${LLM_API_KEY:-}" in text
    assert "ENABLE_EXTERNAL_PROVIDERS: ${ENABLE_EXTERNAL_PROVIDERS:-false}" in text


def test_init_generates_restrictive_environment_and_upgrade_commands(tmp_path: Path) -> None:
    if shutil.which("docker") is None or shutil.which("openssl") is None:
        pytest.skip("Docker and OpenSSL are required for the Ubuntu self-host smoke test")
    env_file = tmp_path / ".env.self-host"
    result = subprocess.run(
        [SCRIPT, "init"],
        env={**os.environ, "SELF_HOST_ENV_FILE": str(env_file)},
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    content = env_file.read_text(encoding="utf-8")
    assert "GENERATE_ON_SETUP" not in content
    assert stat.S_IMODE(env_file.stat().st_mode) == 0o600
    script = SCRIPT.read_text(encoding="utf-8")
    assert "scripts/migrate.sh" in script
    assert "seed-admin" in script and "seed-demo" in script
    assert "upgrade)" in script and "--remove-orphans" in script


def test_compose_configuration_validates_with_generated_values(tmp_path: Path) -> None:
    if shutil.which("docker") is None:
        pytest.skip("Docker Compose is unavailable")
    env_file = tmp_path / "self-host.env"
    env_file.write_text(
        "\n".join(
            (
                "POSTGRES_PASSWORD=test-only-database-secret",
                "MINIO_ROOT_PASSWORD=test-only-storage-secret",
                "AUTH_JWT_SECRET=test-only-jwt-secret-with-enough-entropy",
                "AUTH_SESSION_SECRET=test-only-session-secret-with-enough-entropy",
            )
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        ["docker", "compose", "--env-file", env_file, "-f", COMPOSE, "config", "--quiet"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
