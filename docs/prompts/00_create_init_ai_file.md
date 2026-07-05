# Prompt: Create Initial AI Project Files

ใช้ prompt นี้เมื่อเริ่มโปรเจกต์ใหม่ หรือเมื่อต้องการสร้างชุดเอกสาร `initial project files` จาก SRS, PRD, product brief, proposal, meeting notes, หรือเอกสาร requirement อื่น ๆ

เป้าหมายคือให้ AI อ่านเอกสารต้นทาง แล้วสร้างไฟล์เริ่มต้นที่ทีมและ AI agents ใช้ต่อได้ทันทีในหลายโปรเจกต์ ไม่ผูกกับ tech stack หรือ domain ใด domain หนึ่ง

---

## Input

ใช้เอกสารต้นทางต่อไปนี้เป็น source of truth:

```text
{SOURCE_DOCUMENT_PATH_OR_CONTENT}
```

ตัวอย่าง:

```text
from docs\srs_todo_plus_v1_0.md create initial project files
```

หากโปรเจกต์มีข้อมูลเสริม ให้รวมไว้ใน context ก่อนเริ่ม เช่น:

- ชื่อโปรเจกต์
- ประเภทผลิตภัณฑ์ เช่น SaaS, marketplace, internal tool, mobile app, API platform
- กลุ่มผู้ใช้หลัก
- Tech stack ที่ต้องการ
- Cloud/provider ที่ต้องใช้
- ภาษา UI ที่ต้องรองรับ
- ข้อจำกัดด้าน security, compliance, budget, timeline
- Repo structure ที่มีอยู่แล้ว

---

## Role

คุณคือ Senior Product Engineer + Technical Writer + AI Project Architect

หน้าที่ของคุณ:

1. อ่านเอกสารต้นทางให้ครบก่อนสร้างไฟล์
2. แยกข้อมูลที่เป็น fact ออกจาก assumption
3. สร้างเอกสารที่ทีมใช้ implement ต่อได้จริง
4. ใช้ภาษากระชับ ชัดเจน เป็นระบบ
5. ทำให้ไฟล์ `initial project files` เป็น operating manual สำหรับ AI agents และมนุษย์ในทีม

---

## Tasks

สร้างหรืออัปเดตไฟล์ต่อไปนี้:

```text
README.md
.gitignore
docs/design/00-project-overview.md
docs/design/01-architecture.md
docs/design/02-coding-rules.md
docs/design/03-database-design.md
docs/design/04-api-standard.md
docs/design/05-decisions.md
docs/design/06-backlog.md
docs/design/07-security-rules.md
docs/design/08-ui-guide.md
docs/design/09-testing-guide.md
docs/design/10-glossary.md
docs/design/11-tasks.md
docs/design/12-ui-image-prompts.md
```

ถ้าโปรเจกต์ไม่ต้องใช้บางไฟล์ ให้ยังสร้างไฟล์ไว้ แต่ระบุว่า `Not applicable yet` พร้อมเหตุผลและสิ่งที่ต้องเติมภายหลัง

ถ้าโฟลเดอร์ `docs/design/` ยังไม่มี ให้สร้างโฟลเดอร์นี้ก่อนแล้ววางไฟล์ `00` ถึง `12` ทั้งหมดไว้ใต้โฟลเดอร์นี้

---

## General Rules

- ห้าม invent requirement ที่ไม่มีในเอกสารต้นทาง
- ถ้าจำเป็นต้องเดา ให้ใส่ไว้ในหัวข้อ `Assumptions`
- ถ้าพบข้อมูลขัดแย้ง ให้ใส่ไว้ใน `Open Questions`
- ใช้ heading, table, checklist และ bullet ให้ scan ง่าย
- ทุกไฟล์ควรมี `Source` ระบุว่าข้อมูลมาจากเอกสารใดหรือ section ใด
- ใช้คำศัพท์เดียวกันทั้งชุดเอกสาร เช่น role, status, entity, module
- ใช้ภาษาเดียวกับเอกสารต้นทางเป็นหลัก ถ้าเอกสารเป็นไทย ให้เขียนไทยและคง technical terms ที่จำเป็นเป็นอังกฤษ
- ทำให้เนื้อหา generalizable ใช้กับโปรเจกต์อื่นได้ ไม่ hard-code ชื่อ framework/cloud เว้นแต่ source ระบุชัด
- ถ้า repo มีไฟล์เดิมอยู่แล้ว ให้อัปเดตแบบ preserve ข้อมูลที่ยังถูกต้อง ไม่ลบทิ้งโดยไม่จำเป็น

---

## README.md Requirements

สร้าง README สำหรับมนุษย์ที่เพิ่งเปิด repo ครั้งแรก

ควรมี:

- Project name
- One-line summary
- Problem statement
- Target users
- Core modules/features
- Tech stack หรือ `To be decided`
- High-level architecture
- Getting started
- Environment variables
- Common commands
- Folder structure
- Development workflow
- Testing
- Deployment
- Links ไปยังเอกสารใน `initial project files` โดยใช้ path ใต้ `docs/design/` สำหรับไฟล์ `00` ถึง `12`
- License หรือ `TBD`

ตัวอย่าง section:

```md
# {Project Name}

## Overview

## Features

## Tech Stack

## Getting Started

## Environment Variables

## Scripts

## Project Structure

## Documentation

## Development Workflow

## Testing

## Deployment

## License
```

---

## .gitignore Requirements

สร้าง `.gitignore` ให้เหมาะกับ tech stack จากเอกสารต้นทาง

หากยังไม่รู้ tech stack ให้ใช้ baseline ที่ปลอดภัย:

```gitignore
# Dependencies
node_modules/
vendor/

# Build outputs
dist/
build/
out/
.next/
.nuxt/
.output/
coverage/

# Environment
.env
.env.*
!.env.example

# Logs
*.log
npm-debug.log*
yarn-debug.log*
pnpm-debug.log*

# OS / editor
.DS_Store
Thumbs.db
.idea/
.vscode/*
!.vscode/extensions.json
!.vscode/settings.example.json

# Cache
.cache/
.turbo/
.parcel-cache/

# Local generated files
tmp/
temp/
```

เพิ่ม ignore เฉพาะ stack เมื่อ source ระบุ เช่น Python, Java, Go, Rust, Firebase, Terraform, Docker, mobile app

---

## 00-project-overview.md

สรุปภาพรวมผลิตภัณฑ์และเหตุผลของโปรเจกต์

ควรมี:

- Project name
- Vision
- Problem statement
- Goals
- Non-goals
- Target users/personas
- Roles and permissions summary
- Core modules
- MVP scope
- Out of scope
- Roadmap
- Success metrics
- Risks
- Assumptions
- Open Questions

---

## 01-architecture.md

อธิบายสถาปัตยกรรมเชิงระบบ

ควรมี:

- Architecture goals
- Proposed tech stack
- System context
- Component diagram แบบ Mermaid ถ้าเหมาะสม
- Request/data flow
- Frontend structure
- Backend/API structure
- Data storage
- Auth/session model
- Background jobs/events
- Search/cache/CDN ถ้ามี
- Observability/monitoring/logging
- Deployment topology
- Scalability considerations
- Key tradeoffs
- Open technical decisions

ถ้ายังไม่รู้ tech stack ให้เสนอ 2-3 options พร้อม tradeoff แต่ไม่เลือกแทน source โดยไม่มีเหตุผล

---

## 02-coding-rules.md

กำหนดกติกาการเขียนโค้ดให้ทีมและ AI agents

ควรมี:

- Language/framework conventions
- Folder structure
- Naming conventions
- Type safety rules
- Error handling rules
- Logging rules
- Configuration/env rules
- i18n rules ถ้ามีหลายภาษา
- Accessibility rules สำหรับ UI
- API/client-server boundary
- Data validation rules
- Security coding checklist
- Code review checklist
- Definition of Done สำหรับโค้ด

หาก source ยังไม่ระบุ stack ให้เขียนเป็น generic rules และ mark `TBD` เฉพาะส่วน stack-specific

---

## 03-database-design.md

ออกแบบข้อมูลตาม domain ของโปรเจกต์

ควรมี:

- Data model overview
- Entity list
- ERD หรือ Mermaid diagram ถ้าเหมาะสม
- Table/collection schema
- Field names, types, required/optional
- Status/enums
- Relationships
- Indexes
- Constraints
- Audit fields เช่น createdAt, updatedAt, createdBy
- Soft delete/retention strategy
- Migration/seed strategy
- Backup/restore notes
- Data privacy notes

ถ้า database ยังไม่เลือก ให้แยกเป็น conceptual model และ physical model options

---

## 04-api-standard.md

กำหนดมาตรฐาน API ทั้งระบบ

ควรมี:

- API design principles
- Base URL/versioning
- Auth mechanism
- Role/permission checks
- Request format
- Response format
- Error format
- Pagination
- Filtering/sorting
- Idempotency
- Rate limiting
- Webhook/event format ถ้ามี
- Notification templates ถ้ามี
- Endpoint catalog แยกตาม module
- API security checklist

ตัวอย่าง response format:

```json
{
  "data": {},
  "meta": {
    "requestId": "req_...",
    "nextCursor": null
  }
}
```

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable message",
    "fields": [],
    "requestId": "req_..."
  }
}
```

---

## 05-decisions.md

ใช้เป็น ADR log สำหรับการตัดสินใจสำคัญ

ควรมี:

- Open decisions
- Accepted decisions
- Rejected alternatives
- Decision template

Decision template:

```md
## ADR-000: {Title}

Status: Proposed | Accepted | Superseded | Rejected
Date: YYYY-MM-DD

### Context

### Decision

### Alternatives Considered

### Consequences

### Follow-up
```

เติม decision ที่ source ระบุชัด เช่น เลือก cloud, database, auth, architecture pattern

---

## 06-backlog.md

แปลง requirement เป็น backlog ที่ implement ได้

ควรมี:

- Epics
- User stories
- Acceptance criteria
- Priority เช่น P0/P1/P2
- Dependencies
- Risks/blockers
- Non-functional requirements
- Traceability กลับไป source section

รูปแบบ user story:

```md
### US-001: {Title}

As a {role},
I want {capability},
so that {benefit}.

Priority: P0
Source: {source section}

Acceptance Criteria:

- [ ] ...
- [ ] ...

Notes:

- ...
```

---

## 07-security-rules.md

กำหนด security model และ access control

ควรมี:

- Threat model summary
- Auth model
- Role matrix
- Resource access matrix
- Data classification
- PII/privacy considerations
- Compliance requirements เช่น PDPA, GDPR, HIPAA, SOC2 ถ้าเกี่ยวข้อง
- Security rules หรือ policy pseudocode
- Secret management
- Audit log requirements
- Abuse/rate-limit controls
- Security test checklist

ถ้าใช้ Firebase/Supabase/Postgres/RBAC ให้ใส่ตัวอย่าง rules หรือ policy ตาม stack นั้น

---

## 08-ui-guide.md

กำหนด UX/UI guide ให้ implement ต่อได้

ควรมี:

- Product design principles
- Information architecture
- User flows
- Wireframe outline
- Navigation model
- Page inventory
- UI states: loading, empty, error, success, permission denied, offline
- Design tokens: color, typography, spacing, radius, shadow
- Component inventory
- Responsive rules
- Accessibility requirements
- i18n/content tone

ถ้า source ไม่มี design direction ให้เสนอ direction ที่เหมาะกับ domain พร้อมระบุว่าเป็น assumption

---

## 09-testing-guide.md

กำหนด testing strategy

ควรมี:

- Test pyramid
- Unit test scope
- Integration test scope
- E2E flows
- Security tests
- Accessibility tests
- Performance tests
- API contract tests
- Test data/fixtures
- CI test commands
- Coverage target
- Manual QA checklist

ต้อง map test กลับไปยัง critical user flows และ acceptance criteria

---

## 10-glossary.md

รวมคำศัพท์กลางของระบบ

ควรมี:

- Business terms
- Technical terms
- Roles
- Entities
- Status values
- Error codes
- Event names
- Permission names
- Acronyms

รูปแบบ:

```md
| Term | Meaning | Notes |
| ---- | ------- | ----- |
| ...  | ...     | ...   |
```

---

## 11-tasks.md

สร้าง task plan สำหรับ sprint/current work

ควรมี:

- Current phase/sprint
- Task checklist แยกตาม module
- Dependencies
- Definition of Done
- Verification checklist
- Deployment checklist
- Backlog/future tasks
- Notes สำหรับ AI agents

ใช้สถานะ:

```text
[ ] todo
[/] in progress
[x] done
[!] blocked
```

---

## 12-ui-image-prompts.md

สร้าง prompt สำหรับ generate ภาพ UX/UI ที่ใช้สื่อสารแนวทางผลิตภัณฑ์กับลูกค้า นักลงทุน ทีมออกแบบ และทีมพัฒนา โดยอ้างอิง requirement และ `08-ui-guide.md` ไม่ใช่ใช้ภาพแทน implementation specification

ควรมี:

- Purpose และวิธีใช้ prompt ชุดนี้
- Master Style Prompt ที่กำหนด product type, brand personality, visual direction, design tokens, typography, accessibility, layout และ output format
- Negative Prompt สำหรับป้องกัน visual style, content หรือข้อมูลที่ไม่เหมาะกับผลิตภัณฑ์
- Prompt แยกตาม screen/page จาก page inventory และ critical user flows ใน `08-ui-guide.md`
- แต่ละ screen prompt ระบุ objective, user role, key content, components, state, primary/secondary actions และ navigation ที่จำเป็น
- Prompt สำหรับ responsive variants เมื่อมีทั้ง mobile, tablet หรือ desktop
- Prompt สำหรับ presentation composite เช่น user journey board, ecosystem หรือ feature overview เมื่อเหมาะกับโปรเจกต์
- Consistency checklist สำหรับสี typography component icon navigation sample data และ terminology
- Recommended presentation set ที่เลือกเฉพาะหน้าสำคัญสำหรับ demo หรือ pitch
- Source/traceability กลับไปยัง requirement และ `08-ui-guide.md`

กติกา:

- ใช้ `[MASTER STYLE]` หรือกลไกอ้างอิง style กลางเดียวกันในทุก screen prompt
- ระบุ aspect ratio, resolution และรูปแบบภาพ เช่น flat app screen หรือ device mockup
- ใช้ sample data ที่สมจริงแต่เป็นข้อมูลสมมติ ห้ามใส่ PII, credential หรือข้อมูลจริง
- รักษา role, entity, status, label และ navigation ให้ตรงกับเอกสารไฟล์อื่น
- ครอบคลุม loading, empty, error, success, permission denied และ offline state ที่สำคัญ ไม่สร้างเฉพาะ happy path
- ถ้ามี AI-generated text ในภาพ ให้ใช้ข้อความสั้นและระบุว่าควรตรวจหรือแก้ typography/text ใน design tool ภายหลัง
- ห้าม invent feature เพื่อให้ภาพดูน่าสนใจ หากต้องเสนอแนวทางเพิ่มให้ระบุเป็น `Assumption`
- สำหรับ domain ที่มีความเสี่ยงสูง ให้ใส่ข้อจำกัดด้าน safety, consent, privacy, disclaimer และการใช้สีเตือนให้ตรงกับ `07-security-rules.md` และ `08-ui-guide.md`
- หลีกเลี่ยงโลโก้มีลิขสิทธิ์ แบรนด์บุคคลที่สาม และเนื้อหาที่อาจทำให้เข้าใจว่าเป็นข้อมูลหรือบริการจริง

หากโปรเจกต์ไม่มี UI ให้สร้างไฟล์และระบุ `Not applicable yet` พร้อมเหตุผล เช่นเป็น library หรือ backend-only service และบอกว่า artifact ใดควรใช้แทน เช่น architecture diagram หรือ API workflow

---

## Output Quality Bar

ผลลัพธ์ต้อง:

- อ่านแล้วเริ่ม implement ได้โดยไม่ต้องย้อนถาม requirement พื้นฐาน
- เชื่อมโยงไฟล์ `initial project files` กันเองด้วย relative links เมื่อเหมาะสม
- ไม่มี placeholder ที่ว่างเปล่าแบบไร้ประโยชน์
- มี `Assumptions` และ `Open Questions` เมื่อข้อมูลไม่ครบ
- มี checklist ที่ตรวจได้จริง
- ใช้ Markdown ที่สะอาดและ consistent
- ไม่ใส่ข้อมูลลับ หรือค่า env จริง
- `docs/design/12-ui-image-prompts.md` ครอบคลุม critical screens จาก `docs/design/08-ui-guide.md` และใช้ style/safety constraints เดียวกันทุก prompt

---

## Final Response Format

หลังสร้างไฟล์ ให้ตอบกลับสั้น ๆ ด้วย:

```md
Created/updated initial project files.

Files:

- README.md
- .gitignore
- docs/design/00-project-overview.md
- ...
- docs/design/12-ui-image-prompts.md

Key assumptions:

- ...

Open questions:

- ...

Recommended next steps:

1. Review assumptions
2. Confirm open decisions
3. Start implementation from docs/design/11-tasks.md
```

ถ้ามีไฟล์เดิมถูกอัปเดต ให้บอกว่า preserve อะไรไว้ และเปลี่ยนอะไรบ้าง
