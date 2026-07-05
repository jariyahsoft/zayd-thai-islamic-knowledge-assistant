# Software Requirements Specification — Zayd 1.0

## ข้อมูลเอกสาร

| รายการ | ค่า |
|---|---|
| เวอร์ชัน | SRS Summary 1.0 |
| วันที่ | 5 กรกฎาคม 2026 |
| สถานะ | DRAFT FOR TECHNICAL REVIEW |
| อ้างอิง | PRD 1.1 |

## 1. Scope

ระบบประกอบด้วย User PWA, Reviewer Portal, Admin Portal, Core API, Answer Orchestrator, Retrieval Engine, Ingestion Worker, Evaluation Service, PostgreSQL/pgvector, Redis และ S3-compatible object storage

ระบบต้องเปลี่ยน LLM, embedding, reranker, vector store และ knowledge provider ผ่าน adapter ได้

## 2. Architecture Constraints

- Greenfield Core + Selective Reuse
- Open-source first
- Local-first RAG
- Code license แยกจาก dataset license
- Production retrieval ใช้เฉพาะ `PUBLISHED`
- ทุกคำตอบมี trace และ version references
- LLM ไม่มีสิทธิ์ override license/security policies

## 3. Technology Baseline

### Frontend

- Next.js, TypeScript, Tailwind CSS, TanStack Query, i18next, PWA

### Backend

- Python, FastAPI, Pydantic, SQLAlchemy, Alembic, SSE

### Data

- PostgreSQL, pgvector, Redis, MinIO/S3-compatible

### Operations

- Docker Compose, OpenTelemetry, Prometheus/Grafana, Sentry-compatible error tracking

## 4. User Roles

- Guest
- User
- Data Operator
- Translator
- Reviewer
- Senior Scholar
- Admin
- Auditor
- Maintainer

RBAC permissions ต้องกำหนดเป็น action-based identifiers เช่น `documents.publish`, `licenses.manage`, `audit.read`

## 5. Functional Requirements

### 5.1 Authentication

- **FR-AUTH-001** รองรับ email/password
- **FR-AUTH-002** รองรับ OAuth/OIDC ผ่าน adapter
- **FR-AUTH-003** รองรับ guest session ที่มี TTL
- **FR-AUTH-004** Reviewer/Admin ต้องใช้ MFA
- **FR-AUTH-005** ผู้ใช้ revoke sessions ได้
- **FR-AUTH-006** Login และ role changes ต้องเข้า audit log

### 5.2 Chat

- **FR-CHAT-001** ถามภาษาไทยได้
- **FR-CHAT-002** รองรับอาหรับและอังกฤษระดับพื้นฐาน
- **FR-CHAT-003** ตอบแบบ SSE streaming
- **FR-CHAT-004** แสดงสถานะ analyze/search/verify/generate
- **FR-CHAT-005** เลือกมัซฮับและความยาวคำตอบได้
- **FR-CHAT-006** รองรับ history, deletion และ no-history mode
- **FR-CHAT-007** หยุด generation ได้
- **FR-CHAT-008** แสดง abstention เมื่อไม่มีหลักฐาน

### 5.3 Question Classification

- **FR-CLASS-001** ตรวจภาษา
- **FR-CLASS-002** จำแนก intent/topic
- **FR-CLASS-003** ระบุมัซฮับจากคำถามหรือ preference
- **FR-CLASS-004** จัด risk level
- **FR-CLASS-005** ตรวจว่าต้องใช้ข้อมูลปัจจุบันหรือไม่
- **FR-CLASS-006** Rule-based ก่อน LLM fallback

### 5.4 Retrieval

- **FR-RET-001** Local KB ก่อน external
- **FR-RET-002** Exact reference search
- **FR-RET-003** Full-text search
- **FR-RET-004** Vector search
- **FR-RET-005** Hybrid scoring
- **FR-RET-006** Metadata filters: language, madhhab, source type, status, license
- **FR-RET-007** Multilingual expansion ไทย/อังกฤษ/อาหรับ
- **FR-RET-008** Reranker ผ่าน adapter
- **FR-RET-009** บันทึก retrieval run และ score components
- **FR-RET-010** Evidence sufficiency: sufficient/partial/insufficient/conflicting

### 5.5 External Providers

- **FR-EXT-001** Provider ทุกตัวใช้ adapter
- **FR-EXT-002** Timeout, limited retry และ circuit breaker
- **FR-EXT-003** Cache ต้องมี TTL
- **FR-EXT-004** Provider manifest ระบุ storage policy
- **FR-EXT-005** ข้อมูล persistent ต้องผ่าน review ก่อน production
- **FR-EXT-006** Admin ปิด provider ได้

### 5.6 Answer Generation

- **FR-ANS-001** ข้อกล่าวอ้างสำคัญต้อง grounded ใน evidence
- **FR-ANS-002** Structured response schema
- **FR-ANS-003** แยก summary, explanation, evidence, differences, limitations
- **FR-ANS-004** ไม่อ้างว่าเป็นฟัตวา
- **FR-ANS-005** Revise หรือ abstain เมื่อ verification ไม่ผ่าน
- **FR-ANS-006** บันทึก model, prompt และ policy version

### 5.7 Citations

- **FR-CIT-001** ทุก citation มี canonical ID
- **FR-CIT-002** ผูก document version และ chunk
- **FR-CIT-003** LLM อ้างได้เฉพาะ IDs ที่ backend จัดให้
- **FR-CIT-004** ตรวจ reference, quote และ claim support
- **FR-CIT-005** แสดง metadata ตามประเภทแหล่ง
- **FR-CIT-006** Invalidate citation ได้
- **FR-CIT-007** Flag คำตอบเดิมที่ใช้ citation ถูกระงับ

### 5.8 Data Ingestion

- **FR-ING-001** PDF, DOCX, TXT, Markdown, HTML, JSON, CSV
- **FR-ING-002** File type/size validation และ malware scan
- **FR-ING-003** SHA-256 และ duplicate detection
- **FR-ING-004** เก็บ original file แบบ private
- **FR-ING-005** Parser plugin และ page/heading positions
- **FR-ING-006** เก็บ original กับ normalized text แยกกัน
- **FR-ING-007** AI metadata ต้องเป็น UNVERIFIED
- **FR-ING-008** ไม่ embed production ก่อน approval

### 5.9 Review and Publishing

- **FR-REV-001** Review queue/filter/assign/claim
- **FR-REV-002** Side-by-side original/extracted
- **FR-REV-003** Diff, comments และ revision history
- **FR-REV-004** Approve, request changes, reject, escalate
- **FR-REV-005** Two-level approval สำหรับเนื้อหาสำคัญ
- **FR-REV-006** Separation of duties
- **FR-REV-007** Publish แบบ atomic/compensating workflow
- **FR-REV-008** Suspend และ rollback ได้

### 5.10 Admin

- **FR-ADM-001** User/role management
- **FR-ADM-002** Provider/model management
- **FR-ADM-003** Source/license management
- **FR-ADM-004** Prompt/policy version management
- **FR-ADM-005** Re-index/re-embed
- **FR-ADM-006** Health, queue, usage, cost, audit

### 5.11 Feedback and Incidents

- **FR-FDB-001** ผู้ใช้รายงาน answer ได้
- **FR-FDB-002** Ticket เชื่อม answer/retrieval/citations/model/prompt/policy
- **FR-FDB-003** Reviewer ระบุ root cause และ resolution
- **FR-FDB-004** Incident severity P0–P3
- **FR-FDB-005** Answer invalidation และ user warning
- **FR-FDB-006** Incident แปลงเป็น regression test ได้

### 5.12 Open-source and Self-host

- **FR-OSS-001** `.env.example`
- **FR-OSS-002** Docker Compose development/minimal profiles
- **FR-OSS-003** ทำงานได้โดยไม่ต้องใช้ proprietary service
- **FR-OSS-004** Local LLM และ local embeddings
- **FR-OSS-005** Sample dataset ที่แจกได้
- **FR-OSS-006** Migration/seed/backup/restore commands
- **FR-OSS-007** Provider SDK และ plugin template

## 6. Data Model Requirements

Core entities:

- Users, roles, permissions, sessions
- Sources, source licenses
- Documents, versions, pages, chunks, embeddings
- Review tasks, reviews, comments, approvals
- Conversations, messages, answers
- Retrieval runs/results, citations
- Feedback, incidents, audit logs
- Providers, model configs, prompt/policy versions
- Evaluation datasets/cases/runs/results

ทุก entity สำคัญต้องมี UUID, timestamps และ version/audit references ตามความเหมาะสม

## 7. Document State Machine

`DRAFT → UPLOADED → PARSING → AI_EXTRACTED → IN_REVIEW → SCHOLAR_REVIEW → SCHOLAR_APPROVED → PUBLISHED`

ทางเลือก: `CHANGES_REQUESTED`, `REJECTED`, `SUSPENDED`, `ARCHIVED`, `NEW_VERSION`

ห้าม transition โดยข้าม approval ที่ policy กำหนด

## 8. API Requirements

- REST under `/api/v1`
- OpenAPI 3.1
- RFC 7807 errors
- Pagination
- Request/Trace ID
- Idempotency keys สำหรับ publish และงานสำคัญ
- SSE สำหรับ chat
- Rate-limit headers

## 9. Non-functional Requirements

### Security

- **NFR-SEC-001** TLS
- **NFR-SEC-002** Secure password hashing
- **NFR-SEC-003** Secrets ไม่อยู่ใน repo/log
- **NFR-SEC-004** MFA privileged roles
- **NFR-SEC-005** Endpoint authorization
- **NFR-SEC-006** Prompt injection defenses
- **NFR-SEC-007** Dependency/secret/container scanning
- **NFR-SEC-008** Immutable audit controls

### Privacy

- **NFR-PRV-001** ไม่ใช้บทสนทนาฝึกโมเดลโดยค่าเริ่มต้น
- **NFR-PRV-002** User deletion และ no-history
- **NFR-PRV-003** Redact personal data ก่อน external provider เมื่อทำได้
- **NFR-PRV-004** Logs ไม่เก็บข้อความเต็มโดย default

### Performance

- **NFR-PERF-001** หน้าแรก ≤ 3 วินาทีในเครือข่ายมือถือทั่วไป
- **NFR-PERF-002** เริ่ม streaming ≤ 5 วินาทีเป้าหมาย
- **NFR-PERF-003** Local retrieval ≤ 2 วินาทีเป้าหมาย
- **NFR-PERF-004** คำตอบทั่วไป ≤ 20 วินาทีเป้าหมาย

### Availability and Recovery

- **NFR-AVL-001** Availability MVP 99.5%
- **NFR-AVL-002** Local retrieval ทำงานได้เมื่อ external ล่ม
- **NFR-AVL-003** Health/readiness/liveness
- **NFR-BCK-001** Daily encrypted backup
- **NFR-BCK-002** Monthly restore test
- Initial targets: RPO 24h, RTO 8h

## 10. Testing Requirements

- Unit tests: policies, state machines, normalization, citations
- Integration: PostgreSQL, Redis, object storage, provider adapters
- E2E: upload→review→publish→ask→citation→feedback
- RAG benchmarks
- Security tests including authz, upload, SSRF, XSS, prompt injection
- License CI checks

## 11. Release Acceptance

- Docker Compose self-host works
- PWA, Reviewer, Admin usable
- Dataset license checks enforced
- Citation and safety quality gates pass
- No critical vulnerabilities
- Backup/restore passes
- Open-source files and third-party notices complete
