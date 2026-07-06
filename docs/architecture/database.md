# Database Architecture

Status: design draft for `TASK-02-01`

Zayd uses PostgreSQL as the system of record and pgvector for embedding search. Redis is cache/queue state only, and object storage contains original documents, permission evidence and large artifacts.

## Ownership Boundaries

| Area | Owner | Database responsibility |
|---|---|---|
| `services/api` | API/domain services | Identity, RBAC, review workflow, conversations, feedback, incidents and audit hooks |
| `services/ingestion` | Ingestion workers | Source document intake, version creation, extracted text and page mapping |
| `services/retrieval` | Retrieval service | Chunks, full-text search, embeddings, retrieval runs and retrieval results |
| `services/orchestrator` | Orchestrator service | Answers, citations, provider/model configs, prompt and policy versions |
| `services/evaluation` | Evaluation service | Evaluation datasets, cases, runs and results |
| `database/` | Database maintainers | Migrations, schemas, database tests and seed fixtures only; no business logic |

## Source of Truth

PostgreSQL stores:

- Users, roles, permissions and sessions.
- Sources, license records and document metadata.
- Document versions, extracted text, chunks, citations and embedding metadata.
- Review tasks, reviews, approvals and comments.
- Conversations, messages, answers, retrieval runs and retrieval results.
- Feedback, incidents and append-only audit records.
- Provider/model configuration, prompt versions and policy versions.
- Evaluation datasets, cases, runs and results.

Object storage stores:

- Original uploaded files.
- Permission evidence documents.
- Large exports and development/production backup artifacts.

Redis stores:

- Ephemeral cache, rate limit state, locks and background-job coordination.
- Redis must not be treated as the durable source of truth.

## Data Lifecycle

```text
Source + SourceLicense
        ↓
Document metadata
        ↓
DocumentVersion (original_file_key + extracted_text + metadata)
        ↓
DocumentPage + DocumentChunk (normalized searchable text)
        ↓
ReviewTask / Review / Approval
        ↓
Freeze version + publish document pointer
        ↓
EmbeddingRecord + Citation
        ↓
RetrievalRun / RetrievalResult
        ↓
Answer + Feedback + Incident + AuditLog
```

## State and Versioning

### Document State

Document state follows SRS §24:

```text
DRAFT → UPLOADED → PARSING → AI_EXTRACTED → IN_REVIEW
  ↳ CHANGES_REQUESTED → IN_REVIEW
  ↳ REJECTED
  ↳ SCHOLAR_REVIEW → SCHOLAR_APPROVED → PUBLISHED
       ↳ SUSPENDED
       ↳ ARCHIVED
       ↳ NEW_VERSION
```

Database design supports this through:

- `documents.review_status` for the current aggregate state.
- immutable `document_versions.version_number` for every content version.
- `documents.published_version_id` for the current production version.
- append-only `reviews` and `approvals` records.
- `audit_logs` for every sensitive mutation and state transition.

Runtime validation for allowed transitions belongs in service code, not migration files.

### Versioned Configuration

The following entities are immutable once used in production traces:

- `document_versions`
- `prompt_versions`
- `policy_versions`
- `evaluation_datasets`
- `retrieval_runs`
- `answers`
- `audit_logs`

Mutable configuration tables (`providers`, `model_configurations`, `sources`, roles and users) include `row_version` for optimistic locking and must be audited on mutation.

## Retrieval Boundary

Production retrieval must be fail-closed:

1. `documents.review_status = 'published'`.
2. `documents.published_version_id = document_versions.id`.
3. `document_versions.status = 'published'` and `frozen_at IS NOT NULL`.
4. `document_chunks.is_published = true`.
5. `source_licenses.status` allows persistent use.
6. `source_licenses.embedding_permission` allows embedding where vector search is used.
7. `citations.verified = true` and `invalidated_at IS NULL` for citation-backed evidence.
8. `embedding_records.status = 'active'` for vector search.

The `core-domain.schema.json` file documents these as invariants; TASK-02-02 will translate feasible constraints into PostgreSQL checks, foreign keys, triggers or validated service transactions.

## License and Content Separation

License records and document text are intentionally separate:

- `source_licenses` stores legal and usage permissions.
- `documents` references a `source_license_id` used for the current document.
- `document_versions` stores extracted text and metadata.
- `document_chunks` stores normalized chunk text.
- `embedding_records` stores vector artifacts only.

This supports license expiry, revocation and takedown without rewriting source text tables.

## Sensitive Data Handling

Sensitive columns include:

- `auth_users.email`, `display_name`, `password_hash`
- `auth_sessions.session_hash`, `ip_hash`, `user_agent_hash`
- `document_versions.original_file_key`, `extracted_text`
- `document_chunks.content`, `content_normalized`
- `messages.body`, `retrieval_runs.query_original`, `retrieval_runs.query_normalized`
- `answers.answer_json`, `feedback.body`, `incidents.summary`
- `providers.base_url`, `providers.secret_ref`, `prompt_versions.prompt_body`

Controls:

- Do not log full sensitive values by default.
- Use hashes for session tokens and integrity checks.
- Keep provider secrets in environment/secret manager; database rows store references only.
- Use soft delete/anonymization for user-facing data where legal/product policy permits.
- Keep audit summaries concise and redacted.

## Index Strategy

Primary access patterns and required indexes are listed in `database/schemas/core-domain.schema.json` and summarized in `database/schemas/core-domain.md`.

High-priority query paths:

1. Review queue lookup by status, level and due date.
2. Published full-text chunk search filtered by language, madhhab, source type, review/license status and reliability.
3. Published vector search by active embedding model.
4. Citation lookup by canonical reference.
5. Conversation history by user and update time.
6. Audit lookup by actor, resource and trace ID.
7. Evaluation result aggregation by run.

## Migration Guidance for TASK-02-02

- Enable required extensions early: `pgcrypto`, `citext`, `vector`.
- Create enums before dependent tables.
- Create identity/config tables first, then source/license, document/version, chunks, citations/retrieval, chat/answers, feedback/incidents and evaluation.
- Handle the `documents.published_version_id → document_versions.id` relationship with a deferrable FK or an `ALTER TABLE` after both tables exist.
- Convert cross-row invariants into service transactions and/or triggers where PostgreSQL CHECK constraints cannot reference other tables.
- Make all destructive migration steps explicit and reversible where possible.

## Security Review Notes

- No production data, secrets or restricted religious corpus are part of this design.
- Schema supports RBAC and audit but runtime enforcement remains in later auth/API tasks.
- Embeddings are considered derived content and must be invalidated on license expiry, document suspension or model change.
- Answer records intentionally reference prompt, policy, model and retrieval versions to support post-incident review and regression tests.
