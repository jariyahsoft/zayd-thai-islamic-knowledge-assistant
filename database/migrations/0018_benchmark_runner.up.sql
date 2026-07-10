ALTER TABLE evaluation_runs
  ADD COLUMN IF NOT EXISTS run_config_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS random_seed integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS git_commit text NOT NULL DEFAULT 'unknown';

ALTER TABLE evaluation_results
  ADD COLUMN IF NOT EXISTS output_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS duration_ms double precision;

CREATE INDEX IF NOT EXISTS idx_evaluation_runs_reproducibility
  ON evaluation_runs (dataset_id, model_configuration_id, prompt_version_id, policy_version_id, random_seed);

INSERT INTO schema_migrations (version, description)
VALUES ('0018_benchmark_runner', 'Reproducible benchmark configuration and case outputs')
ON CONFLICT (version) DO NOTHING;
