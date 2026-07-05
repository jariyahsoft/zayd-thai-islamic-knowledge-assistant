# ADR-001 — Greenfield Core + Selective Reuse

- Status: ACCEPTED
- Date: 5 กรกฎาคม 2026

## Context

Zayd ต้องมี domain model, reviewer workflow, license registry, Thai policy และ local-first RAG ที่แตกต่างจาก Ansari และโครงการอื่นอย่างมาก

## Decision

สร้าง repository และ core domain ใหม่ แล้วนำแนวคิดหรือโมดูลที่ตรวจ license แล้วมาใช้แบบ selective ผ่าน boundary ที่ชัดเจน

## Consequences

### Positive

- ไม่ติด upstream architecture
- ออกแบบ governance และ audit ได้ตั้งแต่ต้น
- ลด merge conflict จาก fork ที่เปลี่ยนโครงสร้างหนัก

### Negative

- ต้องสร้าง foundation มากกว่า fork ทั้งระบบ
- ต้องบันทึก provenance ของโค้ดที่ดัดแปลง

## Rules

- ห้าม copy code โดยไม่เก็บ license/commit source
- ใช้ `CODE_PROVENANCE.md` และ `THIRD_PARTY_NOTICES.md`
- Reused module ต้องมี tests และ adapter ก่อนเข้าสู่ core
