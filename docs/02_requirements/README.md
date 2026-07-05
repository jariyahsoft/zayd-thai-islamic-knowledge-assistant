# Requirements Documentation

โฟลเดอร์นี้เก็บข้อกำหนดระบบที่ใช้เป็นแหล่งอ้างอิงหลักสำหรับการออกแบบ พัฒนา ทดสอบ และ release Zayd

## เอกสารหลัก

1. [SRS 1.1 — Full Canonical Specification](SRS.md) — เอกสารหลักที่ต้องยึดในการพัฒนา
2. [SRS Summary 1.0](SRS_summary.md) — ฉบับย่อสำหรับอ่านภาพรวม
3. [Requirements Traceability Matrix](traceability_matrix.md) — เชื่อม Product Goal → Requirement → Task → Verification
4. [Archived Compact SRS 1.0](archive/SRS_v1.0_compact.md) — ฉบับย่อเดิม เก็บเพื่ออ้างอิงประวัติ

## กฎการใช้งาน

- หากเนื้อหาระหว่าง Full SRS กับ Summary ขัดกัน ให้ยึด `SRS.md`
- Task ใหม่ต้องอ้าง Requirement ID ที่มีอยู่ หรือแก้ SRS และ Traceability Matrix ก่อน
- การเปลี่ยน requirement ด้าน Security, License, Madhhab, Citation หรือ Review Workflow ต้องผ่านเจ้าของนโยบายที่เกี่ยวข้อง
- ห้ามแก้ requirement เพื่อให้ตรงกับ implementation ที่ทำผิดอยู่แล้วโดยไม่มี RFC/Decision Record

## Version History

| Version | การเปลี่ยนแปลง |
|---|---|
| SRS 1.0 | ฉบับย่อสำหรับ baseline เริ่มต้น |
| SRS 1.1 | คืนข้อกำหนดฉบับเต็ม เพิ่ม Open-source, Self-host, API, Data Model, Governance, CI/CD, Security, Testing และ Release Requirements |
