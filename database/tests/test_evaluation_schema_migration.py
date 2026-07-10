from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_evaluation_case_migration_is_forward_and_reversible() -> None:
    up = (ROOT / "database/migrations/0017_evaluation_case_schema.up.sql").read_text()
    down = (ROOT / "database/migrations/0017_evaluation_case_schema.down.sql").read_text()
    for column in (
        "schema_version",
        "case_type",
        "visibility",
        "reviewer_status",
        "source_references",
        "license_metadata",
        "provenance_json",
    ):
        assert column in up
        assert column in down
    assert "evaluations', 'manage" in up
    assert "0017_evaluation_case_schema" in up
    assert "0017_evaluation_case_schema" in down
