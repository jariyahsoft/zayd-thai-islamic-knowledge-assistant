# Zayd Data License Policy

## 1. Purpose

กำหนดกฎการรับ เก็บ แปลง สร้าง embedding ใช้ และแจกจ่ายข้อมูล เพื่อแยกสิทธิ์ของ source code ออกจากสิทธิ์ของเนื้อหาอย่างชัดเจน

## 2. Fundamental Rule

> การที่ API เข้าถึงข้อมูลได้ หรือ repository ใช้ open-source license ไม่ได้แปลว่า Zayd มีสิทธิ์เก็บ corpus หรือแจกจ่ายเนื้อหานั้น

## 3. License Status

- `UNKNOWN`
- `REVIEW_REQUIRED`
- `EPHEMERAL_CACHE_ONLY`
- `PERSISTENT_PRIVATE`
- `PERSISTENT_REDISTRIBUTABLE`
- `PROHIBITED`
- `EXPIRED`

`UNKNOWN`, `PROHIBITED`, `EXPIRED` ห้ามเข้าสู่ Production RAG

## 4. Required Source License Fields

- owner/rightsholder
- source URL/reference
- license name and version
- permission evidence
- storage permission
- embedding/indexing permission
- commercial-use permission
- redistribution permission
- attribution requirements
- cache TTL
- validity dates
- jurisdiction/notes

## 5. Permitted Actions Matrix

| Status | Cache | Persistent Store | Embedding | Redistribute |
|---|---:|---:|---:|---:|
| UNKNOWN | No, except minimal transient processing | No | No | No |
| REVIEW_REQUIRED | Limited quarantine | No | No | No |
| EPHEMERAL_CACHE_ONLY | Yes, within TTL | No | No persistent index | No |
| PERSISTENT_PRIVATE | Yes | Yes | If explicitly allowed | No |
| PERSISTENT_REDISTRIBUTABLE | Yes | Yes | If allowed | Yes with conditions |
| PROHIBITED | No | No | No | No |
| EXPIRED | Stop use and evaluate removal | No new use | No new embedding | No |

## 6. API Responses

External provider adapter ต้องประกาศ:

- maximum cache TTL
- whether persistent storage is allowed
- whether original text may be displayed
- whether embeddings may be created
- attribution template

หากไม่ทราบ ให้ถือเป็น `UNKNOWN`

## 7. Document Intake

Data Operator ต้องแนบ:

- source record
- license record
- permission file or public license reference
- checksum
- proposed use

ระบบต้องบล็อก submit-for-review เมื่อ license metadata ไม่ครบ

## 8. Dataset Repository

Public repository อนุญาตเฉพาะ:

- manifests
- scripts ที่ดาวน์โหลดจากต้นทางอย่างถูกต้อง
- sample/public-domain/explicitly licensed content
- checksums and attribution

ห้าม commit private licensed corpus, API dumps หรือ copyrighted books โดยไม่มีสิทธิ์แจกจ่าย

## 9. Attribution

Citation UI และ dataset manifest ต้องแสดง attribution ตามเงื่อนไขของแต่ละแหล่ง ห้ามรวม attribution เป็นข้อความทั่วไปหาก license ต้องการรูปแบบเฉพาะ

## 10. License Expiry and Revocation

Scheduled job ตรวจ `valid_until`:

1. แจ้ง Data Steward ล่วงหน้า
2. ปิดรับเอกสารใหม่
3. เมื่อหมดอายุให้ suspend retrieval ตาม policy
4. Flag answers ที่ใช้ source นั้น
5. เก็บ audit trail และเหตุผล

## 11. AI-generated Content

คำแปล สรุป หรือ metadata ที่ AI สร้างไม่ทำให้สิทธิ์ของข้อความต้นฉบับหายไป และต้องติดป้าย `UNVERIFIED` จนกว่ามนุษย์ตรวจ

## 12. Enforcement

License Policy Engine เป็น deterministic code และ LLM ห้าม override การตัดสินใจ

CI ต้องตรวจ:

- dataset manifest
- unknown licenses
- prohibited file patterns
- third-party notices
- dependency license policy

## 13. Takedown

เมื่อได้รับคำร้องสิทธิ์:

- สร้าง incident
- suspend content ชั่วคราวตาม severity
- ตรวจ evidence
- remove/restore/modify attribution
- แจ้งผลและบันทึก audit
