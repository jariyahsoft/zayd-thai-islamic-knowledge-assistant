# Project Charter — Zayd

## ข้อมูลเอกสาร

| รายการ | ค่า |
|---|---|
| โครงการ | Zayd — Thai Islamic Knowledge Assistant |
| เวอร์ชัน | 1.0 |
| วันที่ | 5 กรกฎาคม 2026 |
| สถานะ | DRAFT |
| เจ้าของเอกสาร | Product Owner |

## 1. วัตถุประสงค์

สร้างแพลตฟอร์มโอเพนซอร์สสำหรับค้นคว้าและอธิบายความรู้อิสลามเป็นภาษาไทย โดยคำตอบต้องมีหลักฐาน ตรวจสอบย้อนกลับได้ แยกทัศนะตามมัซฮับ และมีระบบให้ผู้รู้ตรวจทานข้อมูลก่อนเผยแพร่

## 2. ปัญหาที่โครงการแก้ไข

- ข้อมูลศาสนาภาษาไทยกระจัดกระจายและคุณภาพไม่สม่ำเสมอ
- AI ทั่วไปอาจสร้างเลขอายะฮ์ เลขหะดีษ หรือแหล่งอ้างอิงที่ไม่มีจริง
- ระบบจำนวนมากผสมทัศนะหลายมัซฮับโดยไม่ระบุ
- ยังไม่มี workflow เปิดซอร์สที่ครอบคลุมการนำเข้า ตรวจทาน อนุมัติ และระงับเอกสารศาสนา
- การพึ่ง External API อย่างเดียวเสี่ยงต่อค่าใช้จ่าย การหยุดบริการ และข้อจำกัดสิทธิ์ข้อมูล

## 3. ผลลัพธ์หลัก

1. Mobile-first PWA สำหรับผู้ใช้ทั่วไป
2. Reviewer Portal สำหรับผู้ตรวจทานและนักวิชาการ
3. Admin Portal สำหรับจัดการผู้ใช้ แหล่งข้อมูล Provider และเหตุการณ์
4. Local-first RAG พร้อม External API fallback
5. Source และ License Registry
6. Citation Registry และ Citation Verification
7. Thai Islamic benchmark
8. Self-host deployment package
9. Open-source governance และ plugin architecture

## 4. หลักการของโครงการ

- Evidence first
- Citation required
- Scholar in the loop
- Madhhab aware
- Thai context
- Privacy by default
- Vendor-neutral
- Auditable
- Open-source code แยกจากสิทธิ์ของ dataset

## 5. ขอบเขต Zayd 1.0

### รวมในขอบเขต

- ภาษาไทยเป็นหลัก ภาษาอาหรับและอังกฤษเป็นภาษารอง
- มัซฮับชาฟิอีเป็นค่าเริ่มต้นที่ผู้ใช้เปลี่ยนได้
- หัวข้อเริ่มต้น: หลักศรัทธาพื้นฐาน ความสะอาด น้ำละหมาด ละหมาด ถือศีลอด มารยาท และดุอาอ์พื้นฐาน
- Document ingestion, review, approval, publishing และ rollback
- Hybrid retrieval, multilingual query expansion และ evidence sufficiency
- Feedback และ incident workflow

### นอกขอบเขต Zayd 1.0

- มุฟตี AI หรือฟัตวาอัตโนมัติ
- เครื่องคำนวณมรดกและซะกาตเต็มรูปแบบ
- Native Android/iOS
- LINE Bot
- Billing
- รองรับทุกมัซฮับอย่างครบถ้วน

## 6. ผู้มีส่วนได้ส่วนเสีย

| กลุ่ม | ความรับผิดชอบ |
|---|---|
| Product Owner | กำหนดขอบเขตและลำดับความสำคัญ |
| Technical Lead | สถาปัตยกรรมและคุณภาพทางเทคนิค |
| Islamic Content Board | นโยบายศาสนาและอนุมัติเนื้อหา |
| Data Steward | สิทธิ์ข้อมูลและ dataset manifests |
| Security Lead | Threat model และ security gates |
| QA/Evaluation Lead | Benchmark และ release quality |
| Maintainers | Code review, release และ governance |
| Community Contributors | โค้ด เอกสาร คำแปล และ test cases |

## 7. ตัวชี้วัดความสำเร็จ

- Citation correctness ≥ 98% ในชุดทดสอบหลัก
- Fabricated citation = 0 ใน release gate
- Retrieval Recall@5 ≥ 90% ในหัวข้อ MVP
- High-risk routing accuracy ≥ 95%
- ไม่มี P0/P1 incident ค้างก่อน release
- Production RAG ใช้เฉพาะเอกสารสถานะ `PUBLISHED`
- Self-host profile ติดตั้งได้จากเอกสารโดยผู้ดูแลระบบภายนอก

## 8. ความเสี่ยงหลัก

- ขาด dataset ภาษาไทยที่มีสิทธิ์ชัดเจน
- Reviewer ไม่เพียงพอ
- ความเห็นต่างทางวิชาการ
- Hallucination และ prompt injection
- Provider ภายนอกเปลี่ยนราคา/เงื่อนไข
- ชื่อเสียงเสียหายจากคำตอบผิด

## 9. อำนาจตัดสินใจ

- Product scope: Product Owner
- Architecture: Technical Lead ผ่าน ADR
- Religious policy: Islamic Content Board
- Data license: Data Steward และ Legal reviewer เมื่อจำเป็น
- Security release gate: Security Lead
- Final release: Maintainers + Product Owner + Islamic Content Board representative
