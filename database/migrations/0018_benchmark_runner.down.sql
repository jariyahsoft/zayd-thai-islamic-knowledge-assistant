DROP INDEX IF EXISTS idx_evaluation_runs_reproducibility;
ALTER TABLE evaluation_results
  DROP COLUMN IF EXISTS duration_ms,
  DROP COLUMN IF EXISTS output_json;
ALTER TABLE evaluation_runs
  DROP COLUMN IF EXISTS git_commit,
  DROP COLUMN IF EXISTS random_seed,
  DROP COLUMN IF EXISTS run_config_json;
DELETE FROM schema_migrations WHERE version = '0018_benchmark_runner';
