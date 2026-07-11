# Roadmap

## Status

This roadmap covers currently approved baseline milestones only. It does not promise delivery dates.

## Zayd 1.0 Milestone Status

All MVP tasks required for the v1.0 closed pilot have been successfully completed:

- **Milestone 1**: Open-source foundation and legal separation (Completed)
- **Milestone 2**: Monorepo and development environment (Completed)
- **Milestone 3**: Core database, authentication, and RBAC (Completed)
- **Milestone 4**: Ingestion pipelines, malware scans, and parsers (Completed)
- **Milestone 5**: Hybrid search, vector pgvector, and query expansion (Completed)
- **Milestone 6**: Orchestration, citation checks, and Safety Engine (Completed)
- **Milestone 7**: Operations logging, OTel tracing, and Prometheus metrics (Completed)
- **Milestone 8**: Benchmark runner, evaluations, and pilot allowance (Completed)

## Zayd 1.1 Planning & Production Roadmap

Future developmental phases planned to transition Zayd from closed pilot to public production release:

- **Distributed Telemetry & Rate-Limiting**: Move from process-local memory caches to Redis cluster-backed limiters and centralized metrics buckets.
- **Enhanced Normalization**: Support and validate deep Arabic orthographic variants and rich Thai lexical expansions.
- **Richer Content Policies**: Scale the Safety Policy Engine to support dynamic classifications for additional legal/jurisprudential categories.
- **Automated Regression Audits**: Wire evaluation runner outputs into automated feedback loops to assert that new model configurations don't regression-check previous user-reported issues.

## Guidance

Major roadmap changes require the governance process described in [`GOVERNANCE.md`](GOVERNANCE.md).

## Related Documents

- [`README.md`](README.md)
- [`CONTRIBUTING.md`](CONTRIBUTING.md)
- [`CHANGELOG.md`](CHANGELOG.md)

