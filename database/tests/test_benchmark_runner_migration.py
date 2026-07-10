from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_benchmark_runner_migration_records_reproducibility_fields() -> None:
    up = (ROOT / "database/migrations/0018_benchmark_runner.up.sql").read_text()
    down = (ROOT / "database/migrations/0018_benchmark_runner.down.sql").read_text()
    for field in ("run_config_json", "random_seed", "git_commit", "output_json", "duration_ms"):
        assert field in up
        assert field in down
    assert "0018_benchmark_runner" in up
    assert "0018_benchmark_runner" in down
