# Product Requirements Document — Zayd 1.0

## ข้อมูลเอกสาร

| รายการ | ค่า |
|---|---|
| ผลิตภัณฑ์ | Zayd — Thai Islamic Knowledge Assistant |
| เวอร์ชัน | PRD 1.0 |
| วันที่ | 5 กรกฎาคม 2026 |
| สถานะ | DRAFT FOR REVIEW |
| แพลตฟอร์มแรก | Mobile-first Web Application / PWA |
| ภาษาหลัก | ไทย |
| ภาษารอง | อาหรับและอังกฤษ |
| มัซฮับเริ่มต้น | ชาฟิอี โดยผู้ใช้เปลี่ยนได้ |

## 1. Product Summary

Zayd คือผู้ช่วย AI สำหรับค้นคว้าและอธิบายความรู้อิสลามที่ออกแบบเพื่อผู้ใช้ในประเทศไทย ระบบตอบเป็นภาษาไทยพร้อมหลักฐาน แสดงข้อความอาหรับ คำแปล เลขอ้างอิง และทัศนะทางฟิกฮ์อย่างชัดเจน

Zayd ไม่ใช่ระบบออกฟัตวาอัตโนมัติ แต่เป็นเครื่องมือช่วยค้นคว้าและนำผู้ใช้ไปยังหลักฐานที่ตรวจสอบได้

## 2. Problem Statement

### สำหรับผู้ใช้

- เนื้อหาภาษาไทยกระจัดกระจายและยากต่อการตรวจความน่าเชื่อถือ
- AI ทั่วไปอาจสร้างหลักฐานหรือผสมทัศนะโดยไม่ระบุ
- ผู้ใช้บางกลุ่มไม่สามารถอ่านแหล่งอาหรับหรืออังกฤษได้
- คำถามความเสี่ยงสูงอาจสร้างผลเสียหาก AI ตอบเกินหลักฐาน

### สำหรับผู้ตรวจและนักวิชาการ

- ไม่มีคิวตรวจข้อมูลและ workflow อนุมัติที่ตรวจย้อนหลังได้
- ไม่ทราบว่า AI ใช้เอกสารและ prompt ใด
- Feedback จากผู้ใช้ไม่ถูกแปลงเป็น incident และ regression test

### สำหรับผู้พัฒนา

- โครงการที่มีอยู่พึ่ง provider เฉพาะรายหรือไม่มี reviewer portal
- สิทธิ์ของ source code และ corpus มักถูกปะปน
- ขาด benchmark ภาษาไทยเฉพาะด้าน citation, madhhab และ abstention

## 3. Vision

> ทำให้มุสลิมในประเทศไทยเข้าถึงความรู้อิสลามที่ตรวจสอบได้ เข้าใจง่าย และเคารพความแตกต่างทางวิชาการ โดยใช้ AI เป็นเครื่องมือช่วยค้นคว้า ไม่ใช่ผู้แทนนักวิชาการ

## 4. Product Positioning

### Zayd เป็น

- ผู้ช่วยค้นคว้าความรู้อิสลามภาษาไทย
- เครื่องมือค้นหลักฐานและเปิดแหล่งต้นฉบับ
- ระบบแยกทัศนะตามมัซฮับ
- แพลตฟอร์มตรวจทานและเผยแพร่คลังความรู้

### Zayd ไม่เป็น

- มุฟตี AI
- ผู้ตัดสินข้อพิพาท
- ระบบ takfir
- เครื่องมือให้คำแนะนำทางแพทย์หรือกฎหมายแทนผู้เชี่ยวชาญ

## 5. Personas

### P1 — ผู้ใช้มุสลิมทั่วไป

ต้องการคำตอบไทยที่เข้าใจง่าย มีหลักฐานและทราบมัซฮับ

### P2 — นักเรียนศาสนา

ต้องการค้นต้นฉบับ เปรียบเทียบทัศนะ และดูข้อมูลหนังสือ/ผู้เขียน/หน้า

### P3 — ผู้เปลี่ยนมานับถืออิสลาม

ต้องการคำศัพท์และขั้นตอนพื้นฐานโดยไม่ใช้ศัพท์ซับซ้อนเกินไป

### P4 — Reviewer/Translator

ต้องการตรวจไฟล์ต้นฉบับ ข้อความสกัด คำแปล metadata และ chunk preview

### P5 — Senior Scholar

ต้องการตรวจประเด็นความเสี่ยงสูง อนุมัติ ระงับ และดูประวัติการตัดสินใจ

### P6 — Admin/Data Steward

ต้องการจัดการผู้ใช้ provider license source queue cost และ audit

## 6. Product Goals

1. ถามและตอบภาษาไทยพร้อม citation
2. แยกข้อความต้นฉบับออกจากคำอธิบายของ AI
3. รองรับมัซฮับและความเห็นต่าง
4. งดตอบเมื่อหลักฐานไม่พอ
5. ตรวจเอกสารก่อนเผยแพร่
6. ใช้ Local RAG เป็นลำดับแรก
7. รองรับ External API แบบ adapter และ storage policy
8. เปิดซอร์สและติดตั้งแบบ self-host ได้

## 7. Non-goals for 1.0

- รองรับฟิกฮ์ทุกบทและทุกมัซฮับอย่างสมบูรณ์
- Native mobile app
- LINE Bot
- Billing
- Public API/MCP สำหรับบุคคลทั่วไป
- เครื่องคำนวณมรดกและซะกาตขั้นสูง

## 8. MVP Content Scope

### เต็มรูปแบบ

- หลักศรัทธาพื้นฐาน
- ความสะอาดและน้ำละหมาด
- การละหมาด
- การถือศีลอด
- มารยาทและดุอาอ์พื้นฐาน
- ฟิกฮ์ชาฟิอีในหัวข้อข้างต้น

### จำกัดและต้องแสดงข้อจำกัด

- การเงินอิสลาม
- ฮาลาลเฉพาะผลิตภัณฑ์
- ครอบครัวและการแต่งงาน
- ประวัติศาสตร์และตัฟซีรเชิงลึก

### ส่งต่อผู้รู้

- หย่า
- มรดก
- takfir
- คดีและข้อพิพาท
- สัญญาการเงินซับซ้อน
- ปัญหาส่วนบุคคลที่ต้องสอบข้อเท็จจริง

## 9. Core User Journeys

### UJ-01 ถามคำถาม

เปิดแอป → พิมพ์คำถาม → ระบบจำแนก → ค้น Local RAG → fallback ถ้าจำเป็น → ตรวจหลักฐาน → ตอบพร้อม citation

### UJ-02 ตรวจหลักฐาน

เปิด citation → ดูต้นฉบับ → คำแปล → metadata → สถานะตรวจ → แหล่งที่มา

### UJ-03 รายงานคำตอบ

กดรายงาน → เลือกประเภท → สร้าง ticket → reviewer ตรวจ retrieval trace → แก้ระบบ/ข้อมูล → เพิ่ม regression test

### UJ-04 นำเข้าเอกสาร

อัปโหลด → ตรวจสิทธิ์และ malware → parse → AI แนะนำ metadata → human review → scholar approval → chunk/embed → publish

## 10. Functional Scope

### Chat

- Guest mode และ user mode
- Streaming
- Conversation history และ no-history mode
- เลือกความยาวคำตอบและมัซฮับ
- Save/share/report

### Retrieval

- Exact, full-text, vector และ hybrid search
- Multilingual query expansion
- Metadata filters
- Reranking
- Evidence sufficiency

### Citation

- Canonical IDs
- Quran/Hadith/Book cards
- Verified status
- Source details
- Invalidation และ re-review

### Reviewer Portal

- Review queue
- Side-by-side original/extracted view
- Diff, comments, assignment และ escalation
- Two-level approval

### Admin Portal

- Users/RBAC
- Providers/models
- Sources/licenses
- Prompt/policy versions
- Queue, cost, health และ incidents

## 11. Product Safety

- แบ่ง risk: Low, Medium, High, Restricted
- High/Restricted ต้องจำกัดคำตอบหรือส่งต่อผู้รู้
- ไม่อ้างว่าคำตอบเป็นฟัตวา
- ไม่สร้าง citation เอง
- ไม่ให้คำแนะนำอันตรายด้านสุขภาพ
- ไม่ตัดสินบุคคลเรื่องการออกจากศาสนา

## 12. Success Metrics

### Quality

- Citation correctness ≥ 98%
- Fabricated citation = 0 ใน release set
- Scholar approval ≥ 90% ในหมวด MVP
- High-risk routing ≥ 95%

### Retrieval

- Recall@5 ≥ 90%
- Local RAG hit rate ถูกติดตามและเพิ่มขึ้นตาม corpus

### Product

- ผู้ใช้เปิด citation ได้และเข้าใจว่ามาจากแหล่งใด
- Feedback สามารถปิดวงจรเป็น correction/regression test

### Operations

- Availability MVP 99.5%
- Local RAG ยังทำงานเมื่อ external provider ล่ม
- Backup และ restore ผ่านการทดสอบ

## 13. Release Phases

1. Foundation and governance
2. Vertical slice: Taharah/Shafi'i
3. MVP
4. Closed scholar/user pilot
5. Public beta
6. Zayd 1.0

## 14. Product Acceptance Criteria

Zayd 1.0 พร้อมเปิดเมื่อ:

- PWA ใช้งานบนมือถือได้
- Reviewer/Admin workflows ครบ
- Production retrieval ใช้เฉพาะ PUBLISHED
- Citation กดตรวจได้
- License Registry บังคับใช้จริง
- High-risk routing และ abstention ผ่านเกณฑ์
- ไม่มี P0/P1 ค้าง
- self-host installation และ restore test ผ่าน
