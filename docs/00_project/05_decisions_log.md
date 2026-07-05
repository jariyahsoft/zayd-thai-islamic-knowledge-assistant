# Decision Log

ตารางนี้สรุปการตัดสินใจระดับโครงการ ก่อนสร้าง ADR รายละเอียด

| ID | การตัดสินใจ | สถานะ | เหตุผลย่อ |
|---|---|---|---|
| DEC-001 | สร้าง Zayd แบบ Greenfield Core + Selective Reuse | ACCEPTED | Domain model, review และ license workflow ต่างจากโครงการต้นทางมาก |
| DEC-002 | เปิด source code หลักภายใต้ Apache-2.0 | PROPOSED | รองรับการใช้งานเชิงพาณิชย์และมี patent grant |
| DEC-003 | แยก code license ออกจาก dataset license | ACCEPTED | สิทธิ์ซอฟต์แวร์ไม่ครอบคลุมเนื้อหาศาสนา |
| DEC-004 | ใช้ PostgreSQL + pgvector ใน MVP | ACCEPTED | ลดระบบที่ต้องดูแลและรองรับ metadata filtering |
| DEC-005 | ใช้ Local-first RAG | ACCEPTED | ลด vendor lock-in และคงความพร้อมเมื่อ API ภายนอกล่ม |
| DEC-006 | มัซฮับชาฟิอีเป็นค่าเริ่มต้น | PROPOSED | สอดคล้องกับกลุ่มเป้าหมายหลัก แต่ผู้ใช้ต้องเห็นและเปลี่ยนได้ |
| DEC-007 | Production RAG ใช้เฉพาะเอกสาร PUBLISHED | ACCEPTED | ป้องกันข้อมูลที่ยังไม่ตรวจเข้าสู่คำตอบ |
| DEC-008 | LLM อ้างได้เฉพาะ Citation ID จาก backend | ACCEPTED | ลด fabricated citation |
| DEC-009 | คำถามเสี่ยงสูงต้องจำกัดคำตอบหรือส่งต่อผู้รู้ | ACCEPTED | ลดผลกระทบจากคำตอบเฉพาะบุคคลที่ผิด |
| DEC-010 | Web/PWA มาก่อน Native App | ACCEPTED | ลดต้นทุนและส่งมอบวงจรหลักได้เร็วกว่า |
| DEC-011 | ไม่บันทึก chain-of-thought ภายใน | ACCEPTED | ไม่จำเป็นต่อ audit และเพิ่มความเสี่ยงข้อมูล |
| DEC-012 | AI coding agents ห้ามตัดสิน policy ศาสนาเอง | ACCEPTED | Policy ต้องผ่านมนุษย์ผู้รับผิดชอบ |

## วิธีเพิ่มการตัดสินใจ

การตัดสินใจที่มีผลต่อ API, schema, security, religious policy หรือ migration ต้องสร้าง ADR ใน `docs/03_architecture/adr/` และเชื่อม Task ที่เกี่ยวข้อง
