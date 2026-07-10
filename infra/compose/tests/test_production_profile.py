from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
COMPOSE = ROOT / "infra/compose/production.yml"
LOADER = ROOT / "infra/scripts/load-secrets-and-exec.sh"


def _production_environment() -> dict[str, str]:
    return {
        **os.environ,
        "APP_URL": "https://zayd.example.test",
        "S3_ENDPOINT": "https://objects.example.test",
        "S3_REGION": "test-region-1",
        "S3_BUCKET": "zayd-private",
        "LLM_PROVIDER": "openai_compatible",
        "LLM_BASE_URL": "https://models.example.test/v1",
        "LLM_MODEL": "reviewed-model",
        "EMBEDDING_PROVIDER": "openai_compatible",
        "EMBEDDING_BASE_URL": "https://embeddings.example.test/v1",
        "EMBEDDING_MODEL": "reviewed-embedding",
        "ENABLE_EXTERNAL_PROVIDERS": "true",
        "ALLOWED_ORIGINS": "https://zayd.example.test",
        "IMAGE_REGISTRY": "registry.example.test/zayd",
        "IMAGE_TAG": "1.0.0-test",
        "OFFSITE_S3_URI": "s3://zayd-offsite-test/backups",
    }


def test_production_compose_validates() -> None:
    if shutil.which("docker") is None:
        pytest.skip("Docker Compose is unavailable")
    result = subprocess.run(
        ["docker", "compose", "-f", COMPOSE, "config", "--quiet"],
        env=_production_environment(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_replicas_probes_rollback_worker_isolation_and_external_state_are_explicit() -> None:
    text = COMPOSE.read_text(encoding="utf-8")
    assert "replicas: 3" in text and text.count("max_replicas_per_node: 1") >= 3
    assert "failure_action: rollback" in text and "order: start-first" in text
    assert text.count("healthcheck:") >= 4
    worker = text.split("  worker:\n", 1)[1].split("  monitoring:\n", 1)[0]
    assert "networks: [backend]" in worker and "edge" not in worker
    for stateful_service in ("postgres", "redis", "minio"):
        assert f"  {stateful_service}:\n" not in text
    assert "prometheus-data: {external: true}" in text
    assert "backup-staging: {external: true}" in text


def test_production_profile_has_no_embedded_credentials_or_floating_app_images() -> None:
    text = COMPOSE.read_text(encoding="utf-8")
    assert "password:" not in text.lower()
    assert "minioadmin" not in text and "change-me" not in text
    assert "IMAGE_TAG:?IMAGE_TAG is required" in text
    assert text.count("{external: true}") >= 12
    assert "_SECRET_FILE: /run/secrets/" in text
    assert "_API_KEY_FILE: /run/secrets/" in text


def test_secret_loader_fails_closed_and_loads_secret(tmp_path: Path) -> None:
    missing = subprocess.run(
        [LOADER, "true"],
        env={**os.environ, "AUTH_JWT_SECRET_FILE": str(tmp_path / "missing")},
        text=True,
        capture_output=True,
        check=False,
    )
    assert missing.returncode != 0
    assert "secret_unavailable" in missing.stderr

    secret = tmp_path / "secret"
    secret.write_text("test-only-value", encoding="utf-8")
    loaded = subprocess.run(
        [LOADER, "sh", "-c", 'test "$AUTH_JWT_SECRET" = test-only-value'],
        env={**os.environ, "AUTH_JWT_SECRET_FILE": str(secret)},
        text=True,
        capture_output=True,
        check=False,
    )
    assert loaded.returncode == 0, loaded.stderr
