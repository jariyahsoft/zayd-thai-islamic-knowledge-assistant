# Software Requirements Specification — Zayd 1.0

## ข้อมูลเอกสาร

| รายการ | รายละเอียด |
|---|---|
| ชื่อระบบ | Zayd |
| ชื่อเต็ม | Zayd — Thai Islamic Knowledge Assistant |
| ประเภทระบบ | Open-source Islamic AI and RAG Platform |
| เวอร์ชันเอกสาร | SRS 1.1 |
| วันที่ | 5 กรกฎาคม 2026 |
| สถานะ | DRAFT FOR TECHNICAL REVIEW |
| เอกสารอ้างอิง | PRD 1.1 |
| แพลตฟอร์มหลัก | Mobile-first Web Application / PWA |
| รูปแบบการเผยแพร่ | Open Source + Self-hosted + Optional Cloud Services |
| ภาษาหลัก | ภาษาไทย |
| ภาษารอง | ภาษาอาหรับและภาษาอังกฤษ |
| มัซฮับเริ่มต้น | ชาฟิอี โดยผู้ใช้สามารถเปลี่ยนได้ |
| เอกสารฉบับย่อ | [SRS_summary.md](SRS_summary.md) |
| Traceability | [traceability_matrix.md](traceability_matrix.md) |

---

# 1. วัตถุประสงค์ของเอกสาร

เอกสารนี้กำหนดข้อกำหนดทางเทคนิคของระบบ Zayd สำหรับใช้เป็นแหล่งอ้างอิงหลักของทีมพัฒนา ผู้ตรวจทานระบบ ผู้ดูแลโครงการ และ AI Coding Agent โดยครอบคลุม:

- สถาปัตยกรรมระบบ
- Functional Requirements
- Non-functional Requirements
- โครงสร้างฐานข้อมูล
- ระบบ Retrieval-Augmented Generation
- ระบบตรวจทานและอนุมัติเนื้อหา
- ระบบสิทธิ์ผู้ใช้งาน
- ระบบ API และ streaming
- แนวทาง Open Source และ Self-host
- ระบบทดสอบและประเมินคุณภาพ
- ความปลอดภัย ความเป็นส่วนตัว และการสำรองข้อมูล
- การจัดการสิทธิ์ของชุดข้อมูลและ External API
- เกณฑ์การส่งมอบและเปิดใช้งาน Zayd 1.0

เอกสารนี้ใช้เป็นฐานสำหรับ:

1. ออกแบบฐานข้อมูลและ migration
2. ออกแบบ API และ contracts
3. แตกงานพัฒนาใน `tasks/`
4. สร้าง Test Cases และ Benchmark
5. สร้าง CI/CD และ Release Gates
6. สร้างเอกสาร Open-source และ Self-host
7. ประเมินความพร้อมก่อน Closed Pilot และ Production

---

# 2. ขอบเขตระบบ

Zayd เป็นผู้ช่วย AI สำหรับค้นคว้าและอธิบายความรู้อิสลามสำหรับผู้ใช้ภาษาไทย โดยตอบจากหลักฐานที่ค้นได้จริง แสดงแหล่งอ้างอิง และแยกทัศนะตามมัซฮับอย่างชัดเจน

ระบบประกอบด้วย:

1. User Web Application / PWA
2. Reviewer Portal
3. Admin Portal
4. Core API
5. AI Answer Orchestrator
6. Retrieval Engine
7. Local Knowledge Base
8. External Knowledge Provider Connectors
9. Document Ingestion Pipeline
10. Citation Registry and Verification Service
11. Feedback and Incident Management
12. Evaluation and Benchmark Framework
13. Open-source Plugin System
14. Self-host Deployment Package
15. Monitoring, Backup and Operational Tooling

ระบบต้องไม่ผูกกับ provider รายเดียว และต้องเปลี่ยนส่วนต่อไปนี้ผ่าน adapter หรือ plugin ได้:

- LLM
- Embedding model
- Reranker
- Vector store
- Object storage
- Authentication provider
- External Islamic knowledge API
- OCR and document parser

---

# 3. เป้าหมายทางสถาปัตยกรรม

## 3.1 Open Source First

ระบบหลักต้อง:

- ติดตั้งได้ด้วย Docker Compose
- ใช้งานได้โดยไม่ผูกกับ Cloud รายเดียว
- ใช้ Local LLM และ Local Embedding ได้
- เปลี่ยน provider ได้โดยไม่แก้ business logic
- ตรวจสอบ source code และ build artifacts ได้
- ทดสอบได้โดยใช้ mock provider และ sample dataset
- ไม่มี production secret หรือ restricted dataset อยู่ใน repository

## 3.2 Data License Separation

สิทธิ์ของโค้ด เอกสาร และชุดข้อมูลต้องแยกจากกัน:

```text
Open-source code
    ≠
Open documentation
    ≠
Open dataset
    ≠
สิทธิ์นำข้อความศาสนาหรือคำแปลไปแจกจ่ายต่อ
```

การเปิด source code ของ Zayd ไม่ได้หมายความว่า corpus ทุกชุดสามารถนำไปแจกจ่าย ใช้เชิงพาณิชย์ หรือสร้าง embedding ได้

## 3.3 Modular Architecture

โมดูลต้องสื่อสารผ่าน interface ที่กำหนดไว้ เพื่อรองรับการเปลี่ยน implementation และลด vendor lock-in

## 3.4 Local-first RAG

ระบบต้องค้นฐานข้อมูลในเครื่องก่อนใช้ External API และต้องยังตอบจาก Local RAG ได้เมื่อ provider ภายนอกไม่พร้อมใช้งาน

## 3.5 Auditable by Design

ทุกคำตอบต้องตรวจย้อนกลับได้อย่างน้อยถึง:

- Request ID และ Trace ID
- Model และ provider
- Prompt version
- Policy version
- Retrieval version
- Query expansions
- Document version และ chunk
- Citation IDs
- Evidence sufficiency result
- ผู้ตรวจที่อนุมัติเอกสาร

## 3.6 Scholar-in-the-loop

เอกสารสำคัญ โดยเฉพาะฟิกฮ์ คำแปล และเนื้อหาที่มีความเห็นต่าง ต้องผ่าน workflow ตรวจทานก่อนค้นได้ใน Production

---

# 4. แนวทางการเปิด Source Code

## 4.1 Repository Strategy

ใช้ Hybrid Repository Strategy:

```text
zayd-project/
├── zayd-platform       # แอปและบริการหลัก
├── zayd-datasets       # ชุดข้อมูลที่มีสิทธิ์เผยแพร่
├── zayd-benchmarks     # Benchmark สาธารณะ
├── zayd-deploy         # Deployment templates
├── zayd-docs           # Documentation
└── zayd-community      # Community resources
```

ในช่วง MVP สามารถเก็บ `zayd-platform`, docs และ deployment เบื้องต้นใน monorepo เดียวก่อน แล้วแยก repository เมื่อมีเหตุผลด้าน release หรือสิทธิ์ข้อมูล

## 4.2 `zayd-platform`

เก็บ:

- User Web
- Reviewer Portal
- Admin Portal
- Backend API
- Worker
- Retrieval Engine
- Provider adapters
- Shared packages
- Database migrations

License ที่แนะนำ: **Apache License 2.0**

## 4.3 `zayd-datasets`

เก็บเฉพาะ:

- Dataset manifests
- Metadata ที่เผยแพร่ได้
- Sample records
- Public-domain content
- Scripts สำหรับดาวน์โหลดจากต้นทาง
- Checksum และ attribution

ทุก dataset ต้องมี:

```text
dataset.yaml
LICENSE
SOURCE.md
ATTRIBUTION.md
CHECKSUMS.txt
```

## 4.4 `zayd-benchmarks`

เก็บ:

- Zayd-IslamicQA-TH public subset
- Evaluation scripts
- Retrieval cases
- Citation cases
- High-risk routing cases
- Adversarial cases

สามารถแยก private holdout set เพื่อป้องกัน benchmark contamination

## 4.5 `zayd-deploy`

เก็บ:

- Docker Compose
- Kubernetes manifests
- Helm charts
- Terraform examples
- Reverse proxy configuration
- Monitoring configuration
- Backup scripts

ต้องไม่มี API key, password, certificate หรือ restricted dataset

---

# 5. License Structure

## 5.1 Source Code

แนะนำ Apache-2.0 เพื่อรองรับการใช้ แก้ไข แจกจ่าย และใช้งานเชิงพาณิชย์ พร้อม patent grant

## 5.2 Documentation

แนะนำ CC BY 4.0

## 5.3 Trademark

ชื่อและ logo ของ Zayd สามารถอยู่ภายใต้ Trademark Policy แยกจาก license ของ source code

## 5.4 Dataset

Dataset แต่ละชุดต้องมี license แยก เช่น:

- Public Domain
- CC BY
- CC BY-SA
- CC BY-NC
- Permission granted
- Private use only
- Cache only
- No redistribution

## 5.5 Third-party Code

Repository ต้องมี:

```text
THIRD_PARTY_NOTICES.md
CODE_PROVENANCE.md
licenses/
```

ทุกโมดูลที่นำมาจากโครงการอื่นต้องบันทึก repository, commit hash, license, วันที่นำเข้า และรายละเอียดการแก้ไข

---

# 6. สถาปัตยกรรมระดับสูง

```text
┌──────────────────────────────────────────────┐
│ Client Applications                          │
│ User PWA | Reviewer Portal | Admin Portal    │
└──────────────────────┬───────────────────────┘
                       │ HTTPS / SSE
                       ▼
┌──────────────────────────────────────────────┐
│ API Gateway / Core API                       │
│ Auth | RBAC | Rate Limit | Validation        │
└──────────────────────┬───────────────────────┘
                       ▼
┌──────────────────────────────────────────────┐
│ Answer Orchestrator                          │
│ Classification | Risk | Madhhab | Retrieval  │
│ Generation | Citation Verification           │
└──────────────┬───────────────────┬───────────┘
               │                   │
               ▼                   ▼
┌────────────────────────┐   ┌─────────────────┐
│ Local Retrieval        │   │ External Adapters│
│ PostgreSQL/pgvector    │   │ Quran/Hadith/API │
│ Full-text + Reranker   │   │ Optional Cloud   │
└──────────────┬─────────┘   └────────┬────────┘
               └────────────┬─────────┘
                            ▼
┌──────────────────────────────────────────────┐
│ Knowledge and Review Layer                   │
│ Sources | Licenses | Documents | Chunks      │
│ Citations | Reviews | Versions | Audit Logs  │
└──────────────────────────────────────────────┘
```

รายละเอียดเชิงสถาปัตยกรรมให้ยึด [System Architecture](../03_architecture/system_architecture.md) และ ADR ที่อนุมัติแล้ว

---

# 7. Technology Stack

## 7.1 Frontend

- Next.js
- TypeScript
- React
- Tailwind CSS
- TanStack Query
- i18next
- Markdown renderer
- PWA
- OpenAPI-generated client

## 7.2 Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- LangGraph หรือ custom state machine
- Server-Sent Events

## 7.3 Data Layer

- PostgreSQL
- pgvector
- PostgreSQL Full-text Search
- Redis
- MinIO หรือ S3-compatible object storage

## 7.4 Optional Search Backends

- Qdrant
- OpenSearch
- Elasticsearch

## 7.5 Monitoring and Operations

- OpenTelemetry
- Prometheus
- Grafana
- Loki หรือ compatible log store
- Sentry-compatible error tracking
- Docker / Docker Compose
- Kubernetes เป็น optional production profile

---

# 8. โครงสร้าง Monorepo

```text
zayd-platform/
├── apps/
│   ├── web/
│   ├── reviewer/
│   └── admin/
├── services/
│   ├── api/
│   ├── orchestrator/
│   ├── retrieval/
│   ├── ingestion/
│   ├── worker/
│   └── evaluation/
├── packages/
│   ├── ui/
│   ├── api-client/
│   ├── contracts/
│   ├── config/
│   ├── auth/
│   ├── citations/
│   ├── provider-sdk/
│   ├── plugin-sdk/
│   └── testing/
├── plugins/
│   ├── llm/
│   ├── embeddings/
│   ├── rerankers/
│   ├── vector-stores/
│   ├── knowledge-providers/
│   ├── auth-providers/
│   └── storage/
├── database/
│   ├── migrations/
│   ├── schemas/
│   ├── seeds/
│   └── tests/
├── evaluation/
├── infra/
├── docs/
├── tasks/
└── .github/
```

กฎ dependency boundaries:

- Apps ห้ามเข้าถึง database โดยตรง
- Business logic ห้าม import SDK ของ provider โดยตรง
- Provider-specific code ต้องอยู่ใน plugin/adapter
- Shared packages ห้ามพึ่ง app หรือ service ชั้นบน
- Religious policy และ license policy ต้องเป็น server-side enforcement

---

# 9. Provider Adapter Architecture

## 9.1 LLM Provider Interface

```python
class LLMProvider:
    async def generate(self, request): ...
    async def stream(self, request): ...
    async def health_check(self): ...
    def capabilities(self): ...
```

รองรับ OpenAI-compatible API, Anthropic, Gemini, Ollama, vLLM, llama.cpp และ custom provider

## 9.2 Embedding Provider Interface

```python
class EmbeddingProvider:
    async def embed_documents(self, texts): ...
    async def embed_query(self, text): ...
    def dimensions(self): ...
    def model_id(self): ...
```

## 9.3 Knowledge Provider Interface

```python
class KnowledgeProvider:
    async def search(self, query, filters): ...
    async def fetch_document(self, reference): ...
    async def health_check(self): ...
    def storage_policy(self): ...
```

## 9.4 Vector Store Interface

```python
class VectorStore:
    async def search(self, vector, filters, limit): ...
    async def upsert(self, records): ...
    async def delete(self, ids): ...
```

## 9.5 Plugin Manifest

```yaml
name: zayd-provider-example
type: knowledge_provider
version: 1.0.0
api_version: 1
license: Apache-2.0
capabilities:
  - search
  - document_fetch
storage_policy:
  persistent_storage: false
  max_cache_ttl_seconds: 604800
```

ทุก plugin ต้องประกาศ capability, license, API compatibility และ storage policy

---

# 10. ผู้ใช้งาน บทบาท และสิทธิ์

## 10.1 Roles

| Role | หน้าที่ |
|---|---|
| Guest | ถามคำถามแบบจำกัดและไม่มีสิทธิ์หลังบ้าน |
| User | ประวัติ บันทึกคำตอบ และส่ง Feedback |
| Data Operator | นำเข้าและจัดเตรียมเอกสาร |
| Translator | ตรวจและแก้คำแปล |
| Reviewer | ตรวจข้อความ metadata และหลักฐาน |
| Senior Scholar | อนุมัติเนื้อหาศาสนาสำคัญ |
| Admin | จัดการระบบ ผู้ใช้ provider และ configuration |
| Auditor | อ่าน audit และข้อมูลที่ได้รับอนุญาตโดยแก้ไขไม่ได้ |
| Maintainer | ดูแล Open-source Project และ release |

## 10.2 Permission Model

ใช้ RBAC แบบ action-based เช่น:

```text
documents.upload
documents.edit
documents.review
documents.approve
documents.publish
documents.archive
answers.review
answers.invalidate
providers.manage
users.manage
licenses.manage
prompts.manage
models.manage
audit.read
audit.export
```

## 10.3 Separation of Duties

ผู้ใช้ต้องไม่สามารถ:

- อัปโหลดและอนุมัติเอกสารสำคัญของตนเอง
- เปลี่ยนเอกสารที่ publish แล้วโดยไม่สร้าง version ใหม่
- ลบ audit log
- เปลี่ยน license โดยไม่มีสิทธิ์
- Publish เอกสารที่ไม่มี valid approval
- ลดสิทธิ์ admin คนสุดท้ายโดยไม่มี safeguard

---

# 11. Functional Requirements — Authentication

- **FR-AUTH-001** ระบบต้องรองรับการสมัครและเข้าสู่ระบบด้วย Email และ Password
- **FR-AUTH-002** ระบบต้องรองรับ OAuth/OIDC ผ่าน adapter โดยไม่ผูกกับ provider เดียว
- **FR-AUTH-003** ระบบต้องรองรับ Guest Session ที่มี TTL และสิทธิ์จำกัด
- **FR-AUTH-004** Reviewer, Senior Scholar และ Admin ต้องเปิดใช้ MFA
- **FR-AUTH-005** ผู้ใช้ต้องสามารถ logout และ revoke sessions ทุกอุปกรณ์ได้
- **FR-AUTH-006** ระบบต้องบันทึก login สำคัญ การเปลี่ยน role และ security event ลง audit log
- **FR-AUTH-007** ระบบต้องรองรับ password reset ที่ไม่เปิดเผยว่าบัญชีมีอยู่หรือไม่
- **FR-AUTH-008** Refresh token ต้องหมุนเวียนและตรวจจับ reuse ได้
- **FR-AUTH-009** ระบบต้องรองรับ session expiration และ privileged re-authentication
- **FR-AUTH-010** ระบบต้องไม่ผูกกับ Firebase Authentication โดยตรง

Acceptance highlights:

- Password ใช้ adaptive password hashing ที่ได้รับการยอมรับ
- Login และ reset endpoint มี rate limit
- Recovery code ใช้ได้ครั้งเดียว
- Token และ credential ต้องไม่ปรากฏใน log

---

# 12. Functional Requirements — User Chat

- **FR-CHAT-001** ผู้ใช้ต้องสามารถถามคำถามภาษาไทยได้
- **FR-CHAT-002** ระบบต้องรองรับคำถามภาษาอาหรับและอังกฤษระดับพื้นฐาน
- **FR-CHAT-003** ระบบต้องตอบเป็นภาษาเดียวกับผู้ใช้เป็นค่าเริ่มต้น
- **FR-CHAT-004** ระบบต้องตอบแบบ streaming ผ่าน SSE
- **FR-CHAT-005** ระบบต้องแสดงสถานะ วิเคราะห์คำถาม ค้นหลักฐาน ตรวจ citation และเรียบเรียงคำตอบ
- **FR-CHAT-006** ผู้ใช้ต้องเลือกความยาวคำตอบได้: สั้น ปกติ ละเอียด
- **FR-CHAT-007** ผู้ใช้ต้องเลือกมัซฮับหรือใช้ค่าเริ่มต้นได้
- **FR-CHAT-008** ระบบต้องรองรับบทสนทนาต่อเนื่องภายใน thread
- **FR-CHAT-009** ระบบต้องแยกบริบทเมื่อผู้ใช้เปลี่ยนหัวข้อ
- **FR-CHAT-010** ผู้ใช้ต้องหยุด generation ได้
- **FR-CHAT-011** ระบบต้องแสดง abstention เมื่อหลักฐานไม่พอ
- **FR-CHAT-012** ผู้ใช้ที่อนุญาตต้องบันทึกประวัติและคำตอบโปรดได้
- **FR-CHAT-013** ผู้ใช้ต้องลบ thread ประวัติทั้งหมด หรือเปิด no-history mode ได้
- **FR-CHAT-014** ระบบต้องไม่แสดง hidden chain-of-thought หรือ internal prompt

## 12.1 Functional Requirements — Madhhab Preferences

- **FR-MADH-001** ระบบต้องใช้มัซฮับชาฟิอีเป็นค่าเริ่มต้นสำหรับคำถามฟิกฮ์เมื่อผู้ใช้ยังไม่ได้เลือก
- **FR-MADH-002** ระบบต้องแจ้งค่าเริ่มต้นนี้ให้ผู้ใช้ทราบอย่างชัดเจน
- **FR-MADH-003** ผู้ใช้ต้องเปลี่ยนมัซฮับจากการตั้งค่าได้
- **FR-MADH-004** ผู้ใช้ต้องระบุมัซฮับในคำถามได้ และค่าที่ระบุในคำถามมีลำดับเหนือ preference ทั่วไป
- **FR-MADH-005** เมื่อมีหลายทัศนะ ระบบต้องแยกทัศนะและแหล่งอ้างอิงของแต่ละมัซฮับ
- **FR-MADH-006** ระบบต้องไม่ผสมหลักฐานหรือคำวินิจฉัยของหลายมัซฮับเป็นคำตอบเดียวโดยไม่ระบุ
- **FR-MADH-007** Retrieval trace และ answer record ต้องบันทึกมัซฮับที่ใช้ในการค้นและตอบ

---

# 13. Functional Requirements — Question Classification

- **FR-CLASS-001** ระบบต้องตรวจภาษาของคำถาม
- **FR-CLASS-002** ระบบต้องจำแนก intent เช่น Quran, Hadith, Fiqh, Aqidah, History, Halal, Personal Advice และ High-risk Ruling
- **FR-CLASS-003** ระบบต้องตรวจมัซฮับที่ผู้ใช้ระบุและใช้ user preference เมื่อเหมาะสม
- **FR-CLASS-004** ระบบต้องจำแนกระดับความเสี่ยงเป็น Low, Medium, High หรือ Restricted
- **FR-CLASS-005** ระบบต้องตรวจว่าคำถามต้องใช้ข้อมูลปัจจุบันหรือกฎระเบียบเฉพาะประเทศไทยหรือไม่
- **FR-CLASS-006** ระบบต้องใช้ deterministic rules ก่อน LLM สำหรับกฎความเสี่ยงสำคัญ
- **FR-CLASS-007** ผล classification ต้องเป็น structured output และเก็บ version
- **FR-CLASS-008** ระบบต้องรองรับการแก้ classification จาก reviewer เพื่อใช้เป็น regression case

---

# 14. Functional Requirements — Retrieval

- **FR-RET-001** ระบบต้องค้น Local Knowledge Base ก่อน External API
- **FR-RET-002** ระบบต้องรองรับ exact reference lookup
- **FR-RET-003** ระบบต้องรองรับ Full-text Search
- **FR-RET-004** ระบบต้องรองรับ Vector Search
- **FR-RET-005** ระบบต้องรองรับ Hybrid Search
- **FR-RET-006** ระบบต้องกรอง metadata ตาม language, madhhab, source type, review status, license status และ reliability
- **FR-RET-007** ระบบต้องรองรับ Multilingual Query Expansion ไทย อังกฤษ และอาหรับ
- **FR-RET-008** ระบบต้องรองรับ Reranker และ fallback เมื่อ reranker ไม่พร้อม
- **FR-RET-009** Production Retrieval ต้องค้นเฉพาะเอกสารและ chunk สถานะ `PUBLISHED`
- **FR-RET-010** ระบบต้องบันทึก Retrieval Run และคะแนนองค์ประกอบของผลค้นหา
- **FR-RET-011** ระบบต้องประเมิน Evidence Sufficiency ก่อนสร้างคำตอบ
- **FR-RET-012** ระบบต้องค้นเพิ่มเติมหรือขยายคำค้นเมื่อหลักฐานไม่พอ
- **FR-RET-013** ระบบต้องงดตอบเมื่อยังไม่มีหลักฐานเพียงพอ
- **FR-RET-014** ทุก chunk ต้องย้อนกลับไปยัง document version และตำแหน่งต้นฉบับได้
- **FR-RET-015** ระบบต้องรองรับ invalidation เมื่อ document หรือ citation ถูก suspend

---

# 15. Functional Requirements — External API and Data Rights

- **FR-EXT-001** External provider ทุกตัวต้องติดตั้งผ่าน adapter
- **FR-EXT-002** ระบบต้องตรวจ storage and license policy ก่อน cache, persist, embed หรือ redistribute ข้อมูล
- **FR-EXT-003** ระบบต้องตรวจ response cache ก่อนเรียก provider
- **FR-EXT-004** Cache ต้องมี TTL ตามข้อกำหนด provider
- **FR-EXT-005** ข้อมูลที่อนุญาตเก็บถาวรต้องเข้า Review Queue ก่อน Production RAG
- **FR-EXT-006** ระบบต้องมี timeout, limited retry และ circuit breaker
- **FR-EXT-007** Admin ต้องปิด provider ได้โดยไม่ปิดระบบทั้งหมด
- **FR-EXT-008** ระบบต้องเก็บ provider name, API version, retrieved time และ storage policy
- **FR-EXT-009** ระบบต้องไม่ใช้ API เพื่อทำสำเนาฐานข้อมูลหาก terms ไม่อนุญาต
- **FR-EXT-010** Provider failure ต้องไม่ทำให้ Local Retrieval หยุดทำงาน
- **FR-EXT-011** ข้อมูลสิทธิ์ `UNKNOWN`, `PROHIBITED` หรือ `EXPIRED` ต้อง fail closed

---

# 16. Functional Requirements — Answer Generation

- **FR-ANS-001** ระบบต้องสร้างข้อกล่าวอ้างสำคัญจาก evidence ที่ค้นได้เท่านั้น
- **FR-ANS-002** คำตอบต้องใช้ structured response schema
- **FR-ANS-003** คำตอบต้องแยก summary, explanation, evidence, madhhab views, limitations และ warning
- **FR-ANS-004** ระบบต้องแสดงทัศนะต่างอย่างชัดเจนและไม่ผสมโดยไม่ระบุ
- **FR-ANS-005** ระบบต้อง abstain เมื่อหลักฐานไม่พอหรือขัดแย้งโดยไม่สามารถสรุปได้
- **FR-ANS-006** ระบบต้องแจ้งข้อจำกัดและไม่อ้างว่าคำตอบเป็นฟัตวา
- **FR-ANS-007** คำถามเสี่ยงสูงต้องถูกจำกัดคำตอบหรือส่งต่อผู้รู้ตาม policy
- **FR-ANS-008** ระบบต้องรองรับ answer revision เมื่อ citation verification ไม่ผ่าน
- **FR-ANS-009** ระบบต้องบันทึก model, prompt, policy และ retrieval version กับคำตอบ
- **FR-ANS-010** ระบบต้องไม่เก็บ hidden chain-of-thought

## 16.1 Functional Requirements — Answer Safety

- **FR-SAFE-001** ระบบต้องจัดระดับความเสี่ยงของคำถามเป็น Low, Medium, High หรือ Restricted
- **FR-SAFE-002** คำถามเสี่ยงสูงต้องมีคำเตือน จำกัดขอบเขตคำตอบ หรือส่งต่อผู้รู้ตาม policy
- **FR-SAFE-003** ระบบต้องไม่ตัดสินบุคคลว่าเป็นกุฟรฺหรือออกจากศาสนา
- **FR-SAFE-004** ระบบต้องไม่ให้คำแนะนำด้านสุขภาพหรือความปลอดภัยที่อาจก่ออันตราย และต้องส่งต่อผู้เชี่ยวชาญเมื่อเหมาะสม
- **FR-SAFE-005** ระบบต้องไม่แสดง confidence สูงเมื่อหลักฐานไม่เพียงพอหรือขัดแย้ง
- **FR-SAFE-006** ระบบต้องมีรูปแบบคำตอบ abstain ที่ชัดเจนเมื่อไม่พบหลักฐานเพียงพอ
- **FR-SAFE-007** สถาปัตยกรรมต้องรองรับช่องทางส่งคำถามให้ผู้รู้ แม้อาจเปิดใช้งานหลัง MVP
- **FR-SAFE-008** ทุกคำตอบต้องบันทึก risk classification และ policy version

---

# 17. Functional Requirements — Citation

- **FR-CIT-001** ทุก citation ต้องมี canonical ID
- **FR-CIT-002** Citation ต้องเชื่อมกับ document version และ chunk/reference ต้นทาง
- **FR-CIT-003** LLM ต้องอ้างได้เฉพาะ Citation ID ที่ backend ส่งให้
- **FR-CIT-004** ระบบต้องตรวจ citation existence, reference correctness และ claim support
- **FR-CIT-005** Citation Quran ต้องแสดงซูเราะฮ์ อายะฮ์ ข้อความอาหรับ คำแปล และแหล่งคำแปล
- **FR-CIT-006** Citation Hadith ต้องแสดง collection, number, text, translation, grade และ grader เมื่อมี
- **FR-CIT-007** Citation หนังสือต้องแสดงชื่อ ผู้เขียน ผู้แปล เล่ม หน้า edition และ publisher เมื่อมี
- **FR-CIT-008** ระบบต้องแยก direct quotation ออกจาก AI explanation
- **FR-CIT-009** Citation ต้อง invalidate และ suspend ได้
- **FR-CIT-010** คำตอบเก่าที่อ้าง citation ที่ invalidated ต้องถูก flag เพื่อตรวจซ้ำ
- **FR-CIT-011** Quote fidelity ต้องตรวจเทียบกับข้อความต้นฉบับแบบ deterministic เมื่อทำได้

---

# 18. Functional Requirements — Document Ingestion

- **FR-ING-001** ระบบต้องรองรับ PDF, DOCX, TXT, Markdown, HTML, JSON และ CSV
- **FR-ING-002** ระบบต้องตรวจชนิด ขนาด malware และ checksum ของไฟล์
- **FR-ING-003** ระบบต้องตรวจ duplicate ก่อนนำเข้า
- **FR-ING-004** ไฟล์ต้องเชื่อมกับ source และ license record
- **FR-ING-005** ระบบต้องสกัดข้อความและเก็บตำแหน่งหน้า/section
- **FR-ING-006** ระบบต้องรองรับ OCR เป็น optional plugin
- **FR-ING-007** ระบบต้อง normalize ภาษาไทยและอาหรับโดยเก็บ original text แยก
- **FR-ING-008** ระบบต้องสร้าง metadata suggestions และติดป้าย `UNVERIFIED`
- **FR-ING-009** ระบบต้องสร้าง Review Task หลัง parsing สำเร็จ
- **FR-ING-010** ระบบต้องไม่สร้าง Production Embedding ก่อน approval
- **FR-ING-011** ระบบต้องรองรับ parser plugin, retry และ failure isolation
- **FR-ING-012** ระบบต้องรองรับ re-index และ re-embed แบบ versioned
- **FR-ING-013** Chunking ต้องคำนึงถึงโครงสร้างอายะฮ์ หะดีษ ประเด็นฟิกฮ์ ย่อหน้า ตาราง และบริบท

---

# 19. Functional Requirements — Reviewer Portal

- **FR-REV-001** Reviewer ต้องดู กรอง claim และ assign คิวงานได้
- **FR-REV-002** Reviewer ต้องเห็นไฟล์ต้นฉบับและข้อความที่สกัดพร้อมกัน
- **FR-REV-003** Reviewer ต้องแก้ข้อความ metadata คำแปล และเพิ่มหมายเหตุได้
- **FR-REV-004** ทุกการแก้ไขต้องสร้าง revision และ diff
- **FR-REV-005** Reviewer ต้อง Approve, Reject, Request Changes หรือ Escalate ได้
- **FR-REV-006** Senior Scholar ต้องอนุมัติหรือ suspend เนื้อหาสำคัญได้
- **FR-REV-007** ระบบต้องรองรับ two-level approval และ separation of duties
- **FR-REV-008** ระบบต้องบันทึกผู้ตรวจ เวลา เหตุผล และ approval validity
- **FR-REV-009** Reviewer ต้องตรวจคำตอบที่ถูกรายงานพร้อม retrieval trace ได้
- **FR-REV-010** Reviewer ต้อง preview chunk และ citation ก่อน publish ได้
- **FR-REV-011** งาน review ต้องรองรับ priority, due date และ SLA metrics

---

# 20. Functional Requirements — Admin Portal

- **FR-ADM-001** Admin ต้องจัดการผู้ใช้ role session และ account status ได้
- **FR-ADM-002** Admin ต้องจัดการ provider และทดสอบ connection ได้
- **FR-ADM-003** Admin ต้องจัดการ model allow-list, primary, fallback และ cost limits ได้
- **FR-ADM-004** Admin ต้องจัดการ prompt และ policy version ได้
- **FR-ADM-005** Admin ต้องจัดการ source และ license record ได้
- **FR-ADM-006** Admin ต้องดู queue, system health, provider health และ cost ได้
- **FR-ADM-007** Admin ต้องสั่ง re-index, re-embed, rollback และ suspend source/document ได้
- **FR-ADM-008** การเปลี่ยนแปลงสำคัญต้องเข้า audit log
- **FR-ADM-009** Secrets ต้องถูก mask และห้ามอ่านค่าจริงจาก UI หลังบันทึก
- **FR-ADM-010** Admin UI ต้องป้องกันการลบหรือ downgrade admin คนสุดท้ายโดยไม่ตั้งใจ
- **FR-ADM-011** Admin Dashboard ต้องแสดง system health, provider health, queue depth, RAG hit rate, cost และ incident summary
- **FR-ADM-012** Admin/Auditor ที่มีสิทธิ์ต้องดูและ export immutable audit logs ได้ แต่ห้ามแก้หรือลบผ่าน application

---

# 21. Functional Requirements — Feedback and Incident

- **FR-FDB-001** ผู้ใช้ต้องรายงานคำตอบผิดได้
- **FR-FDB-002** ผู้ใช้ต้องเลือกประเภทปัญหาและเพิ่มคำอธิบายได้
- **FR-FDB-003** ระบบต้องสร้าง ticket เชื่อมกับ question, answer, retrieval, citations, model, prompt และ policy
- **FR-FDB-004** Reviewer ต้อง assign, classify, add root cause และ resolve ticket ได้
- **FR-FDB-005** Incident ต้องมี severity P0, P1, P2 หรือ P3
- **FR-FDB-006** P0/P1 ต้องแจ้งผู้ดูแลและรองรับ source/document suspension
- **FR-FDB-007** ระบบต้อง invalidate answer และแสดงคำเตือนในคำตอบเก่าได้
- **FR-FDB-008** Incident ที่ยืนยันแล้วต้องแปลงเป็น regression test ได้
- **FR-FDB-009** ข้อมูลส่วนบุคคลต้องถูก redact ก่อนสร้าง public benchmark case
- **FR-FDB-010** ผู้ใช้ต้องรับการแจ้งผลตรวจได้เมื่อเปิด notification

---

# 22. Functional Requirements — Open-source and Self-host

- **FR-OSS-001** ระบบต้องเริ่มต้นได้จาก `.env.example`
- **FR-OSS-002** ต้องมี Docker Compose สำหรับ development
- **FR-OSS-003** ต้องมี Minimal Self-host profile
- **FR-OSS-004** ระบบต้องทำงานได้โดยไม่มี proprietary service เมื่อใช้ Local LLM/Embedding
- **FR-OSS-005** ต้องมี sample dataset ที่มีสิทธิ์เผยแพร่
- **FR-OSS-006** ต้องมีคำสั่ง migration และ seed admin
- **FR-OSS-007** ต้องมี health, readiness และ liveness endpoints
- **FR-OSS-008** ต้องมี backup และ restore scripts
- **FR-OSS-009** ต้องมีเอกสารติดตั้งบน Ubuntu Server
- **FR-OSS-010** ต้องมี provider/plugin development guide
- **FR-OSS-011** Release ต้องมี container image, SBOM, checksum และ release notes
- **FR-OSS-012** Repository ต้องมี governance, contribution, security และ third-party notices
- **FR-OSS-013** Restricted dataset และ secrets ต้องไม่อยู่ใน public release

---

# 23. Data Model

## 23.1 Core Entities

```text
User, Role, Permission, Session
Source, SourceLicense
Document, DocumentVersion, DocumentPage, DocumentChunk, EmbeddingRecord
ReviewTask, Review, Approval, ReviewComment
Conversation, Message, Answer
RetrievalRun, RetrievalResult, Citation
Feedback, Incident, AuditLog
Provider, ModelConfiguration, PromptVersion, PolicyVersion
EvaluationDataset, EvaluationCase, EvaluationRun, EvaluationResult
```

## 23.2 Source

ฟิลด์ขั้นต่ำ:

```text
id, name, source_type, owner, website, language, country,
reliability_level, is_active, created_at, updated_at
```

## 23.3 SourceLicense

```text
id, source_id, license_name, storage_permission,
embedding_permission, commercial_use, redistribution,
attribution_required, permission_document_key,
valid_from, valid_until, status, notes
```

## 23.4 Document

```text
id, source_id, canonical_id, document_type, title, author,
translator, publisher, edition, language, madhhab,
review_status, published_version_id, created_at, updated_at
```

## 23.5 DocumentVersion

```text
id, document_id, version_number, content_hash,
original_file_key, extracted_text, metadata_json,
created_by, created_at
```

## 23.6 DocumentChunk

```text
id, document_version_id, chunk_index, content,
content_normalized, token_count, page_start, page_end,
section, reference, metadata_json, is_published,
chunking_strategy_version
```

## 23.7 Review and Approval

```text
review_task_id, reviewer_id, decision, comments,
fields_changed, created_at, approval_level, valid_until
```

## 23.8 Citation

```text
id, canonical_reference, document_version_id, chunk_id,
citation_type, display_title, arabic_text, thai_translation,
hadith_grade, volume, page, verified, invalidated_at
```

## 23.9 RetrievalRun

```text
id, request_id, query_original, query_normalized,
query_expansions, filters, retriever_version, results,
evidence_sufficient, created_at
```

## 23.10 Answer

```text
id, message_id, model_id, prompt_version_id, policy_version_id,
risk_level, madhhab, answer_json, confidence_level,
evidence_sufficient, created_at
```

ข้อมูลต้องใช้ foreign keys, unique constraints, timestamps, versioning และ indexes ตาม query pattern

---

# 24. Document State Machine

```text
DRAFT
  ↓
UPLOADED
  ↓
PARSING
  ↓
AI_EXTRACTED
  ↓
IN_REVIEW
  ├── CHANGES_REQUESTED ──→ IN_REVIEW
  ├── REJECTED
  └── SCHOLAR_REVIEW
           ├── CHANGES_REQUESTED
           ├── REJECTED
           └── SCHOLAR_APPROVED
                    ↓
                PUBLISHED
                    ├── SUSPENDED
                    ├── ARCHIVED
                    └── NEW_VERSION
```

กฎ:

- Production Retrieval ใช้เฉพาะ `PUBLISHED`
- การเปลี่ยน published content ต้องสร้าง version ใหม่
- Suspend ต้องนำ chunk ออกจาก retrieval ทันที
- State transition ทุกครั้งต้องผ่าน server-side validation และ audit
- Publish ต้องอ้าง valid license และ approval

---

# 25. API Requirements

Base path:

```text
/api/v1
```

## 25.1 Authentication

```text
POST /auth/register
POST /auth/login
POST /auth/logout
POST /auth/refresh
POST /auth/password/reset
POST /auth/mfa/setup
POST /auth/mfa/verify
GET  /auth/me
```

## 25.2 Chat

```text
POST   /chat/threads
GET    /chat/threads
GET    /chat/threads/{thread_id}
DELETE /chat/threads/{thread_id}
POST   /chat/threads/{thread_id}/messages
GET    /chat/threads/{thread_id}/stream
```

## 25.3 Citations and Sources

```text
GET /citations/{citation_id}
GET /sources/{source_id}
GET /documents/{document_id}
```

## 25.4 Feedback

```text
POST /feedback
GET  /feedback/{feedback_id}
```

## 25.5 Documents

```text
POST  /documents
POST  /documents/{id}/upload
GET   /documents
GET   /documents/{id}
PATCH /documents/{id}
POST  /documents/{id}/submit-review
POST  /documents/{id}/publish
POST  /documents/{id}/suspend
```

## 25.6 Reviews

```text
GET  /reviews/queue
GET  /reviews/{id}
POST /reviews/{id}/approve
POST /reviews/{id}/request-changes
POST /reviews/{id}/reject
POST /reviews/{id}/escalate
```

## 25.7 Admin

```text
GET   /admin/providers
POST  /admin/providers
PATCH /admin/providers/{id}
GET   /admin/models
POST  /admin/models
GET   /admin/licenses
POST  /admin/licenses
GET   /admin/audit-logs
GET   /admin/system-health
```

## 25.8 Standards

- OpenAPI 3.1
- JSON
- RFC 7807 Problem Details
- Cursor or page-based pagination
- Request ID and Trace ID
- Idempotency key สำหรับ mutation สำคัญ
- Rate-limit headers
- API versioning
- Stable structured error codes
- SSE สำหรับ streaming

---

# 26. Answer Response Schema

```json
{
  "answer_id": "uuid",
  "summary": "คำตอบโดยสรุป",
  "answer_th": "คำอธิบายภาษาไทย",
  "madhhab": "shafii",
  "risk_level": "medium",
  "evidence_sufficient": true,
  "confidence": "high",
  "citations": [
    {
      "citation_id": "CIT-001",
      "display": "ชื่อแหล่งอ้างอิง",
      "source_type": "hadith",
      "verification_status": "verified"
    }
  ],
  "differences_of_opinion": [],
  "limitations": [],
  "requires_scholar": false,
  "trace_id": "REQ-001"
}
```

Client ห้ามอนุมานว่าคำตอบ verified หาก `verification_status` ไม่ผ่าน

---

# 27. Evidence Sufficiency

ระบบต้องพิจารณาอย่างน้อย:

- จำนวนเอกสารและความหลากหลายของแหล่ง
- Retrieval score
- Reranker score
- ความตรงกับหัวข้อและคำถาม
- ความตรงกับมัซฮับ
- Approval และ publication status
- Citation completeness
- Source reliability
- ความขัดแย้งระหว่างเอกสาร
- ความสดใหม่สำหรับข้อมูลที่เปลี่ยนแปลงได้

ผลลัพธ์มาตรฐาน:

```text
SUFFICIENT
PARTIALLY_SUFFICIENT
INSUFFICIENT
CONFLICTING
```

กฎ:

- ห้ามใช้ similarity score ค่าเดียวตัดสิน
- Rule-based evaluator ต้องทำงานได้โดยไม่ใช้ LLM
- LLM evaluator ใช้ได้เป็นชั้นเสริมเท่านั้น
- `INSUFFICIENT` ต้องนำไปสู่ค้นเพิ่มหรือ abstain
- `CONFLICTING` ต้องแสดงความเห็นต่างหรือส่งต่อผู้รู้

---

# 28. Prompt Management

Prompt ต้องไม่ hard-code กระจายใน source code

```text
prompts/
├── system/
├── classification/
├── query-expansion/
├── answer-generation/
├── verification/
└── review-assistance/
```

ทุก prompt ต้องมี:

- ID
- Version
- Purpose
- Input schema
- Output schema
- Owner
- Approval status
- Test cases
- Changelog

Production ใช้เฉพาะ prompt สถานะ `APPROVED`

ทุกคำตอบต้องบันทึก prompt version แต่ห้ามเปิด system prompt หรือ hidden reasoning ต่อผู้ใช้

---

# 29. Model Routing

ระบบต้องกำหนด model ตามงาน:

| งาน | แนวทาง |
|---|---|
| Language detection | Rule-based หรือโมเดลเล็ก |
| Intent classification | โมเดลราคาต่ำ + deterministic rules |
| Query expansion | Multilingual model |
| Answer generation | โมเดลคุณภาพสูง |
| Citation verification | Deterministic checks + optional verifier model |
| Metadata extraction | Batch model |
| Embedding | Multilingual embedding |
| Reranking | Multilingual reranker |

Admin ต้องกำหนด:

- Primary model
- Fallback model
- Timeout
- Token/context limit
- Cost limit
- Data classification allowed
- Provider health threshold

การเปลี่ยน model ที่มีผลต่อคำตอบ Production ต้องผ่าน evaluation gate

---

# 30. Security Requirements

- **NFR-SEC-001** ทุกการเชื่อมต่อภายนอกต้องใช้ TLS
- **NFR-SEC-002** Password ต้อง hash ด้วย adaptive algorithm ที่ได้รับการยอมรับ
- **NFR-SEC-003** Secrets ต้องไม่อยู่ใน repository หรือ log
- **NFR-SEC-004** Privileged roles ต้องใช้ MFA
- **NFR-SEC-005** ต้องมี rate limiting และ abuse protection
- **NFR-SEC-006** ทุก protected endpoint ต้องตรวจ authorization ฝั่ง server
- **NFR-SEC-007** ต้องตรวจ malware และ file type ของ upload
- **NFR-SEC-008** ต้องป้องกัน path traversal, SSRF, XSS, SQL injection และ command injection
- **NFR-SEC-009** ต้องป้องกัน prompt injection จากผู้ใช้และเอกสาร
- **NFR-SEC-010** Document content ต้องไม่สามารถ override system/license/security policy
- **NFR-SEC-011** Audit log ต้องแก้หรือลบไม่ได้โดยผู้ใช้ทั่วไป
- **NFR-SEC-012** ต้องมี dependency, secret, container และ SAST scanning
- **NFR-SEC-013** ต้องมี CSP, secure headers และ CORS allow-list
- **NFR-SEC-014** External provider egress ต้องถูกจำกัดและตรวจสอบ
- **NFR-SEC-015** ต้องมี Security Disclosure Process
- **NFR-SEC-016** Sensitive mutations ต้องรองรับ re-authentication หรือ step-up auth
- **NFR-SEC-017** Object storage ต้อง private by default และใช้ signed URLs
- **NFR-SEC-018** Log และ traces ต้อง redact token, secret และข้อมูลส่วนบุคคล

---

# 31. Privacy Requirements

- **NFR-PRV-001** บทสนทนาต้องไม่ถูกนำไปฝึกโมเดลโดยค่าเริ่มต้น
- **NFR-PRV-002** ผู้ใช้ต้องลบประวัติและข้อมูลที่อนุญาตให้ลบได้
- **NFR-PRV-003** ระบบต้องมี no-history mode
- **NFR-PRV-004** ต้องลดหรือปกปิดข้อมูลส่วนบุคคลก่อนส่ง provider ภายนอกเมื่อทำได้
- **NFR-PRV-005** ต้องมี Data Retention Policy แยกตามข้อมูล
- **NFR-PRV-006** Analytics ต้องแยกจากข้อความสนทนาเต็ม
- **NFR-PRV-007** ผู้ดูแลต้องไม่เห็นบทสนทนาโดยไม่มีสิทธิ์และเหตุผล
- **NFR-PRV-008** Benchmark จาก incident ต้อง redact ข้อมูลส่วนบุคคล
- **NFR-PRV-009** ผู้ใช้ต้องทราบเมื่อข้อมูลถูกส่งไป External Provider ตามนโยบายผลิตภัณฑ์
- **NFR-PRV-010** Backup ต้องปฏิบัติตาม retention และ deletion policy

---

# 32. Performance Requirements

- **NFR-PERF-001** หน้าแรกควรโหลดภายใน 3 วินาทีบนเครือข่ายมือถือทั่วไป
- **NFR-PERF-002** ระบบควรเริ่ม streaming ภายใน 5 วินาที
- **NFR-PERF-003** Local Retrieval ควรเสร็จภายใน 2 วินาทีในภาวะปกติ
- **NFR-PERF-004** คำตอบทั่วไปควรเสร็จภายใน 20 วินาที
- **NFR-PERF-005** Reviewer Queue ควรเปิดภายใน 3 วินาที
- **NFR-PERF-006** Background ingestion ต้องไม่ลดความสามารถ Chat API อย่างมีนัยสำคัญ
- **NFR-PERF-007** API list endpoints ต้องใช้ pagination
- **NFR-PERF-008** Provider timeout ต้องกำหนดแยกตามประเภทงาน

ตัวเลขเป็นเป้าหมายเริ่มต้นและต้องยืนยันด้วย load test

---

# 33. Availability Requirements

- **NFR-AVL-001** Availability เป้าหมาย MVP คือ 99.5%
- **NFR-AVL-002** Local RAG ต้องทำงานได้เมื่อ External API ล่ม
- **NFR-AVL-003** ระบบต้องมี health, readiness และ liveness endpoints
- **NFR-AVL-004** ต้องมี circuit breaker และ graceful degradation
- **NFR-AVL-005** ระบบต้องสามารถเปิด read-only search mode เมื่อ generation service ไม่พร้อม
- **NFR-AVL-006** Worker failure ต้องไม่ทำให้ API process ล่ม
- **NFR-AVL-007** Publish operation ต้องป้องกัน partial availability ของเอกสาร
- **NFR-AVL-008** Provider health ต้องแสดงใน Admin Dashboard

---

# 34. Backup and Disaster Recovery

ต้องสำรอง:

- PostgreSQL
- Object storage
- Prompt versions
- Policy versions
- License evidence
- Audit logs
- Deployment configuration ที่ไม่ใช่ secret

Requirements:

- **NFR-BCK-001** ต้องมี Daily Backup
- **NFR-BCK-002** ต้องมี Off-site Backup
- **NFR-BCK-003** Backup ต้องเข้ารหัส
- **NFR-BCK-004** Production ต้องทดสอบ Restore อย่างน้อยรายเดือน
- **NFR-BCK-005** ต้องมี Disaster Recovery Runbook
- **NFR-BCK-006** Restore ต้องตรวจ consistency ระหว่าง database และ object storage
- **NFR-BCK-007** ต้องบันทึกผล backup/restore และแจ้งเตือนเมื่อผิดพลาด

เป้าหมายเริ่มต้น:

```text
RPO: 24 ชั่วโมง
RTO: 8 ชั่วโมง
```

---

# 35. Observability

ทุก request ต้องมี Trace ID และบันทึก telemetry ที่จำเป็นโดยไม่เก็บ sensitive content เกินจำเป็น

Metrics/trace ขั้นต่ำ:

- API latency and error rate
- Retrieval latency and score distribution
- LLM/provider latency, token usage and cost
- Cache hit rate
- Local RAG hit rate
- External fallback rate
- Citation verification failure rate
- Evidence insufficiency rate
- Queue depth and task age
- Database and object storage health
- Model/provider health

Dashboard ขั้นต่ำ:

1. API Health
2. Chat and Retrieval Latency
3. Error Rate
4. Worker Queue
5. Database Health
6. Provider Health
7. Cost and Token Usage
8. Citation and Safety Metrics
9. Reviewer Queue Metrics

ห้าม log ข้อความผู้ใช้เต็มโดยค่าเริ่มต้น

---

# 36. Testing Requirements

## 36.1 Unit Tests

ครอบคลุม:

- Domain logic
- Permission checks
- State transitions
- License policy
- Citation validation
- Query normalization
- Risk policy
- Evidence sufficiency

## 36.2 Integration Tests

ครอบคลุม:

- PostgreSQL/pgvector
- Redis
- MinIO/S3-compatible storage
- Worker queue
- Provider adapters
- Full-text and vector search

## 36.3 End-to-End Tests

ครอบคลุม:

- User Chat
- Document Upload
- Review and Publish
- Retrieval and Citation
- Feedback and Incident
- Admin Settings
- Suspend and Rollback

## 36.4 RAG Evaluation

- Recall@5
- Recall@10
- MRR
- Precision
- Reranker accuracy
- Citation correctness
- Evidence sufficiency
- Abstention accuracy
- Madhhab consistency

## 36.5 Security Tests

- Authentication bypass
- Authorization/IDOR
- Upload attacks
- SSRF
- XSS
- SQL injection
- Prompt injection
- Secret leakage
- Rate limiting

## 36.6 License Tests

CI ต้องตรวจ:

- Dependency licenses
- Missing third-party notices
- Dataset manifests
- Restricted files
- Unknown dataset license
- Permission expiry

---

# 37. CI/CD Requirements

Pull Request ทุกครั้งต้องผ่าน:

```text
Formatting
Lint
Type Check
Unit Tests
Integration Tests
Migration Check
Security Scan
Dependency Scan
License Scan
Secret Scan
Container Scan
Build
```

Merge ไป `main` ต้อง:

- ผ่าน required reviews
- ผ่าน CODEOWNERS ตามพื้นที่
- ไม่มี Critical Vulnerability
- ไม่มี migration conflict
- มี documentation/changelog เมื่อจำเป็น

Release ต้อง:

- ใช้ Semantic Versioning
- มี Release Notes
- มี Container Images
- มี SBOM
- มี Checksums
- มี Migration Guide
- มี Known Issues
- มี signed artifact เมื่อรองรับ

---

# 38. Branching Strategy

แนะนำ Trunk-based Development:

```text
main
feature/*
fix/*
docs/*
release/*
```

กฎ:

- ห้าม push เข้า `main` โดยตรง
- ใช้ Pull Request
- Require status checks
- Require review
- ใช้ squash merge เป็นค่าเริ่มต้น
- ใช้ signed commits สำหรับ maintainers เมื่อทำได้
- งาน schema/security/policy ต้องมี CODEOWNER review

---

# 39. Open-source Governance

## 39.1 Roles

- Contributor
- Reviewer
- Maintainer
- Security Maintainer
- Islamic Content Board
- Data Steward

## 39.2 Decision Process

การเปลี่ยนแปลงสำคัญต้องใช้ RFC เช่น:

- เปลี่ยน license
- เปลี่ยนฐานข้อมูลหรือ vector store หลัก
- เปลี่ยน API contract
- เปลี่ยน Madhhab Policy
- เปลี่ยน Answer Safety Policy
- เพิ่มชุดข้อมูลที่มีข้อถกเถียง
- เปลี่ยน Governance

## 39.3 RFC Structure

```text
RFC number
Title
Author
Status
Motivation
Proposal
Alternatives
Security impact
Religious-content impact
Data-license impact
Migration plan
```

---

# 40. Community Files

Repository ต้องมี:

- `README.md`
- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `GOVERNANCE.md`
- `SECURITY.md`
- `SUPPORT.md`
- `ROADMAP.md`
- `CHANGELOG.md`
- `LICENSE`
- `NOTICE`
- `TRADEMARK.md`
- `THIRD_PARTY_NOTICES.md`
- `CODE_PROVENANCE.md`

Issue templates:

- Bug report
- Feature request
- Documentation
- Data source proposal
- Religious content issue
- Translation issue
- Citation error
- Security issue redirect

---

# 41. Contribution Workflow

```text
Issue
  ↓
Triage
  ↓
Design/RFC เมื่อจำเป็น
  ↓
Implementation
  ↓
Tests
  ↓
Pull Request
  ↓
Automated Checks
  ↓
Code Review
  ↓
Content Review เมื่อเกี่ยวข้อง
  ↓
Merge
  ↓
Release
```

PR ที่เกี่ยวกับเนื้อหาศาสนาต้องระบุ:

- เนื้อหาที่เปลี่ยน
- แหล่งข้อมูล
- มัซฮับ
- License
- ผู้ตรวจ
- Test case

---

# 42. Data Contribution Workflow

ผู้ร่วมพัฒนาที่เสนอชุดข้อมูลต้องส่ง:

```text
Dataset manifest
Source URL
Owner
License
Permission evidence
Language
Madhhab
Content type
Checksum
Import script
Sample records
Validation report
```

ห้าม merge หนังสือหรือ corpus ที่ไม่มีข้อมูลสิทธิ์ชัดเจน

---

# 43. Self-host Deployment Profiles

## 43.1 Minimal

```text
Web
API
Worker
PostgreSQL + pgvector
Redis
MinIO
Local LLM หรือ API Provider
```

## 43.2 Standard

```text
Reverse Proxy
Web / Reviewer / Admin
API Replicas
Worker
PostgreSQL
Redis
MinIO
Monitoring
Backup
```

## 43.3 Production

```text
Load Balancer / WAF
Multiple App Replicas
HA PostgreSQL
Redis HA
Object Storage
Dedicated Worker Pools
Central Monitoring
Off-site Backup
Secret Manager
```

---

# 44. Environment Configuration

`.env.example` ต้องมีเฉพาะค่าตัวอย่าง:

```text
APP_ENV=development
APP_URL=http://localhost:3000
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
S3_ENDPOINT=http://minio:9000
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=http://ollama:11434
LLM_MODEL=
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=
DEFAULT_LANGUAGE=th
DEFAULT_MADHHAB=shafii
ENABLE_EXTERNAL_PROVIDERS=false
ENABLE_GUEST_MODE=true
```

ระบบต้อง validate configuration ตอนเริ่ม และ mask secret ใน error/log

---

# 45. Installation Requirements

Development/Minimal Self-host ต้องเริ่มได้โดยลำดับประมาณ:

```bash
git clone <repository>
cd zayd-platform
cp .env.example .env
docker compose up -d
make migrate
make seed-admin
make seed-demo-data
```

ต้องมีคำสั่ง:

```text
make setup
make dev
make stop
make migrate
make seed-admin
make seed-demo
make test
make lint
make typecheck
make build
make backup
make restore
```

เอกสารต้องระบุ resource minimum, port, storage, provider setup และ troubleshooting

---

# 46. Public API and MCP

ไม่ใช่ MVP หลัก แต่ architecture ต้องรองรับ

## 46.1 Public API

- API Keys
- Quota
- Rate Limit
- Usage logs
- Citation required
- License-aware response filtering
- ห้าม export raw copyrighted document โดยไม่มีสิทธิ์

## 46.2 MCP Server

Tools ขั้นต่ำในอนาคต:

```text
search_quran
search_hadith
search_fiqh
get_citation
get_source
ask_zayd
```

MCP ต้องใช้ permission, audit และ license policy เดียวกับ Web Application

---

# 47. Acceptance Criteria ระดับระบบ

Zayd 1.0 ถือว่าผ่านเมื่อ:

1. ติดตั้งด้วย Docker Compose ได้จาก clean environment
2. ใช้ Local LLM ได้อย่างน้อยหนึ่งตัว
3. ใช้ Cloud/OpenAI-compatible LLM ผ่าน adapter ได้
4. เปลี่ยน embedding provider ได้
5. ผู้ใช้ถามภาษาไทยได้
6. ระบบตอบพร้อม citation ที่เปิดดูได้
7. Reviewer Portal ใช้งานได้
8. Document Workflow ทำงานครบ
9. Production Retrieval ใช้เฉพาะ `PUBLISHED`
10. License Registry และ policy engine ทำงานได้
11. External API fallback มี cache, timeout และ policy
12. ผู้ใช้รายงานคำตอบผิดได้
13. Admin ตรวจ retrieval trace ได้
14. Audit Log ทำงานได้
15. Benchmark Runner ใช้งานได้
16. Backup และ Restore ผ่านการทดสอบ
17. CI ผ่านทุกขั้นตอน
18. ไม่มี Critical Vulnerability
19. Open-source documentation ครบ
20. Release ไม่มี secret หรือ restricted dataset
21. Citation fabrication เป็นศูนย์ในชุดทดสอบหลัก
22. High-risk routing ผ่าน quality gate
23. Closed Pilot ไม่มี P0/P1 ค้าง

---

# 48. Definition of Done สำหรับ Task

Task ถือว่าเสร็จเมื่อ:

- มี Requirement ID
- มี Scope และ Acceptance Criteria
- Implementation ครบ
- Unit Tests ผ่าน
- Integration/E2E Tests ผ่านเมื่อเกี่ยวข้อง
- Type Check และ Lint ผ่าน
- Security และ License Checks ผ่าน
- Documentation อัปเดต
- Logging/Monitoring เพิ่มเมื่อจำเป็น
- Code Review ผ่าน
- Content Review ผ่านเมื่อเกี่ยวข้อง
- ไม่มี Critical/High issue ค้างโดยไม่มี mitigation
- Completion Report ใน task ถูกอัปเดต

---

# 49. Development Milestones

## Milestone 0 — Open-source Foundation

- Repository
- License
- Governance
- Contribution Guide
- Security Policy
- CI foundation

## Milestone 1 — Core Infrastructure

- Monorepo
- Docker Compose
- PostgreSQL/pgvector
- Redis
- MinIO
- Authentication
- RBAC
- Audit

## Milestone 2 — Knowledge Lifecycle

- Source and License Registry
- Upload
- Parser
- Review Queue
- Scholar Approval
- Publish

## Milestone 3 — Retrieval

- Chunking
- Embedding
- Full-text
- Vector
- Hybrid
- Reranking
- Evidence Sufficiency

## Milestone 4 — AI Answering

- Classification
- Risk Policy
- Madhhab Routing
- Query Expansion
- Generation
- Citation Verification
- Abstention

## Milestone 5 — Applications

- User PWA
- Reviewer Portal
- Admin Portal
- Feedback

## Milestone 6 — Evaluation

- Zayd-IslamicQA-TH
- Retrieval Benchmark
- Citation Benchmark
- Safety Benchmark
- Regression Tests

## Milestone 7 — Self-host Release

- Installation Guide
- Demo Dataset
- Backup/Restore
- Monitoring
- Container Images
- SBOM

## Milestone 8 — Closed Pilot

- Scholar Testing
- User Testing
- Security Testing
- Performance Testing
- Incident Workflow

## Milestone 9 — Zayd 1.0

- Public Release
- Versioned Documentation
- Migration Guide
- Roadmap
- Community Support

Task execution ให้ยึด [`../../tasks/00_task_index.md`](../../tasks/00_task_index.md)

---

# 50. สรุปการออกแบบ Open Source

Zayd ต้องเป็นแพลตฟอร์มที่แยกโค้ด ข้อมูล และ provider ออกจากกันอย่างชัดเจน:

```text
Open-source platform
        +
Plugin-based providers
        +
Self-hosted Local-first RAG
        +
Optional External APIs
        +
Human Review Workflow
        +
Separate Licensed Datasets
```

ระบบจึงต้องสามารถ:

- ติดตั้งและใช้งานแบบ Self-host
- ใช้ Cloud Services เป็นทางเลือก
- สร้างโมดูลเชิงพาณิชย์บน interface เดียวกัน
- เปลี่ยนโมเดลและ provider ได้
- ตรวจสอบสิทธิ์ข้อมูลก่อนจัดเก็บและค้นคืน
- ตรวจคำตอบและ citation ย้อนหลังได้
- รองรับภาษาและมัซฮับเพิ่มเติมในอนาคต
- รักษาความปลอดภัยและความเป็นส่วนตัวโดยค่าเริ่มต้น

> Zayd ไม่ใช่เพียง chatbot แต่เป็น Open-source Knowledge Governance, Retrieval, Review and Answering Platform สำหรับความรู้อิสลามภาษาไทย
