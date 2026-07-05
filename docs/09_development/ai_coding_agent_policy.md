# AI Coding Agent Policy

## 1. Purpose

กำหนดวิธีใช้ Codex, Claude Code หรือ AI coding agent อื่นเพื่อพัฒนา Zayd โดยไม่ให้ agent เปลี่ยน policy, architecture หรือข้อมูลสำคัญโดยไม่มีการตรวจ

## 2. Required Reading Before Work

Agent ต้องอ่านอย่างน้อย:

- `docs/01_product/PRD.md`
- `docs/02_requirements/SRS.md`
- `docs/03_architecture/system_architecture.md`
- policy ที่เกี่ยวข้องกับ Task
- `tasks/README.md`
- task file ปัจจุบันและ dependencies

## 3. Tier Rules

- Tier S: architecture, schema, auth, RBAC, license, retrieval, citations, security, migrations
- Tier A: APIs, integrations, production features, Docker/CI
- Tier B: components, forms, docs, routine tests
- Tier C: mechanical edits

Tier B/C ห้ามเปลี่ยน security, religious policy, data license logic หรือ production migrations โดยลำพัง

## 4. Workflow

1. ตรวจ Task status/dependencies
2. สรุปแผนและไฟล์ที่จะเปลี่ยน
3. Implement เฉพาะ scope
4. เพิ่ม tests
5. Run lint/typecheck/tests/scans ที่เกี่ยวข้อง
6. อัปเดต docs และ Completion Report
7. Commit แยกตาม Task
8. เปลี่ยนเป็น `IN_REVIEW` ไม่ใช่ `DONE` จนมนุษย์อนุมัติ

## 5. Prohibited Actions

- ใส่ secrets หรือ credentials
- ดาวน์โหลด/commit corpus ที่สิทธิ์ไม่ชัด
- scrape แหล่งข้อมูลโดยไม่ได้รับอนุญาต
- bypass tests, approval หรือ license checks
- เปลี่ยนมัซฮับ/safety policy เอง
- อ้างว่าเนื้อหาศาสนาถูกต้องโดยไม่ผ่าน reviewer
- log hidden chain-of-thought
- ใช้ `--force`, destructive migration หรือ delete production data โดยไม่มีขั้นตอนชัดเจน

## 6. Selective Reuse

เมื่อดัดแปลง open-source code:

- ตรวจ license
- ระบุ source repository/commit
- อัปเดต `CODE_PROVENANCE.md`
- รักษา notices
- เพิ่ม tests
- ห้ามคัดลอก dataset พร้อม code โดยสมมติว่า license เดียวกัน

## 7. Database and Migration

- Migration ต้อง forward/rollback หรือมี documented irreversible plan
- ห้ามแก้ migration ที่ release แล้ว
- เพิ่ม indexes และ constraints พร้อม test
- ใช้ transaction เมื่อเหมาะสม

## 8. Security-sensitive Changes

Auth, RBAC, file upload, provider secrets, prompt/tool access และ audit ต้องมี:

- threat notes
- negative tests
- human security review
- no sensitive logging

## 9. Religious-content Changes

Task ที่แตะ prompts, policy, retrieval source priority, madhhab logic หรือ benchmark golden answers ต้องมี `Content Review Required: Yes` และห้าม agent mark final approval

## 10. Completion Report

ต้องบันทึก:

- files changed
- design decisions
- tests/commands and results
- security/license impacts
- known limitations
- follow-up tasks

## 11. Definition of Done

Agent ทำงานเสร็จทางเทคนิคเมื่อ checks ผ่าน แต่ Task เป็น `DONE` ได้หลัง code review และ content/security review ตามที่กำหนด
