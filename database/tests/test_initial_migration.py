# ruff: noqa: E501
from __future__ import annotations

import subprocess
import uuid
from collections.abc import Generator
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
UP_MIGRATION = ROOT / "database" / "migrations" / "0001_initial_core_domain.up.sql"
DOWN_MIGRATION = ROOT / "database" / "migrations" / "0001_initial_core_domain.down.sql"
DB_USER = "zayd_dev"
POSTGRES_SERVICE = "postgres"


def test_migration_files_are_deterministic_reversible_and_secret_free() -> None:
    up_sql = UP_MIGRATION.read_text(encoding="utf-8")
    down_sql = DOWN_MIGRATION.read_text(encoding="utf-8")

    for sql in (up_sql, down_sql):
        assert "BEGIN;" in sql
        assert "COMMIT;" in sql
        assert "CREATE DATABASE" not in sql.upper()
        assert "DROP DATABASE" not in sql.upper()
        assert "TELEGRAM" not in sql.upper()
        assert "BOT_TOKEN=" not in sql.upper()
        assert "CHAT_ID=" not in sql.upper()
        assert "API_KEY=" not in sql.upper()

    assert "INSERT INTO schema_migrations" in up_sql
    assert "DROP TABLE IF EXISTS schema_migrations" in down_sql
    assert "DROP TYPE IF EXISTS document_status" in down_sql
    assert "DROP FUNCTION IF EXISTS zayd_validate_embedding_record()" in down_sql


def run_compose_psql(database: str, sql: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            POSTGRES_SERVICE,
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            DB_USER,
            "-d",
            database,
        ],
        input=sql,
        text=True,
        cwd=ROOT,
        capture_output=True,
        check=False,
    )


def require_running_postgres() -> None:
    probe = run_compose_psql("postgres", "SELECT 1;")
    if probe.returncode != 0:
        pytest.skip("Docker Compose postgres service is not running")


@pytest.fixture()
def migration_database() -> Generator[str, None, None]:
    require_running_postgres()
    db_name = f"zayd_migration_test_{uuid.uuid4().hex[:12]}"
    create = run_compose_psql("postgres", f'CREATE DATABASE "{db_name}";')
    assert create.returncode == 0, create.stderr
    try:
        yield db_name
    finally:
        terminate = run_compose_psql(
            "postgres",
            "SELECT pg_terminate_backend(pid) "
            "FROM pg_stat_activity "
            f"WHERE datname = '{db_name}' AND pid <> pg_backend_pid();",
        )
        assert terminate.returncode == 0, terminate.stderr
        drop = run_compose_psql("postgres", f'DROP DATABASE IF EXISTS "{db_name}";')
        assert drop.returncode == 0, drop.stderr


def apply_migration(database: str, migration_file: Path) -> subprocess.CompletedProcess[str]:
    return run_compose_psql(database, migration_file.read_text(encoding="utf-8"))


def query_scalar(database: str, sql: str) -> str:
    result = run_compose_psql(database, f"\\pset tuples_only on\n\\pset format unaligned\n{sql}")
    assert result.returncode == 0, result.stderr
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    data_lines = [line for line in lines if not line.startswith("Output format")]
    assert data_lines, result.stdout
    return data_lines[-1]


def test_initial_migration_up_down_reup_from_empty_database(migration_database: str) -> None:
    up = apply_migration(migration_database, UP_MIGRATION)
    assert up.returncode == 0, up.stderr
    assert query_scalar(migration_database, "SELECT COUNT(*) FROM schema_migrations;") == "1"
    assert (
        query_scalar(migration_database, "SELECT to_regclass('public.auth_users') IS NOT NULL;")
        == "t"
    )

    down = apply_migration(migration_database, DOWN_MIGRATION)
    assert down.returncode == 0, down.stderr
    assert (
        query_scalar(migration_database, "SELECT to_regclass('public.auth_users') IS NULL;") == "t"
    )
    assert (
        query_scalar(migration_database, "SELECT to_regtype('public.document_status') IS NULL;")
        == "t"
    )

    reup = apply_migration(migration_database, UP_MIGRATION)
    assert reup.returncode == 0, reup.stderr
    assert (
        query_scalar(
            migration_database, "SELECT to_regclass('public.embedding_records') IS NOT NULL;"
        )
        == "t"
    )


def test_initial_migration_creates_required_constraints_and_indexes(
    migration_database: str,
) -> None:
    up = apply_migration(migration_database, UP_MIGRATION)
    assert up.returncode == 0, up.stderr

    expected_relations = {
        "auth_users",
        "source_licenses",
        "documents",
        "document_versions",
        "document_chunks",
        "embedding_records",
        "citations",
        "retrieval_results",
        "audit_logs",
        "evaluation_results",
    }
    relation_count = query_scalar(
        migration_database,
        "SELECT COUNT(*) "
        "FROM pg_class "
        "WHERE relkind = 'r' AND relnamespace = 'public'::regnamespace "
        f"AND relname = ANY(ARRAY{sorted(expected_relations)!r});",
    )
    assert relation_count == str(len(expected_relations))

    expected_indexes = {
        "uq_auth_users_email_active",
        "idx_review_tasks_queue",
        "idx_document_chunks_fts",
        "idx_embedding_records_vector",
        "idx_citations_reference",
        "idx_conversations_user_updated",
        "idx_audit_logs_resource",
        "idx_evaluation_runs_dataset_status",
    }
    index_count = query_scalar(
        migration_database,
        "SELECT COUNT(*) "
        "FROM pg_class "
        "WHERE relkind = 'i' AND relnamespace = 'public'::regnamespace "
        f"AND relname = ANY(ARRAY{sorted(expected_indexes)!r});",
    )
    assert index_count == str(len(expected_indexes))

    fk_count = int(
        query_scalar(
            migration_database,
            "SELECT COUNT(*) FROM pg_constraint WHERE contype = 'f';",
        )
    )
    assert fk_count >= 50


def test_initial_migration_success_path_and_embedding_failure_path(migration_database: str) -> None:
    up = apply_migration(migration_database, UP_MIGRATION)
    assert up.returncode == 0, up.stderr

    success_sql = """
    INSERT INTO auth_users (id, email, display_name)
    VALUES ('00000000-0000-0000-0000-000000000001', 'admin@example.test', 'Admin');

    INSERT INTO sources (id, name, source_type, language, reliability_level, created_by)
    VALUES ('00000000-0000-0000-0000-000000000101', 'Demo Source', 'book', 'th', 5, '00000000-0000-0000-0000-000000000001');

    INSERT INTO source_licenses (
      id, source_id, license_name, status, storage_permission, embedding_permission,
      commercial_use, redistribution, created_by
    ) VALUES (
      '00000000-0000-0000-0000-000000000201', '00000000-0000-0000-0000-000000000101', 'Demo License',
      'persistent_redistributable', 'allowed', 'allowed', 'allowed', 'allowed',
      '00000000-0000-0000-0000-000000000001'
    );

    INSERT INTO providers (id, name, provider_type, status, created_by)
    VALUES ('00000000-0000-0000-0000-000000000301', 'local-embedding', 'embedding', 'enabled', '00000000-0000-0000-0000-000000000001');

    INSERT INTO model_configurations (id, provider_id, model_name, model_type, status, created_by)
    VALUES (
      '00000000-0000-0000-0000-000000000401', '00000000-0000-0000-0000-000000000301',
      'local-embedding-1536', 'embedding', 'enabled', '00000000-0000-0000-0000-000000000001'
    );

    INSERT INTO documents (
      id, source_id, source_license_id, canonical_id, document_type, title, language, created_by
    ) VALUES (
      '00000000-0000-0000-0000-000000000501', '00000000-0000-0000-0000-000000000101',
      '00000000-0000-0000-0000-000000000201', 'demo-book', 'book', 'Demo Book', 'th',
      '00000000-0000-0000-0000-000000000001'
    );

    INSERT INTO document_versions (id, document_id, version_number, status, content_hash, created_by, frozen_at)
    VALUES (
      '00000000-0000-0000-0000-000000000601', '00000000-0000-0000-0000-000000000501',
      1, 'published', 'hash-v1', '00000000-0000-0000-0000-000000000001', now()
    );

    UPDATE documents
    SET review_status = 'published', published_version_id = '00000000-0000-0000-0000-000000000601'
    WHERE id = '00000000-0000-0000-0000-000000000501';

    INSERT INTO document_chunks (
      id, document_version_id, chunk_index, content, content_normalized, token_count,
      is_published, chunking_strategy_version, content_hash
    ) VALUES (
      '00000000-0000-0000-0000-000000000701', '00000000-0000-0000-0000-000000000601', 0,
      'demo content', 'demo content', 2, true, 'test-v1', 'chunk-hash-v1'
    );

    INSERT INTO citations (
      id, canonical_reference, document_version_id, chunk_id, citation_type, display_title, verified
    ) VALUES (
      '00000000-0000-0000-0000-000000000801', 'demo:1', '00000000-0000-0000-0000-000000000601',
      '00000000-0000-0000-0000-000000000701', 'book', 'Demo citation', true
    );

    INSERT INTO embedding_records (
      id, document_version_id, chunk_id, model_configuration_id, provider_id, embedding,
      embedding_hash, dimension, status
    ) VALUES (
      '00000000-0000-0000-0000-000000000901', '00000000-0000-0000-0000-000000000601',
      '00000000-0000-0000-0000-000000000701', '00000000-0000-0000-0000-000000000401',
      '00000000-0000-0000-0000-000000000301', array_fill(0.001::real, ARRAY[1536])::vector,
      'embedding-hash-v1', 1536, 'active'
    );
    """
    success = run_compose_psql(migration_database, success_sql)
    assert success.returncode == 0, success.stderr

    failure_sql = """
    INSERT INTO document_chunks (
      id, document_version_id, chunk_index, content, content_normalized, token_count,
      is_published, chunking_strategy_version, content_hash
    ) VALUES (
      '00000000-0000-0000-0000-000000000702', '00000000-0000-0000-0000-000000000601', 1,
      'draft content', 'draft content', 2, false, 'test-v1', 'chunk-hash-v2'
    );

    INSERT INTO embedding_records (
      id, document_version_id, chunk_id, model_configuration_id, provider_id, embedding,
      embedding_hash, dimension, status
    ) VALUES (
      '00000000-0000-0000-0000-000000000902', '00000000-0000-0000-0000-000000000601',
      '00000000-0000-0000-0000-000000000702', '00000000-0000-0000-0000-000000000401',
      '00000000-0000-0000-0000-000000000301', array_fill(0.001::real, ARRAY[1536])::vector,
      'embedding-hash-v2', 1536, 'active'
    );
    """
    failure = run_compose_psql(migration_database, failure_sql)
    assert failure.returncode != 0
    assert "Active embeddings require a published chunk" in failure.stderr
