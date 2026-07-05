# Madhhab Policy

## 1. Purpose

กำหนดวิธีที่ Zayd จัดเก็บ ค้น และอธิบายทัศนะทางฟิกฮ์โดยไม่ผสมมัซฮับอย่างคลุมเครือ

## 2. Default

- ค่าเริ่มต้นของ Zayd 1.0 คือมัซฮับชาฟิอี
- UI ต้องแจ้งค่าเริ่มต้นอย่างชัดเจน
- ผู้ใช้เปลี่ยน preference ได้
- คำถามที่ระบุมัซฮับมีลำดับเหนือ preference

## 3. Metadata

เอกสารฟิกฮ์และ chunk ต้องระบุ:

- `madhhab`: shafii/hanafi/maliki/hanbali/other/general/unknown
- author/school relationship เมื่อทราบ
- scope เช่น dominant view, alternate view, comparative
- edition/page/reference
- review status

`unknown` ห้ามถูกนำเสนอว่าเป็นคำตอบเฉพาะมัซฮับ

## 4. Retrieval Rules

1. ใช้มัซฮับที่ผู้ใช้ระบุ
2. ถ้าไม่ระบุ ใช้ preference
3. ถ้าไม่มี preference ใช้ default และแจ้งผู้ใช้
4. Comparative question สามารถดึงหลายมัซฮับ แต่ต้องแยกผล
5. ห้ามนำ result ต่างมัซฮับมารวมเป็นข้อสรุปเดียวโดยไม่ติดป้าย

## 5. Answer Format

คำตอบฟิกฮ์ควรมี:

- สรุปตามมัซฮับที่ใช้
- เงื่อนไข/ข้อยกเว้น
- หลักฐานและแหล่งตำรา
- ทัศนะอื่นเมื่อมีประโยชน์
- ข้อจำกัดหรือการส่งต่อผู้รู้

## 6. Differences of Opinion

ระบบต้องใช้ภาษาที่เคารพ เช่น “ในมัซฮับ...”, “มีอีกทัศนะหนึ่ง...” และหลีกเลี่ยงการกล่าวว่าทัศนะที่ยอมรับทางวิชาการเป็นความผิดโดยไม่มีหลักฐานและ policy

## 7. High-risk Cases

เรื่องหย่า แต่งงาน มรดก สัญญา และกรณีเฉพาะบุคคล ต้องไม่ใช้ default madhhab เพื่อออกข้อสรุปโดยไม่ทราบรายละเอียด ให้ข้อมูลทั่วไปและส่งต่อผู้รู้

## 8. Governance

การเปลี่ยน default madhhab, source priority หรือ wording policy ต้องผ่าน Islamic Content Board และ version policy ใหม่
