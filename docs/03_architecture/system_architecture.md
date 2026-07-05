# System Architecture — Zayd 1.0

## 1. Architectural Style

Zayd ใช้ modular monolith ใน MVP ร่วมกับ background workers และ plugin/provider adapters โดยวาง boundary ให้แยก service ได้ภายหลัง

แนวทางหลัก:

- Greenfield Core + Selective Reuse
- Local-first RAG
- Ports and Adapters
- Versioned policies/prompts
- Human approval before production knowledge
- Auditability by design

## 2. Context Diagram

```text
Users / Reviewers / Admins
            │ HTTPS
            ▼
   Web / Reviewer / Admin
            │ REST + SSE
            ▼
        Zayd Core API
            │
  ┌─────────┼──────────┐
  ▼         ▼          ▼
Orchestrator Retrieval Ingestion/Review
  │         │          │
  ├─LLM     ├─Postgres ├─Object Storage
  ├─Policy  ├─pgvector ├─Workers
  └─Verify  └─Providers└─Audit
```

## 3. Runtime Components

### apps/web

- Mobile-first PWA
- Chat/history/preferences/citations/feedback

### apps/reviewer

- Review queues
- Original/extracted comparison
- Translation, metadata และ answer review

### apps/admin

- User/RBAC
- Sources/licenses
- Providers/models
- Prompt/policy versions
- Operations and incidents

### services/api

- Auth/session
- REST/SSE endpoints
- Domain services
- Authorization and audit hooks

### services/orchestrator

- Classification
- Risk/madhhab routing
- Retrieval workflow
- Answer generation
- Citation verification
- Revision/abstention

### services/retrieval

- Exact/full-text/vector/hybrid search
- Query normalization/expansion
- Reranking
- Evidence sufficiency

### services/ingestion and worker

- File scanning/parsing
- Text normalization
- Metadata suggestions
- Chunking/embedding/publishing
- Scheduled license/provider checks

## 4. Data Stores

### PostgreSQL

System of record สำหรับ users, content metadata, review, chat, traces, citations, policies และ evaluations

### pgvector

Embedding index ที่ผูกกับ immutable document version และ chunk

### Redis

Cache, rate limit, ephemeral jobs และ locks ไม่ใช่ source of truth

### S3-compatible storage

Original documents, permission evidence, exports และ backups โดย private เป็นค่าเริ่มต้น

## 5. Knowledge Lifecycle

```text
Source + License
      ↓
Upload → Scan → Parse → Normalize → AI Suggestions
      ↓
Human Review → Scholar Approval
      ↓
Freeze Version → Chunk → Embed → Citation Registry
      ↓
Publish atomically → Production Retrieval
      ↓
Suspend/Rollback เมื่อพบปัญหา
```

## 6. Answer Workflow

```text
Question
  ↓
Language/Intent/Risk/Madhhab Classification
  ↓
Local Exact + Hybrid Retrieval
  ↓
Evidence Sufficiency
  ├─ sufficient → generate
  ├─ partial → query expansion / external fallback
  ├─ conflicting → explain conflict / scholar route
  └─ insufficient → abstain
  ↓
Structured Answer
  ↓
Deterministic Citation Checks
  ↓
Claim Support Verification
  ↓
Revise or Return
```

## 7. Provider Boundaries

Interfaces:

- `LLMProvider`
- `EmbeddingProvider`
- `RerankerProvider`
- `KnowledgeProvider`
- `VectorStore`
- `ObjectStorageProvider`
- `AuthProvider`

Business logic ห้าม import SDK ของ provider โดยตรง

## 8. Security Boundaries

- Internet → reverse proxy/API gateway
- User apps → authenticated API
- Reviewer/Admin → MFA + RBAC
- API → private database/network
- Workers → limited object storage and queue permissions
- External providers → redacted/minimized payloads

## 9. Transaction and Consistency

Publishing ต้องไม่ทำให้เอกสารพร้อมค้นเพียงบางส่วน:

1. Freeze document version
2. Generate chunks/citations
3. Generate embeddings in staging state
4. Validate counts and hashes
5. Flip published version and searchable flag in transaction
6. On failure, compensate and leave previous version active

## 10. Versioning

ทุกคำตอบบันทึก:

- model configuration ID
- prompt version
- policy version
- retriever version
- query expansions
- document/chunk IDs
- citation verification results

## 11. Scalability

MVP scale-out:

- Stateless API replicas
- Separate worker replicas
- PostgreSQL connection pool
- Redis-backed rate limits/jobs
- Optional migration to Qdrant/OpenSearch through interfaces

## 12. Failure Modes

| Failure | Expected behavior |
|---|---|
| External API down | ใช้ local results หรือ abstain |
| Reranker down | ใช้ hybrid ranking |
| LLM timeout | retry limited/fallback model/return error |
| Citation verifier fails | ไม่ส่งคำตอบที่ยังไม่ verified |
| License expired | suspend source/documents according to policy |
| Embedding mismatch | reject query/index and require re-embed |
| Worker crash | retry idempotent job |

## 13. Observability

Trace spans:

- request/auth
- classify
- retrieve exact/full-text/vector
- rerank
- provider call
- generate
- citation verify
- database/worker

ห้าม log chain-of-thought หรือข้อความส่วนตัวเต็มโดย default
