# แผนแม่บทการพัฒนา Zayd ตั้งแต่เริ่มโครงการจนเปิดให้บริการจริง

## ข้อมูลเอกสาร

| รายการ | ค่า |
|---|---|
| โครงการ | Zayd — Thai Islamic Knowledge Assistant |
| ชื่อเอกสาร | Master Development Plan |
| เวอร์ชัน | 1.0 |
| วันที่ | 5 กรกฎาคม 2026 |
| สถานะ | DRAFT FOR REVIEW |
| เจ้าของเอกสาร | Product Owner |
| ผู้ร่วมอนุมัติ | Technical Lead, Islamic Content Board, Data Steward, Security Lead, QA/Evaluation Lead |
| เอกสารต้นทาง | Project Charter, PRD 1.1, SRS 1.1, System Architecture, Governance Policies และ Task Index |

---

## 1. วัตถุประสงค์

เอกสารนี้เป็นแผนแม่บทระดับโครงการสำหรับพัฒนา **Zayd** ตั้งแต่การกำหนดวิสัยทัศน์และนโยบาย การรวบรวมข้อมูล การพัฒนาระบบ AI และ RAG การตรวจทานโดยผู้รู้ การทดสอบแบบปิด จนถึงการเปิดบริการจริงและการขยายระบบในระยะต่อไป

แผนนี้ทำหน้าที่เชื่อมเอกสารระดับผลิตภัณฑ์และเทคนิคเข้ากับงานพัฒนาจริง โดยตอบคำถามหลักต่อไปนี้:

1. โครงการต้องทำอะไรตามลำดับ
2. ผลลัพธ์ที่ต้องได้ในแต่ละระยะคืออะไร
3. ใครเป็นผู้รับผิดชอบและผู้อนุมัติ
4. เงื่อนไขใดต้องผ่านก่อนเข้าสู่ระยะถัดไป
5. ความเสี่ยงสำคัญต้องควบคุมอย่างไร
6. เมื่อใดจึงถือว่า Zayd พร้อมเปิดให้บริการจริง

---

## 2. วิสัยทัศน์ของ Zayd

> ทำให้มุสลิมในประเทศไทยเข้าถึงความรู้อิสลามที่ตรวจสอบได้ เข้าใจง่าย และเคารพความแตกต่างทางวิชาการ โดยใช้ AI เป็นเครื่องมือช่วยค้นคว้า ไม่ใช่ผู้แทนนักวิชาการศาสนา

Zayd ต้องถูกออกแบบให้เป็น **ผู้ช่วยค้นคว้าความรู้อิสลามภาษาไทย** ไม่ใช่มุฟตี AI และไม่ใช่ระบบออกฟัตวาอัตโนมัติ

ระบบต้องมีคุณสมบัติสำคัญดังนี้:

- ตอบคำถามเป็นภาษาไทยอย่างเข้าใจง่าย
- แสดงข้อความอาหรับและคำแปลเมื่อเกี่ยวข้อง
- แสดงแหล่งอ้างอิงที่ตรวจสอบย้อนกลับได้
- แยกทัศนะตามมัซฮับอย่างชัดเจน
- ใช้มัซฮับชาฟิอีเป็นค่าเริ่มต้นที่ผู้ใช้เปลี่ยนได้
- งดตอบเมื่อไม่มีหลักฐานเพียงพอ
- ส่งต่อคำถามความเสี่ยงสูงให้ผู้รู้
- ใช้ข้อมูลที่ผ่านการตรวจทานและมีสิทธิ์ใช้งาน
- ติดตั้งแบบ Self-hosted และเปลี่ยน Provider ได้
- ตรวจย้อนหลังได้ว่าแต่ละคำตอบใช้ข้อมูล โมเดล Prompt และ Policy เวอร์ชันใด

---

## 3. หลักการกำกับโครงการ

ทุกระยะของโครงการต้องยึดหลักต่อไปนี้

### 3.1 Evidence First

ระบบต้องค้นหลักฐานก่อนสร้างคำตอบ หากหลักฐานไม่พอ ต้องค้นเพิ่ม ลดขอบเขตคำตอบ หรือปฏิเสธการตอบ

### 3.2 Citation Required

ข้อกล่าวอ้างทางศาสนาที่สำคัญต้องเชื่อมกับ Citation ที่มีอยู่จริงในระบบ ห้ามให้โมเดลสร้างเลขอายะฮ์ เลขหะดีษ ชื่อหนังสือ หรือเลขหน้าขึ้นเอง

### 3.3 Scholar in the Loop

เอกสารฟิกฮ์ คำแปล ข้อมูลที่มีความเห็นต่าง และเนื้อหาความเสี่ยงสูงต้องผ่านกระบวนการตรวจและอนุมัติโดยผู้รู้ก่อนเผยแพร่

### 3.4 Madhhab Aware

ระบบต้องไม่ผสมคำวินิจฉัยของหลายมัซฮับโดยไม่ระบุ และต้องเก็บมัซฮับเป็น Metadata ของข้อมูลตั้งแต่ขั้นตอนนำเข้า

### 3.5 Thai Context

ภาษา คำศัพท์ ตัวอย่าง กฎหมาย ระเบียบฮาลาล และช่องทางส่งต่อผู้รู้ต้องเหมาะกับบริบทประเทศไทย

### 3.6 Open-source Code, Licensed Data

โค้ดของแพลตฟอร์มสามารถเปิดซอร์สได้ แต่ข้อมูลศาสนาแต่ละชุดต้องใช้ License ของตนเอง และต้องไม่รวมข้อมูลที่ไม่มีสิทธิ์แจกจ่ายใน Release สาธารณะ

### 3.7 Auditable by Design

การนำเข้า การแก้ไข การอนุมัติ การเผยแพร่ การเรียกโมเดล และการสร้างคำตอบต้องมีประวัติที่ตรวจสอบย้อนหลังได้

### 3.8 Privacy and Safety by Default

บทสนทนาผู้ใช้ต้องไม่ถูกนำไปฝึกโมเดลโดยอัตโนมัติ ข้อมูลส่วนบุคคลต้องถูกลดทอนก่อนส่งไปยัง Provider ภายนอกเมื่อทำได้ และคำถามความเสี่ยงสูงต้องผ่าน Policy เฉพาะ

---

## 4. รูปแบบการพัฒนา

Zayd ใช้แนวทาง:

> **Greenfield Core + Selective Open-source Reuse**

หมายความว่า:

- Domain model, Reviewer Workflow, License Registry, Citation Registry, Safety Policy และฐานข้อมูลหลักสร้างใหม่สำหรับ Zayd
- ศึกษาหรือนำบางโมดูลจากโครงการ Open Source เช่น Ansari และ Criterion มาใช้เมื่อ License และคุณภาพเหมาะสม
- ทุกโค้ดที่นำมาดัดแปลงต้องบันทึกแหล่งที่มา Commit Hash และ License ใน `CODE_PROVENANCE.md`
- ห้าม Fork โครงการอื่นทั้งระบบแล้วรื้อโครงสร้างหลัก เพราะจะทำให้ Zayd ผูกกับ Architecture และ Provider ของโครงการต้นทาง

สัดส่วนโดยประมาณ:

| ประเภท | สัดส่วนเป้าหมาย |
|---|---:|
| สร้างใหม่สำหรับ Zayd | 65–75% |
| ดัดแปลงจาก Open Source | 20–30% |
| นำมาใช้ตรง ๆ | 5–10% |

---

## 5. ขอบเขต Zayd 1.0

### 5.1 เนื้อหาที่รองรับเต็มรูปแบบ

- หลักศรัทธาพื้นฐาน
- ความสะอาดและน้ำละหมาด
- การอาบน้ำยกหะดัษ
- การละหมาด
- การถือศีลอด
- มารยาทและจริยธรรมพื้นฐาน
- ดุอาอ์พื้นฐาน
- อัลกุรอานและหะดีษที่เกี่ยวข้อง
- ฟิกฮ์มัซฮับชาฟิอีในหัวข้อข้างต้น

### 5.2 ความสามารถหลัก

- Mobile-first Web Application / PWA
- Guest Mode และบัญชีผู้ใช้
- ถามตอบภาษาไทยแบบ Streaming
- Local-first Hybrid RAG
- External API Fallback แบบมี Storage Policy
- Citation Registry และ Citation Verification
- Evidence Sufficiency Engine
- Madhhab Routing
- Risk Classification และ Abstention
- Reviewer Portal
- Admin Portal
- Document Ingestion และ Approval Workflow
- Source และ License Registry
- Feedback และ Incident Management
- Thai Islamic Benchmark
- Self-host Deployment

### 5.3 สิ่งที่ยังไม่รวมใน 1.0

- Native Android/iOS
- LINE Bot
- Public API และ MCP สำหรับบุคคลทั่วไป
- ระบบ Billing
- เครื่องคำนวณมรดกและซะกาตขั้นสูง
- รองรับทุกมัซฮับและทุกหัวข้ออย่างสมบูรณ์
- ระบบออกฟัตวาเฉพาะบุคคลอัตโนมัติ

---

## 6. โครงสร้างทีมขั้นต่ำ

| บทบาท | จำนวนขั้นต่ำ | ความรับผิดชอบหลัก |
|---|---:|---|
| Product Owner | 1 | Scope, Priority, Acceptance และ Product Decisions |
| Technical Lead | 1 | Architecture, Code Quality, ADR และ Technical Gate |
| Backend/RAG Developer | 1–2 | API, Retrieval, Orchestrator, Data Pipeline |
| Frontend Developer | 1 | User PWA, Reviewer และ Admin UI |
| DevOps/Security | 1 แบบ Part-time | CI/CD, Deployment, Security และ Backup |
| QA/Evaluation Lead | 1 | Test Strategy, Benchmark และ Release Gate |
| Senior Scholar | 1–2 | Religious Policy และ Final Content Approval |
| Thai Religious Reviewer | อย่างน้อย 2 | ตรวจคำแปล เนื้อหา และบริบทไทย |
| Arabic Reviewer | อย่างน้อย 1 | ตรวจต้นฉบับภาษาอาหรับและ Citation |
| Data Steward | 1 | Source, License, Dataset Manifest และ Provenance |
| Data Operator | 1 | นำเข้าและเตรียมเอกสาร |

คนหนึ่งสามารถรับหลายบทบาทในระยะแรกได้ แต่ต้องรักษา Separation of Duties โดยเฉพาะ:

- ผู้พัฒนาไม่ควรเป็นผู้อนุมัติเนื้อหาศาสนาเพียงคนเดียว
- ผู้ที่อัปโหลดหรือแก้เอกสารสำคัญไม่ควรอนุมัติงานของตนเอง
- ผู้อนุมัติ Release ต้องมีตัวแทน Product, Technical, Security และ Islamic Content

---

# 7. แผนพัฒนาเป็นระยะ

## Phase 0 — Governance และการตั้งโครงการ

### เป้าหมาย

กำหนดอำนาจตัดสินใจ ขอบเขตผลิตภัณฑ์ นโยบายศาสนา สิทธิ์ข้อมูล และวิธีเปิดซอร์สก่อนเริ่มเขียนระบบ

### งานหลัก

- จัดตั้ง Product Owner และทีมหลัก
- จัดตั้ง Islamic Content Board
- กำหนดมัซฮับเริ่มต้นและนโยบายแสดงความเห็นต่าง
- กำหนดคำถามที่ AI ห้ามวินิจฉัยเอง
- กำหนด License ของ Source Code, Documentation และ Dataset
- กำหนด Governance, Contribution และ Security Disclosure
- อนุมัติ Project Charter

### ผลลัพธ์

- `docs/00_project/00_project_charter.md`
- `docs/06_islamic_governance/madhhab_policy.md`
- `docs/06_islamic_governance/scholar_review_policy.md`
- `docs/06_islamic_governance/answer_safety_policy.md`
- `docs/05_data/license_policy.md`
- Governance และ Open-source Policy

### Exit Gate

- มีผู้รับผิดชอบและผู้มีอำนาจอนุมัติเป็นลายลักษณ์อักษร
- มีนโยบายมัซฮับและคำถามความเสี่ยงสูง
- ตัดสินใจเรื่อง License และ Trademark แล้ว
- ไม่มีข้อขัดแย้งพื้นฐานที่ทำให้เริ่มพัฒนาไม่ได้

---

## Phase 1 — Product, Requirements และ Architecture Baseline

### เป้าหมาย

แปลงวิสัยทัศน์เป็นข้อกำหนดที่ทดสอบได้และสถาปัตยกรรมที่ทีมพัฒนาใช้ร่วมกัน

### งานหลัก

- จัดทำ PRD
- จัดทำ SRS
- กำหนด User Personas และ User Journeys
- กำหนด Functional และ Non-functional Requirements
- สร้าง Requirements Traceability Matrix
- ออกแบบ System Architecture
- ออกแบบ Open-source Repository และ Plugin Architecture
- บันทึก Architecture Decisions ผ่าน ADR
- แตกงานเป็น Epic, Feature และ Task

### ผลลัพธ์

- `docs/01_product/PRD.md`
- `docs/02_requirements/SRS.md`
- `docs/02_requirements/traceability_matrix.md`
- `docs/03_architecture/system_architecture.md`
- ADR สำคัญ
- `tasks/00_task_index.md`
- Task Files ครบตามขอบเขต 1.0

### Exit Gate

- Requirement สำคัญทุกข้อมี Acceptance Criteria
- Requirement เชื่อมกับ Task และ Test Plan ได้
- Architecture ผ่าน Technical Review
- Open Questions ที่กระทบ Critical Path ถูกปิดหรือมี Owner

---

## Phase 2 — Open-source Foundation และ Development Environment

### เป้าหมาย

สร้าง Repository ที่ Contributor ภายนอกสามารถ Clone, Build, Test และเริ่มพัฒนาได้โดยไม่ต้องใช้บริการ Proprietary

### งานหลัก

- สร้าง Monorepo
- เพิ่ม Apache-2.0, NOTICE และ Third-party Notices
- เพิ่ม CONTRIBUTING, GOVERNANCE, SECURITY และ CODEOWNERS
- ตั้งค่า TypeScript และ Python Tooling
- สร้าง Docker Compose สำหรับ Development
- ตั้งค่า PostgreSQL + pgvector, Redis และ MinIO
- สร้าง `.env.example`, Config Validation และ Makefile
- สร้าง CI เบื้องต้น

### ผลลัพธ์

- Repository Structure พร้อมใช้งาน
- Local Development Profile
- Lint, Typecheck, Test และ Build Commands
- Contributor Documentation

### Exit Gate

- Contributor ใหม่ทำตาม README แล้วเริ่มระบบได้
- CI ผ่านบน Repository ว่างหรือ Skeleton
- ไม่มี Secret หรือ Licensed Dataset ใน Source Control
- Build ไม่ผูกกับ Provider รายเดียว

---

## Phase 3 — Core Domain, Database, Authentication และ Audit

### เป้าหมาย

สร้างแกนข้อมูลและระบบสิทธิ์ที่รองรับ Lifecycle ของข้อมูลศาสนาและการตรวจย้อนหลัง

### งานหลัก

- ออกแบบและสร้าง Database Schema
- สร้าง Migration และ Repository Layer
- สร้าง Authentication และ Guest Session
- สร้าง RBAC และ MFA สำหรับผู้มีสิทธิ์สูง
- สร้าง Immutable Audit Log
- สร้าง Document State Machine
- สร้าง Source และ License Registry
- สร้าง Deterministic License Policy Engine

### ผลลัพธ์

- Database Migration รุ่นแรก
- Authentication/RBAC APIs
- Audit Infrastructure
- Source/License Management

### Exit Gate

- Permission Tests ผ่าน
- State Transition ที่ไม่ถูกต้องถูกปฏิเสธ
- เอกสารที่ License ไม่อนุญาตไม่สามารถ Publish ได้
- Audit Log ครอบคลุมการเปลี่ยนแปลงสำคัญ

---

## Phase 4 — Data Acquisition และ Knowledge Governance

### เป้าหมาย

สร้างคลังข้อมูลเริ่มต้นที่มีสิทธิ์ชัดเจน คุณภาพตรวจสอบได้ และเหมาะกับผู้ใช้ไทย

### งานหลัก

- สำรวจอัลกุรอาน คำแปลไทย หะดีษ ตัฟซีร และฟิกฮ์ชาฟิอี
- ขออนุญาตเจ้าของข้อมูลและ API Provider
- สร้าง Dataset Manifest
- บันทึก Source, Owner, License และ Attribution
- กำหนด Canonical Reference
- กำหนด Metadata Schema
- จัดลำดับ Source Reliability
- สร้าง Corpus เริ่มต้นเฉพาะหัวข้อ Vertical Slice

### ผลลัพธ์

- Source Registry ที่ผ่านการตรวจ
- License Evidence
- Approved Dataset Manifests
- Corpus ชุดแรกสำหรับหัวข้อความสะอาดและน้ำละหมาด

### Exit Gate

- ทุก Source มี Owner และ License Status
- ไม่มีข้อมูลสถานะ `UNKNOWN`, `PROHIBITED` หรือ `EXPIRED` ใน Production Corpus
- มีผู้รู้รับรอง Source ชุดเริ่มต้น
- มีข้อมูลเพียงพอสำหรับ Vertical Slice

---

## Phase 5 — Document Ingestion และ Reviewer Portal

### เป้าหมาย

สร้างวงจรตั้งแต่อัปโหลดเอกสารจนผู้รู้อนุมัติและเผยแพร่เข้า Production RAG

### งานหลัก

- อัปโหลดและเก็บไฟล์ใน Object Storage
- Malware Scan และ Duplicate Check
- Parser Framework สำหรับ PDF, DOCX, TXT, Markdown, HTML, JSON และ CSV
- Thai/Arabic Normalization โดยเก็บต้นฉบับไว้เสมอ
- AI-assisted Metadata Extraction พร้อมสถานะ `UNVERIFIED`
- Review Queue
- Document Review Workspace
- Translation Review
- Scholar Approval และ Two-level Approval
- Publish, Suspend, Rollback และ Re-index

### ผลลัพธ์

- Ingestion Pipeline
- Reviewer Portal รุ่นแรก
- Scholar Approval Workflow
- Published Document Versioning

### Exit Gate

- ไม่มีเอกสารเข้าสู่ Production RAG โดยไม่ผ่าน Approval
- Reviewer เห็นต้นฉบับ ข้อความสกัด Metadata และ Diff
- Suspend เอกสารแล้ว Retrieval หยุดใช้ทันที
- Publish Failure ไม่ทำให้เกิดข้อมูลครึ่งชุด

---

## Phase 6 — Local-first Retrieval Engine

### เป้าหมาย

ค้นข้อมูลภาษาไทยและอาหรับได้แม่นยำ พร้อมกรองตามมัซฮับ Source และสถานะการอนุมัติ

### งานหลัก

- Chunking ตามอายะฮ์ หะดีษ หัวข้อฟิกฮ์ และโครงสร้างเอกสาร
- Multilingual Embedding Provider
- PostgreSQL Full-text Search
- pgvector Search
- Exact Reference Search
- Hybrid Search
- Metadata Filtering
- Multilingual Query Expansion ไทย–อาหรับ–อังกฤษ
- Reranker
- Evidence Sufficiency Engine
- Retrieval Trace

### ผลลัพธ์

- Local Retrieval API
- Hybrid Search Configuration
- Evidence Status: `SUFFICIENT`, `PARTIALLY_SUFFICIENT`, `INSUFFICIENT`, `CONFLICTING`
- Retrieval Benchmark รุ่นแรก

### Exit Gate

- Production Search ใช้เฉพาะ `PUBLISHED`
- Retrieval Recall@5 ใน Vertical Slice ผ่านเป้าหมายที่กำหนด
- สามารถค้นคำศัพท์ศาสนาไทยและอาหรับได้
- หลักฐานขัดแย้งถูกตรวจพบและไม่ถูกรวมเป็นคำตอบเดียวโดยอัตโนมัติ

---

## Phase 7 — AI Orchestrator, Safety และ Citation

### เป้าหมาย

สร้างกระบวนการตอบที่ใช้หลักฐานจริง ตรวจ Citation และงดตอบเมื่อจำเป็น

### งานหลัก

- Provider SDK สำหรับ LLM, Embedding, Reranker และ Knowledge Provider
- Local LLM และ OpenAI-compatible Adapter
- Language, Intent, Topic, Madhhab และ Risk Classification
- Risk Policy Engine
- Query Expansion และ Retrieval Loop
- Answer Generation จาก Evidence
- Citation Registry
- Deterministic Citation Checks
- Claim-support Verification
- Answer Revision หรือ Abstention
- Prompt และ Policy Versioning
- Streaming Chat API

### ผลลัพธ์

- Structured Answer API
- Traceable Orchestration Workflow
- Citation Verification Engine
- High-risk Routing
- Abstention Mechanism

### Exit Gate

- โมเดลอ้างได้เฉพาะ Citation ID ที่ Backend ส่งให้
- Fabricated Citation เป็นศูนย์ในชุดทดสอบหลัก
- คำถามความเสี่ยงสูงถูก Route ตาม Policy
- คำตอบที่ Evidence ไม่พอถูกจำกัดหรืองดตอบ
- ทุกคำตอบบันทึก Model, Prompt, Policy และ Retrieval Version

---

## Phase 8 — User PWA, Reviewer และ Admin Experience

### เป้าหมาย

ส่งมอบประสบการณ์ใช้งานที่เหมาะกับโทรศัพท์มือถือและเครื่องมือหลังบ้านที่ทีมดูแลระบบใช้จริงได้

### งานหลัก

#### User PWA

- Chat Interface
- Streaming Status
- Citation Cards
- Source Detail
- Madhhab และ Answer Preferences
- History, Saved Answers และ No-history Mode
- Feedback Form
- PWA และ Accessibility

#### Reviewer Portal

- Review Dashboard
- Document Review Workspace
- Scholar Approval Workspace
- Answer Feedback Review

#### Admin Portal

- User/Role Management
- Source/License Management
- Provider/Model Configuration
- Prompt/Policy Version Management
- Queue, Cost, Health และ Incident Dashboard

### ผลลัพธ์

- End-to-end Vertical Slice ที่ผู้ใช้ถามและผู้ตรวจย้อนกลับได้
- Mobile-first PWA
- Reviewer/Admin Portals

### Exit Gate

- User Journey หลักผ่าน E2E Test
- Thai Typography และ Arabic RTL แสดงถูกต้อง
- ผู้ใช้เปิด Source และ Citation Detail ได้
- Admin ไม่เห็น Secret แบบ Plaintext
- Reviewer สามารถปิด Feedback Ticket ได้ครบ Workflow

---

## Phase 9 — Feedback, Incident และ Continuous Improvement

### เป้าหมาย

เปลี่ยนคำตอบผิดและปัญหาที่พบจากผู้ใช้ให้เป็นการแก้ข้อมูล ระบบ และ Regression Test

### งานหลัก

- Feedback API และ Review Queue
- Incident Severity P0–P3
- Answer Invalidation
- Document Suspension
- Root Cause Analysis
- Notification สำหรับเหตุการณ์สำคัญ
- Convert Incident to Evaluation Case
- Regression Test Automation

### ผลลัพธ์

- Feedback-to-Fix Workflow
- Incident Timeline
- Invalid Answer Warning
- Regression Dataset

### Exit Gate

- P0/P1 Incident สามารถระงับ Source/Answer ได้อย่างรวดเร็ว
- Incident ที่ยืนยันแล้วถูกเพิ่มเป็น Regression Test
- ผู้ดูแลตรวจได้ว่าคำตอบใดได้รับผลกระทบจาก Citation ที่ถูกระงับ

---

## Phase 10 — Evaluation, Security และ Operational Readiness

### เป้าหมาย

พิสูจน์คุณภาพ ความปลอดภัย และความสามารถในการดูแลระบบก่อนทดสอบกับผู้ใช้จริง

### งานหลัก

#### Evaluation

- Zayd-IslamicQA-TH
- Retrieval Metrics
- Citation Metrics
- Madhhab Consistency
- Safety และ Abstention Metrics
- Thai Readability
- Scholar Evaluation

#### Security

- Threat Model
- Authentication/Authorization Testing
- Prompt Injection Testing
- Malicious Document Testing
- Dependency, Secret, Container และ License Scanning

#### Operations

- OpenTelemetry
- Metrics, Logs และ Traces
- Provider Health และ Circuit Breaker
- Backup และ Restore
- Disaster Recovery Runbook
- Minimal Self-host Profile
- Production Deployment Profile

### ผลลัพธ์

- Evaluation Reports
- Security Review Report
- Monitoring Dashboards
- Backup/Restore Evidence
- Self-host Installation Guide

### Exit Gate

- Citation Correctness ≥ 98%
- Fabricated Citation = 0 ใน Release Gate
- Retrieval Recall@5 ≥ 90% ในหัวข้อ MVP
- High-risk Routing Accuracy ≥ 95%
- ไม่มี Critical Security Issue
- Backup และ Restore Test ผ่าน
- Self-host Installation ผ่านการทดสอบโดยบุคคลที่ไม่ได้สร้างระบบ

---

## Phase 11 — Closed Pilot

### เป้าหมาย

ทดสอบระบบกับผู้รู้ นักเรียนศาสนา และผู้ใช้ทั่วไปในสภาพแวดล้อมควบคุม

### กลุ่ม Pilot

- Senior Scholars และ Reviewers
- ครูสอนศาสนา
- นักเรียนศาสนา
- ผู้ใช้ทั่วไปที่อ่านอาหรับได้
- ผู้ใช้ทั่วไปที่ใช้ภาษาไทยเป็นหลัก
- ผู้เปลี่ยนมานับถืออิสลาม

### งานหลัก

- ตั้ง Pilot Environment แยกจาก Production
- จำกัดจำนวนผู้ใช้และคำถาม
- จัดชุดคำถามทดสอบ
- เก็บ Feedback เชิงคุณภาพและเชิงปริมาณ
- วัด Review Queue และต้นทุนต่อคำตอบ
- แก้ปัญหา P0/P1/P2
- ปรับ Corpus, Retrieval, Prompt และ Policy

### ผลลัพธ์

- Pilot Report
- Scholar Approval Report
- User Experience Findings
- Cost and Performance Report
- Updated Benchmark และ Regression Suite

### Exit Gate

- ไม่มี P0/P1 ค้าง
- คณะผู้รู้เห็นชอบขอบเขตเนื้อหาและข้อจำกัด
- SLA ของ Review Queue อยู่ในระดับที่ทีมดูแลได้
- Product Owner และ Technical Lead อนุมัติเข้าสู่ Public Beta

---

## Phase 12 — Public Beta

### เป้าหมาย

เปิดระบบให้ผู้ใช้ทั่วไปแบบจำกัด เพื่อพิสูจน์ความเสถียรและกระบวนการ Incident ก่อน Release 1.0

### งานหลัก

- เปิด Registration หรือ Waitlist
- กำหนด Rate Limit และ Usage Quota
- เปิด Status Page
- เผยแพร่ Terms, Privacy, AI Limitation และ Source Methodology
- เฝ้าระวัง Incident และ Cost
- ทำ Canary Release สำหรับโมเดล Prompt และ Retrieval Version ใหม่
- ทบทวน Feedback รายสัปดาห์

### ผลลัพธ์

- Public Beta Service
- Production-like Metrics
- Updated Runbooks
- Final Release Candidate

### Exit Gate

- Availability และ Latency ผ่านเป้าหมาย
- Incident Response ทำงานได้จริง
- ไม่มี Restricted Dataset ใน Public Release
- Release Candidate ผ่าน Security และ Evaluation Gates
- Backup/Restore ล่าสุดผ่าน

---

## Phase 13 — Zayd 1.0 Production Release

### เป้าหมาย

เปิด Zayd 1.0 เป็นบริการจริงและเผยแพร่ Open-source Release ที่ติดตั้งได้

### Release Artifacts

- Source Code Tag
- Container Images
- Checksums และ SBOM
- Database Migration Guide
- Release Notes และ Known Issues
- Docker Compose Self-host Profile
- Demo Dataset ที่มีสิทธิ์แจกจ่าย
- Admin, Reviewer และ User Guides
- Backup/Restore Guide
- Security และ Support Policies

### Production Readiness Checklist

- PRD/SRS/Architecture เป็นเวอร์ชัน Approved
- Source และ License Registry ครบสำหรับข้อมูล Production
- Production RAG ใช้เฉพาะเอกสาร `PUBLISHED`
- Citation Verification ผ่าน Quality Gate
- High-risk Policy ผ่านการรับรอง
- Monitoring และ Alerting ทำงาน
- Backup, Restore และ Rollback ทดสอบแล้ว
- ไม่มี P0/P1 ค้าง
- ไม่มี Critical Vulnerability
- Terms, Privacy และ AI Limitation เผยแพร่แล้ว
- ทีม On-call และ Incident Owners ชัดเจน

### ผู้อนุมัติ Release

- Product Owner
- Technical Lead
- Security Lead
- QA/Evaluation Lead
- ตัวแทน Islamic Content Board
- Data Steward ยืนยัน Dataset และ License

---

## Phase 14 — Post-launch Operations และการขยายระบบ

### เป้าหมาย

รักษาคุณภาพหลังเปิดบริการและขยายระบบโดยไม่ลดมาตรฐาน Citation, Safety และ Review

### งานต่อเนื่อง

- ติดตาม Feedback และ Incident
- ทบทวน Source และ License Expiry
- เพิ่มเอกสารและผู้ตรวจ
- ประเมินโมเดลใหม่ก่อนเปลี่ยน Production
- ทำ Regression Test ทุก Release
- ทบทวน Madhhab และ Safety Policy เป็นรอบ
- เผยแพร่ Transparency และ Quality Reports

### Roadmap หลัง 1.0

1. LINE Messaging API
2. Expo Android/iOS
3. ภาษาอังกฤษและมลายู
4. มลายูปาตานี
5. Voice Input และ Text-to-Speech
6. Scholar Workspace และระบบถามผู้รู้
7. Public API และ MCP
8. เครื่องคำนวณซะกาตแบบ Deterministic
9. เครื่องคำนวณมรดกแบบ Rule Engine
10. Institutional Deployment สำหรับโรงเรียน มัสยิด และองค์กร

ทุก Feature ใหม่ต้องผ่าน RFC และประเมินผลกระทบด้าน:

- Religious Content
- Data License
- Security และ Privacy
- Evaluation
- Operational Cost

---

# 8. Vertical Slice แรก

ก่อนสร้างฟังก์ชันครบทุกหมวด ต้องพัฒนา Vertical Slice ที่ทำงานครบวงจรในหัวข้อ:

> **ความสะอาดและน้ำละหมาดตามมัซฮับชาฟิอี**

Vertical Slice ต้องครอบคลุม:

```text
นำเข้าเอกสาร
→ ตรวจ Source และ License
→ Parse และ Normalize
→ Reviewer แก้ไข
→ Senior Scholar อนุมัติ
→ Publish และสร้าง Embedding
→ ผู้ใช้ถามภาษาไทย
→ Hybrid Retrieval
→ ตรวจ Evidence Sufficiency
→ สร้างคำตอบพร้อม Citation
→ ผู้ใช้เปิด Source
→ ผู้ใช้ส่ง Feedback
→ Reviewer ตรวจ Retrieval Trace
→ สร้าง Regression Test
```

ห้ามขยาย Corpus และ Feature จำนวนมากก่อน Vertical Slice นี้ผ่าน E2E Test และ Scholar Review

---

# 9. Critical Path

เส้นทางงานสำคัญของ Zayd คือ:

```text
Governance และ Policies
→ PRD/SRS/Architecture
→ Open-source Foundation
→ Database และ RBAC
→ Source/License Registry
→ Ingestion
→ Scholar Review
→ Publishing
→ Chunking และ Hybrid Retrieval
→ Evidence Sufficiency
→ Orchestrator
→ Citation Verification
→ User PWA
→ Benchmark และ Security
→ Closed Pilot
→ Public Beta
→ Zayd 1.0
```

หากงานใดในเส้นทางนี้ล่าช้า จะกระทบ Release โดยตรง โดยเฉพาะ:

- การได้สิทธิ์ Dataset ภาษาไทย
- การจัดหาผู้ตรวจและ Senior Scholar
- Citation Verification
- Evidence Sufficiency
- Security Review
- Backup/Restore

---

# 10. Release Quality Gates

## Gate A — Documentation Ready

- Project Charter, PRD และ SRS ผ่านการทบทวน
- Architecture และ ADR สำคัญพร้อม
- Governance และ Safety Policies พร้อม

## Gate B — Data Ready

- Source/License Registry ครบ
- Corpus ชุดเริ่มต้นได้รับอนุมัติ
- ไม่มีข้อมูลที่สิทธิ์ไม่ชัดใน Production

## Gate C — Vertical Slice Ready

- Workflow ครบตั้งแต่นำเข้าถึง Feedback
- Citation เปิดดูและตรวจย้อนกลับได้
- Reviewer และ Scholar ใช้งาน Portal ได้

## Gate D — Technical MVP Ready

- Functional Requirements สำคัญครบ
- E2E Tests ผ่าน
- Local-first RAG ทำงานเมื่อ External API ล่ม
- Observability และ Backup พร้อม

## Gate E — Pilot Ready

- Benchmark ผ่านขั้นต่ำ
- ไม่มี Critical Security Issue
- Pilot Environment แยกและควบคุมได้

## Gate F — Public Beta Ready

- Pilot Findings สำคัญถูกแก้
- Terms, Privacy และ AI Limitation พร้อม
- Incident Response และ On-call พร้อม

## Gate G — Production Ready

- Citation Correctness ≥ 98%
- Fabricated Citation = 0
- Retrieval Recall@5 ≥ 90% ในหัวข้อ MVP
- High-risk Routing Accuracy ≥ 95%
- ไม่มี P0/P1 ค้าง
- Restore Test ผ่าน
- Release Approvers ลงนามครบ

---

# 11. KPI และตัวชี้วัด

## 11.1 Product

- Daily/Monthly Active Users
- Returning User Rate
- จำนวนการเปิด Citation
- User Satisfaction
- Feedback Rate

## 11.2 Retrieval และ AI

- Local RAG Hit Rate
- External Fallback Rate
- Retrieval Recall@5 และ Recall@10
- Citation Correctness
- Citation Completeness
- Fabricated Citation Rate
- Abstention Accuracy
- Madhhab Consistency
- High-risk Routing Accuracy

## 11.3 Reviewer

- Queue Depth
- Median Review Time
- Approval/Rejection Rate
- Reviewer Disagreement Rate
- งานเกิน SLA

## 11.4 Operations

- Availability
- Error Rate
- P95 Latency
- Cost per Answer
- Provider Failure Rate
- Backup Success และ Restore Test

---

# 12. ความเสี่ยงและแผนลดความเสี่ยง

| ความเสี่ยง | ผลกระทบ | แนวทางลดความเสี่ยง |
|---|---|---|
| ไม่มี Dataset ไทยที่สิทธิ์ชัดเจน | Critical Path หยุด | เริ่มขอสิทธิ์ตั้งแต่ Phase 0, ใช้ Manifest และ Corpus ขนาดเล็กก่อน |
| Reviewer ไม่เพียงพอ | Queue สะสมและ Release ล่าช้า | จำกัด Scope, แบ่งระดับความเสี่ยง, รับสมัคร Reviewer และกำหนด SLA |
| ความเห็นต่างทางวิชาการ | คำตอบขัดแย้ง | เก็บมัซฮับและ Source Metadata, แสดงความเห็นต่าง, Escalate |
| Citation หลอน | ความน่าเชื่อถือเสียหาย | Citation Registry, Allow-list Citation ID, Deterministic Verification |
| Prompt Injection | คำตอบผิดหรือข้อมูลรั่ว | แยก Instruction/Data, Sanitize Documents, Tool Allow-list และ Security Tests |
| External Provider ล่ม | บริการหยุด | Local-first, Circuit Breaker, Cache และ Provider Fallback |
| ค่า LLM สูง | ใช้งานต่อเนื่องไม่ได้ | Model Routing, Cache, จำกัด Context และ Cost Dashboard |
| License Violation | กฎหมายและชื่อเสียง | License Policy Engine, Dataset Manifest, Release Scan |
| ข้อมูลผู้ใช้รั่ว | ความเชื่อมั่นและกฎหมาย | Data Minimization, Redaction, RBAC, Encryption และ Audit |
| คำตอบเสี่ยงสูงผิด | อันตรายต่อผู้ใช้ | Risk Policy, Abstention, Scholar Escalation และ Incident Response |

---

# 13. การควบคุมการเปลี่ยนแปลง

การเปลี่ยนแปลงต่อไปนี้ต้องใช้ RFC:

- เปลี่ยน License
- เปลี่ยน Database หรือ Vector Store หลัก
- เปลี่ยน Default Madhhab
- เปลี่ยน Safety Policy
- เพิ่มหัวข้อความเสี่ยงสูง
- เปิด Public API หรือ MCP
- เพิ่ม Dataset ที่มีข้อจำกัด
- เปลี่ยนวิธี Citation Verification
- เปลี่ยน Governance หรืออำนาจอนุมัติ

RFC ต้องระบุ:

- Motivation
- Proposed Change
- Alternatives
- Migration Plan
- Security Impact
- Religious-content Impact
- Data-license Impact
- Evaluation Plan
- Rollback Plan

---

# 14. การเชื่อมกับ Task Plan

การดำเนินงานระดับโค้ดให้ยึด `tasks/00_task_index.md` เป็นแหล่งติดตามสถานะหลัก โดยแบ่งเป็น:

| Epic | เนื้อหา |
|---|---|
| EPIC-00 | Open-source Foundation |
| EPIC-01 | Monorepo and Development Environment |
| EPIC-02 | Database and Core Domain |
| EPIC-03 | Authentication, RBAC and Audit |
| EPIC-04 | Source and License Registry |
| EPIC-05 | Document Ingestion |
| EPIC-06 | Review and Publishing Workflow |
| EPIC-07 | Retrieval Engine |
| EPIC-08 | AI Orchestrator and Citation |
| EPIC-09 | User PWA |
| EPIC-10 | Reviewer and Admin Portals |
| EPIC-11 | Feedback and Incident Management |
| EPIC-12 | Evaluation and Benchmark |
| EPIC-13 | Security, Monitoring and Operations |
| EPIC-14 | Closed Pilot and Release |

Task จะเริ่มได้เมื่อผ่าน Definition of Ready และปิดได้เมื่อผ่าน Definition of Done ตามที่ระบุใน Task File

---

# 15. เอกสารอ้างอิงภายในโครงการ

- [Project Charter](00_project_charter.md)
- [Product Requirements Document](../01_product/PRD.md)
- [Software Requirements Specification](../02_requirements/SRS.md)
- [Requirements Traceability Matrix](../02_requirements/traceability_matrix.md)
- [System Architecture](../03_architecture/system_architecture.md)
- [Data License Policy](../05_data/license_policy.md)
- [Madhhab Policy](../06_islamic_governance/madhhab_policy.md)
- [Scholar Review Policy](../06_islamic_governance/scholar_review_policy.md)
- [Answer Safety Policy](../06_islamic_governance/answer_safety_policy.md)
- [Security Architecture](../07_security/security_architecture.md)
- [Evaluation Plan](../08_evaluation/evaluation_plan.md)
- [AI Coding Agent Policy](../09_development/ai_coding_agent_policy.md)

---

# 16. นิยามความสำเร็จของโครงการ

Zayd ถือว่าพร้อมให้บริการจริงเมื่อ:

1. ผู้ใช้ถามภาษาไทยและได้รับคำตอบพร้อมแหล่งอ้างอิงที่เปิดดูได้
2. ข้อความอัลกุรอาน หะดีษ และข้อมูลหนังสือตรวจย้อนกลับได้
3. ระบบแยกมัซฮับและความเห็นต่างอย่างชัดเจน
4. Production RAG ใช้เฉพาะเอกสารที่ผ่านการอนุมัติ
5. ระบบงดตอบเมื่อหลักฐานไม่พอ
6. คำถามความเสี่ยงสูงถูกจำกัดหรือส่งต่อผู้รู้
7. Reviewer สามารถตรวจคำตอบ Retrieval Trace และประวัติการแก้ไขได้
8. ผู้ใช้รายงานคำตอบผิดและทีมแก้ไขผ่าน Incident Workflow ได้
9. ระบบติดตั้งแบบ Self-host โดยไม่ผูกกับ Cloud รายเดียวได้
10. Evaluation, Security, Backup และ Restore ผ่าน Release Gate
11. ไม่มี P0/P1 Incident หรือ Critical Vulnerability ค้างอยู่
12. คณะผู้รู้ Product Owner และทีมเทคนิคอนุมัติ Release ร่วมกัน

---

## สถานะการอนุมัติ

| ผู้อนุมัติ | สถานะ | วันที่ | หมายเหตุ |
|---|---|---|---|
| Product Owner | PENDING |  |  |
| Technical Lead | PENDING |  |  |
| Islamic Content Board | PENDING |  |  |
| Data Steward | PENDING |  |  |
| Security Lead | PENDING |  |  |
| QA/Evaluation Lead | PENDING |  |  |
