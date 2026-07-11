# Changelog

All notable changes to this project are recorded here.

The format follows a versioned changelog structure.

## [Unreleased]

### Added

- None.

## [1.0.0] - 2026-07-11

### Added

- **Platform Core**: Greenfield monorepo structure with Python services (`uv` workspace) and Next.js frontend applications (`pnpm` workspace).
- **Core Security**: JWT authentication with MFA support, separation of duties via swarmed RBAC permissions, and encrypted offsite backups.
- **Data & Ingestion**: S3 object storage integration, clamav malware scanner pipeline, and semantic document parsers.
- **Islamic Governance**: Madhhab policy engine (Shafii default), senior-scholar approval workflow, and citation-level verification checks.
- **RAG & Search**: Hybrid search engine combining pgvector vector search and full-text search, sliced by reliability level.
- **Safety**: Prompt injection validator, local SSRF loopback IP blocking, and rate limiters.
- **Review Portals**: Document review edit workspace, reviewer dashboard with aggregate stats, and feedback triage queue.
- **Evaluations**: Reproducible benchmark runner, citation/retrieval/safety metrics services, and run comparison dashboards.
- **Pilot Overlay**: Invite allowlisting via salted email digests, and isolated Stack volume overlays.

### Fixed

- Duplicate keys construct error in pilot swarm config profile.
- Executable shell bits on environment validator script.

## [0.1.0] - 2026-07-06

### Added

- Baseline open-source foundation documents.
- License and provenance policy separation.
- Community governance and contribution workflow guidance.

