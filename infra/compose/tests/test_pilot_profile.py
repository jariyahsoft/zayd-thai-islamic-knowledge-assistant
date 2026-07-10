from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[3]
PRODUCTION = ROOT / "infra/compose/production.yml"
PILOT = ROOT / "infra/compose/pilot.yml"
VALIDATOR = ROOT / "infra/scripts/validate-pilot-environment.sh"


def _environment(manifest: Path) -> dict[str, str]:
    environment = {
        **os.environ,
        "APP_URL": "https://production.example.test",
        "S3_ENDPOINT": "https://production-objects.example.test",
        "S3_REGION": "production-region-1",
        "S3_BUCKET": "production-private",
        "LLM_PROVIDER": "openai_compatible",
        "LLM_BASE_URL": "https://models.example.test/v1",
        "LLM_MODEL": "reviewed-model",
        "EMBEDDING_PROVIDER": "openai_compatible",
        "EMBEDDING_BASE_URL": "https://embeddings.example.test/v1",
        "EMBEDDING_MODEL": "reviewed-embedding",
        "ENABLE_EXTERNAL_PROVIDERS": "true",
        "ALLOWED_ORIGINS": "https://production.example.test",
        "IMAGE_REGISTRY": "registry.example.test/zayd",
        "IMAGE_TAG": "1.0.0-rc.1",
        "OFFSITE_S3_URI": "s3://production-offsite/backups",
        "PILOT_ENVIRONMENT_ID": "pilot-th-closed",
        "PILOT_APP_URL": "https://pilot.example.test",
        "PILOT_ALLOWED_ORIGINS": "https://pilot.example.test",
        "PILOT_S3_ENDPOINT": "https://pilot-objects.example.test",
        "PILOT_S3_REGION": "pilot-region-1",
        "PILOT_S3_BUCKET": "pilot-private",
        "PILOT_OFFSITE_S3_URI": "s3://pilot-offsite/backups",
        "PILOT_INVITE_ALLOWLIST_VERSION": "pilot-invites-v1",
        "PILOT_DATASET_MANIFEST": str(manifest),
        "PILOT_DATASET_SHA256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "PILOT_DATASET_APPROVAL_ID": "SCHOLAR-APPROVAL-001",
        "PILOT_PROMETHEUS_VOLUME": "pilot-prometheus-data",
        "PILOT_BACKUP_VOLUME": "pilot-backup-staging",
    }
    for name in (
        "DATABASE_URL",
        "REDIS_URL",
        "S3_ACCESS_KEY",
        "S3_SECRET_KEY",
        "AUTH_JWT",
        "AUTH_SESSION",
        "PROVIDER_TOKEN",
        "LLM_API_KEY",
        "EMBEDDING_API_KEY",
        "INVITE_EMAIL_HASHES",
        "BACKUP_ENCRYPTION_KEY",
        "TLS_CERTIFICATE",
        "TLS_PRIVATE_KEY",
    ):
        environment[f"PILOT_{name}_SECRET"] = f"pilot-{name.lower().replace('_', '-')}"
    return environment


def test_pilot_validator_and_profile_fail_closed_on_data_isolation_inputs(tmp_path: Path) -> None:
    manifest = tmp_path / "approved-manifest.json"
    manifest.write_text('{"approved": true}', encoding="utf-8")
    environment = _environment(manifest)
    validated = subprocess.run(
        [VALIDATOR], env=environment, text=True, capture_output=True, check=False
    )
    assert validated.returncode == 0, validated.stderr
    assert "dataset_approval=SCHOLAR-APPROVAL-001" in validated.stdout

    invalid = subprocess.run(
        [VALIDATOR],
        env={**environment, "PILOT_DATABASE_URL_SECRET": "production-database-url"},
        text=True,
        capture_output=True,
        check=False,
    )
    assert invalid.returncode != 0
    assert "secret_namespace_invalid" in invalid.stderr

    if shutil.which("docker") is None:
        pytest.skip("Docker Compose is unavailable")
    configured = subprocess.run(
        ["docker", "compose", "-f", PRODUCTION, "-f", PILOT, "config", "--quiet"],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert configured.returncode == 0, configured.stderr


def test_pilot_profile_forces_invite_only_and_uses_pilot_secret_names() -> None:
    text = PILOT.read_text(encoding="utf-8")
    assert 'PILOT_MODE: "true"' in text
    assert 'ENABLE_GUEST_MODE: "false"' in text
    assert "PILOT_INVITE_EMAIL_HASHES_FILE" in text
    assert text.count("PILOT_") >= 20
