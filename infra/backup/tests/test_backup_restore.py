from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BACKUP = ROOT / "infra/backup/backup.sh"
RESTORE = ROOT / "infra/backup/restore.sh"


def executable(path: Path, body: str) -> None:
    path.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def mock_tools(directory: Path) -> None:
    executable(
        directory / "pg_dump",
        'for value in "$@"; do\n'
        '  case "$value" in --file=*) printf "db" > "${value#--file=}";; esac\n'
        "done\n",
    )
    executable(directory / "pg_dumpall", 'printf "CREATE ROLE restored;\\n"\n')
    executable(directory / "pg_restore", "exit 0\n")
    executable(directory / "psql", "exit 0\n")
    executable(
        directory / "aws",
        'if [[ "${1:-}" == s3 && "${2:-}" == sync && "${3:-}" == s3://* ]]; then\n'
        '  dest="${4}"\n'
        '  mkdir -p "$dest"\n'
        '  printf object >"$dest/object.bin"\n'
        "fi\n",
    )


def environment(tmp_path: Path) -> dict[str, str]:
    tools = tmp_path / "bin"
    tools.mkdir()
    mock_tools(tools)
    key = tmp_path / "key"
    key.write_text("test-only-long-backup-passphrase", encoding="utf-8")
    config = tmp_path / "policy"
    config.mkdir()
    (config / "policy.txt").write_text("reviewed", encoding="utf-8")
    return {
        **os.environ,
        "PATH": f"{tools}:{os.environ['PATH']}",
        "BACKUP_ROOT": str(tmp_path / "backups"),
        "BACKUP_ENCRYPTION_KEY_FILE": str(key),
        "BACKUP_CONFIG_PATHS": str(config),
        "DATABASE_URL": "postgresql://test/isolated",
        "S3_BUCKET": "source-private",
    }


def create_backup(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    env = environment(tmp_path)
    result = subprocess.run([BACKUP], env=env, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    artifacts = list((tmp_path / "backups").glob("*.tar.gpg"))
    assert len(artifacts) == 1
    assert artifacts[0].with_suffix(artifacts[0].suffix + ".sha256").is_file()
    return artifacts[0], env


def test_encrypted_backup_and_isolated_restore_drill(tmp_path: Path) -> None:
    artifact, env = create_backup(tmp_path)
    env.update(
        RESTORE_ENVIRONMENT="isolated",
        RESTORE_DATABASE_URL="postgresql://test/restore",
        RESTORE_S3_BUCKET="restore-private",
    )
    result = subprocess.run(
        [RESTORE, artifact], env=env, text=True, capture_output=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert "restore_completed" in result.stdout
    audit = (tmp_path / "backups/audit/operations.jsonl").read_text(encoding="utf-8")
    assert '"operation":"backup","status":"completed"' in audit
    assert '"operation":"restore","status":"completed"' in audit


def test_restore_rejects_corrupt_artifact(tmp_path: Path) -> None:
    artifact, env = create_backup(tmp_path)
    artifact.write_bytes(artifact.read_bytes() + b"corruption")
    env.update(
        RESTORE_ENVIRONMENT="isolated",
        RESTORE_DATABASE_URL="postgresql://test/restore",
        RESTORE_S3_BUCKET="restore-private",
    )
    result = subprocess.run(
        [RESTORE, artifact], env=env, text=True, capture_output=True, check=False
    )
    assert result.returncode != 0
    assert "artifact_corrupt" in result.stderr


def test_restore_fails_closed_outside_isolated_environment(tmp_path: Path) -> None:
    artifact, env = create_backup(tmp_path)
    result = subprocess.run(
        [RESTORE, artifact], env=env, text=True, capture_output=True, check=False
    )
    assert result.returncode != 0
    assert "restore_not_isolated" in result.stderr
