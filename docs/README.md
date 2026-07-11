# Zayd Documentation Index

เอกสารชุดนี้เป็น **Baseline ก่อนเริ่ม Coding** ของโครงการ **Zayd — Thai Islamic Knowledge Assistant** ใช้เป็นแหล่งอ้างอิงหลักสำหรับ Product Owner, Technical Lead, AI Coding Agent, ผู้ตรวจทานเนื้อหา และคณะผู้รู้

> Zayd เป็นผู้ช่วยค้นคว้าความรู้อิสลามที่ตอบพร้อมหลักฐาน ไม่ใช่มุฟตี AI และไม่ใช่ระบบออกฟัตวาอัตโนมัติ

## เวอร์ชัน Baseline

- Documentation baseline: **v1.4**
- ครอบคลุม: Project Charter, Master Development Plan, PRD, SRS, Architecture, Governance, Security, Evaluation และ AI Coding Policy
- งานพัฒนาอ้างอิงจาก: [`../tasks/00_task_index.md`](../tasks/00_task_index.md)

## ลำดับการอ่านที่แนะนำ

1. [Project Charter](00_project/00_project_charter.md)
2. [Master Development Plan](00_project/01_master_development_plan.md)
3. [Product Requirements Document](01_product/PRD.md)
4. [Software Requirements Specification — Full SRS 1.1](02_requirements/SRS.md)
5. [Requirements Traceability Matrix](02_requirements/traceability_matrix.md)
6. [System Architecture](03_architecture/system_architecture.md)
7. นโยบายข้อมูล ศาสนา ความปลอดภัย และการประเมิน
8. [AI Coding Agent Policy](09_development/ai_coding_agent_policy.md)
9. [Task Index](../tasks/00_task_index.md)

---

## 00 — Project

เอกสารระดับโครงการ ใช้กำหนดเป้าหมาย ขอบเขต ทิศทาง และการตัดสินใจหลัก

- [Project Charter](00_project/00_project_charter.md)
- [Master Development Plan](00_project/01_master_development_plan.md)
- [Glossary](00_project/04_glossary.md)
- [Decision Log](00_project/05_decisions_log.md)

## 01 — Product

เอกสารความต้องการเชิงผลิตภัณฑ์ กลุ่มผู้ใช้ ขอบเขต MVP และตัวชี้วัดความสำเร็จ

- [Product Requirements Document — Full PRD 1.1](01_product/PRD.md)
- [Archived Compact PRD 1.0](01_product/archive/PRD_v1.0_compact.md)

## 02 — Requirements

ข้อกำหนดระบบที่ทีมพัฒนาและ AI Coding Agent ต้องปฏิบัติตาม

- [Requirements Folder Guide](02_requirements/README.md)
- [Software Requirements Specification — Full SRS 1.1](02_requirements/SRS.md)
- [SRS Summary 1.0](02_requirements/SRS_summary.md)
- [Requirements Traceability Matrix](02_requirements/traceability_matrix.md)
- [Archived Compact SRS 1.0](02_requirements/archive/SRS_v1.0_compact.md)

## 03 — Architecture

สถาปัตยกรรมหลักและ Architecture Decision Records (ADR)

- [System Architecture](03_architecture/system_architecture.md)
- [ADR-001: Greenfield Core + Selective Reuse](03_architecture/adr/ADR-001_greenfield_selective_reuse.md)
- [ADR-002: PostgreSQL + pgvector for MVP](03_architecture/adr/ADR-002_postgresql_pgvector.md)
- [ADR-003: Local-first RAG](03_architecture/adr/ADR-003_local_first_rag.md)

## 03a — Architecture Deep-Dives

- [Answer Orchestrator](architecture/answer-orchestrator.md)
- [Chunking](architecture/chunking.md)
- [Citation Registry](architecture/citation-registry.md)
- [Citation Verification](architecture/citation-verification.md)
- [Database](architecture/database.md)
- [Evidence Sufficiency](architecture/evidence-sufficiency.md)
- [Full-text Search](architecture/full-text-search.md)
- [Guest Sessions](architecture/guest-sessions.md)
- [Hybrid Search](architecture/hybrid-search.md)
- [License Policy Engine](architecture/license-policy-engine.md)
- [Metadata Extraction](architecture/metadata-extraction.md)
- [Monorepo Structure](architecture/monorepo.md)
- [Object Storage](architecture/object-storage.md)
- [Persistence](architecture/persistence.md)
- [pgvector Search](architecture/pgvector-search.md)
- [Publishing Pipeline](architecture/publishing-pipeline.md)
- [Query Expansion](architecture/query-expansion.md)
- [Question Classification](architecture/question-classification.md)
- [Review Task Creation](architecture/review-task-creation.md)
- [State Machines](architecture/state-machines.md)
- [Text Normalization](architecture/text-normalization.md)

## 04 — API

- [API Overview](api/README.md)
- [Authentication](api/authentication.md)
- [Authorization](api/authorization.md)
- [Document Review](api/document-review.md)
- [Document Upload](api/document-upload.md)
- [Feedback](api/feedback.md)
- [Licenses](api/licenses.md)
- [Review Queue](api/review-queue.md)
- [Sources](api/sources.md)
- [Streaming Chat](api/streaming-chat.md)

## 05 — Data Governance

นโยบายสิทธิ์ข้อมูล การจัดเก็บ การสร้าง Embedding และการเผยแพร่ Dataset

- [Data License Policy](05_data/license_policy.md)
- [Dataset Governance](evaluation/dataset-governance.md)

## 06 — Islamic Governance

นโยบายกำกับเนื้อหาศาสนา การแยกมัซฮับ การตรวจทานโดยผู้รู้ และความปลอดภัยของคำตอบ

- [Madhhab Policy](06_islamic_governance/madhhab_policy.md)
- [Scholar Review Policy](06_islamic_governance/scholar_review_policy.md)
- [Answer Safety Policy](06_islamic_governance/answer_safety_policy.md)

## 07 — Security

ข้อกำหนดความปลอดภัยของแอป ระบบ AI, RAG, Provider, เอกสาร และข้อมูลผู้ใช้

- [Security Architecture](07_security/security_architecture.md)
- [Authentication](security/authentication.md)
- [Audit Logging](security/audit-logging.md)
- [File Scanning](security/file-scanning.md)
- [Hardening Checklist](security/hardening.md)
- [MFA](security/mfa.md)
- [RBAC](security/rbac.md)
- [Threat Model](security/threat-model.md)
- [Release Review & Penetration Test](security/release-review.md)

## 08 — Evaluation

เกณฑ์ประเมิน Retrieval, Citation, Safety, Abstention และคุณภาพคำตอบภาษาไทย

- [Evaluation Plan](08_evaluation/evaluation_plan.md)
- [Benchmark Runner](evaluation/benchmark-runner.md)
- [Citation Metrics](evaluation/citation-metrics.md)
- [Data Schema](evaluation/data-schema.md)
- [Dataset Governance](evaluation/dataset-governance.md)
- [Incident Regressions](evaluation/incident-regressions.md)
- [Retrieval Metrics](evaluation/retrieval-metrics.md)
- [Safety Metrics](evaluation/safety-metrics.md)

## 09 — Development

กฎการใช้ AI Coding Agent และข้อกำหนดก่อนแก้ไขระบบสำคัญ

- [AI Coding Agent Policy](09_development/ai_coding_agent_policy.md)
- [CI Pipeline](development/ci.md)
- [Commands](development/commands.md)
- [Configuration](development/configuration.md)
- [Demo Data](development/demo-data.md)
- [Docker](development/docker.md)
- [Embedding Providers](development/embedding-providers.md)
- [Migrations](development/migrations.md)
- [Parser Plugins](development/parser-plugins.md)
- [Provider SDK](development/provider-sdk.md)
- [Python Guide](development/python.md)
- [Reranker Providers](development/reranker-providers.md)
- [TypeScript Guide](development/typescript.md)

## 10 — Deployment

- [Deployment Overview](deployment/README.md)
- [Minimal Self-host](deployment/minimal-self-host.md)
- [Minio Setup](deployment/minio.md)
- [Production](deployment/production.md)

## 11 — Operations

- [Answer Invalidation](operations/answer-invalidation.md)
- [Audit Retention](operations/audit-retention.md)
- [Backup & Restore](operations/backup-restore.md)
- [Content Suspension](operations/content-suspension.md)
- [Disaster Recovery](operations/disaster-recovery.md)
- [Incident Management](operations/incident-management.md)
- [Logging](operations/logging.md)
- [Metrics](operations/metrics.md)
- [Tracing](operations/tracing.md)

## 12 — User Guides

- [Admin Dashboard](user/admin-dashboard.md)
- [Admin MFA](user/admin-mfa.md)
- [Conversation History](user/conversation-history.md)
- [Document Review](user/document-review.md)
- [Evaluation Dashboard](user/evaluation-dashboard.md)
- [Feedback Review](user/feedback-review.md)
- [Preferences](user/preferences.md)
- [Provider Management](user/provider-management.md)
- [Report Answer](user/report-answer.md)
- [Reviewer Dashboard](user/reviewer-dashboard.md)
- [Saved Answers](user/saved-answers.md)
- [Scholar Approval](user/scholar-approval.md)
- [Source & License Admin](user/source-license-admin.md)
- [User & Role Admin](user/user-role-admin.md)

## 13 — Governance

- [Governance Overview](governance/README.md)
- [Answer Safety Policy](governance/answer-safety-policy.md)
- [Data Licenses](governance/data-licenses.md)
- [Prompt Management](governance/prompt-management.md)
- [Scholar Approval](governance/scholar-approval.md)
- [Source Policy](governance/source-policy.md)

## 14 — Frontend

- [Chat Interface](frontend/chat.md)
- [Citation Cards](frontend/citations.md)
- [User App Shell](frontend/user-app.md)

## 15 — Pilot

- [Pilot Environment](pilot/environment.md)
- [Scholar Pilot Workflow](pilot/scholar-workflow.md)
- [User Pilot Workflow](pilot/user-workflow.md)

## 16 — Testing

- [Performance & Load Testing](testing/performance.md)

## 17 — Releases

- [Zayd 1.0 Release](releases/1.0.md)
- [SBOM](releases/sbom.md)

---

## ความสัมพันธ์ระหว่างเอกสารกับ Tasks
Project Charter และ Master Plan
        ↓
PRD
        ↓
SRS และ Traceability Matrix
        ↓
Architecture / Governance / Security / Evaluation
        ↓
tasks/00_task_index.md
        ↓
Task รายไฟล์ EPIC-00 ถึง EPIC-14
        ↓
Implementation, Review, Pilot และ Release
```

กฎการทำงาน:

- Task ต้องอ้างอิง Requirement ID จาก PRD/SRS เมื่อเกี่ยวข้อง
- งานด้านสถาปัตยกรรมต้องสอดคล้องกับ ADR ที่อนุมัติแล้ว
- งานด้านข้อมูลต้องผ่าน Data License Policy
- งานด้านเนื้อหาศาสนาต้องผ่าน Islamic Governance Policy ที่เกี่ยวข้อง
- งานด้าน AI/RAG ต้องผ่าน Evaluation Plan และ Release Quality Gates
- หากข้อกำหนดขัดกัน ให้เปิด RFC หรือบันทึก Decision Log ก่อนแก้โค้ด

## ลำดับการอนุมัติเอกสาร

1. Product Owner ตรวจ Project Charter, Master Development Plan และ PRD
2. Technical Lead ตรวจ SRS, Traceability Matrix, System Architecture และ ADR
3. Data Steward ตรวจ Data License Policy
4. Islamic Content Board ตรวจ Madhhab Policy, Scholar Review Policy และ Answer Safety Policy
5. Security Lead ตรวจ Security Architecture
6. QA/Evaluation Lead ตรวจ Evaluation Plan
7. Maintainers ตรวจ AI Coding Agent Policy และความพร้อมของ Tasks

เอกสารที่ยังไม่ผ่านขั้นตอนนี้ให้คงสถานะ `DRAFT` และห้ามใช้เป็นเหตุผลเปลี่ยนพฤติกรรม Production โดยไม่มีการอนุมัติ

## สถานะเอกสาร

ใช้สถานะมาตรฐาน:

- `DRAFT` — อยู่ระหว่างจัดทำ
- `IN_REVIEW` — อยู่ระหว่างตรวจทาน
- `CHANGES_REQUESTED` — ต้องแก้ไขก่อนตรวจใหม่
- `APPROVED` — อนุมัติให้ใช้เป็นข้อกำหนด
- `SUPERSEDED` — มีเอกสารใหม่แทนแล้ว
- `ARCHIVED` — เก็บเพื่ออ้างอิงย้อนหลัง

## การแก้ไขเอกสาร

การเปลี่ยนแปลงต่อไปนี้ต้องบันทึกใน Decision Log และอาจต้องมี ADR/RFC:

- เปลี่ยนขอบเขต MVP หรือ Product Positioning
- เปลี่ยนฐานข้อมูลหรือ Vector Store หลัก
- เปลี่ยนแนวทาง Local-first RAG
- เปลี่ยน License ของ Source Code หรือ Dataset
- เปลี่ยน Madhhab Policy หรือ Answer Safety Policy
- เปลี่ยน Release Quality Gate
- เพิ่ม External Provider ที่มีผลต่อข้อมูลส่วนตัวหรือสิทธิ์การจัดเก็บ

## เอกสารที่ต้องเพิ่มในระยะถัดไป

ก่อน Production ควรมีอย่างน้อย:

- API Design and OpenAPI Guide
- Database Design and Migration Policy
- Threat Model
- Privacy and Data Retention Policy
- Prompt Injection Defense
- Incident Response Plan
- Backup and Disaster Recovery Runbook
- Deployment and Self-host Guide
- Reviewer Handbook
- Dataset Manifest Specification
- Zayd-IslamicQA-TH Benchmark Specification

