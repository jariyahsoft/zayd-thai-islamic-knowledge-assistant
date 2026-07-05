# Scholar Review Policy

## 1. Purpose

กำหนดบทบาท ขั้นตอน และหลักฐานการตรวจทานเนื้อหาศาสนาก่อนเผยแพร่และหลังมี feedback

## 2. Roles

### Data Operator

อัปโหลดไฟล์และกรอกข้อมูลแหล่ง/สิทธิ์ ไม่อนุมัติเนื้อหาตนเอง

### Translator

ตรวจและแก้คำแปล ไม่ตัดสินสถานะฟิกฮ์นอกขอบเขตที่ได้รับมอบหมาย

### Reviewer

ตรวจข้อความ metadata citation และความตรงกับต้นฉบับ

### Senior Scholar

อนุมัติเนื้อหาฟิกฮ์สำคัญ จัดการความเห็นขัดแย้ง ระงับ และกำหนด correction

### Auditor

ดูประวัติได้แต่แก้ข้อมูลไม่ได้

## 3. Review Levels

- Level 0: structural validation โดยระบบ
- Level 1: text/metadata/translation review
- Level 2: scholar review สำหรับฟิกฮ์และประเด็นอ่อนไหว
- Level 3: board review สำหรับ policy หรือข้อขัดแย้งสำคัญ

## 4. Separation of Duties

- ผู้อัปโหลดห้ามเป็นผู้อนุมัติสุดท้ายในเนื้อหาสำคัญ
- ผู้แปลไม่ควรอนุมัติคำแปลตนเองคนเดียว
- การ override incident P0/P1 ต้องมี Senior Scholar หรือ Board ตาม policy

## 5. Review Checklist

- ตรงกับต้นฉบับ
- ชื่อหนังสือ/ผู้เขียน/ฉบับ/หน้า
- ภาษาอาหรับไม่ถูกแก้โดย normalization
- คำแปลไทยไม่เพิ่มข้อสรุปเกินต้นฉบับ
- มัซฮับและประเภททัศนะถูกต้อง
- หะดีษมี reference/grade/grader เมื่อมี
- license อนุญาตการใช้งาน
- chunk ไม่ตัดบริบทสำคัญ
- citation preview ถูกต้อง

## 6. Decisions

- Approve
- Request changes
- Reject
- Escalate
- Mark duplicate
- Mark license issue

ทุก decision ต้องมี reviewer, timestamp, notes และ version diff

## 7. Publishing

เฉพาะ version ที่ได้รับ approval ตามระดับที่ policy กำหนดเท่านั้นจึงเปลี่ยนเป็น `PUBLISHED`

## 8. Post-publication Corrections

เมื่อพบปัญหา:

1. สร้าง incident
2. ประเมิน severity
3. suspend citation/document หากจำเป็น
4. identify affected answers
5. สร้าง version ใหม่และ review
6. publish correction
7. เพิ่ม regression test

## 9. Reviewer Conflict

เมื่อ reviewer ไม่เห็นพ้อง:

- ห้ามบังคับ merge ความเห็น
- บันทึกทั้งสองเหตุผล
- escalate
- หากเป็น ikhtilaf ที่ยอมรับ ให้เผยแพร่แบบแยกทัศนะ

## 10. Service Levels

SLA เป็นค่า configuration ไม่ใช่ข้อยืนยันทางศาสนา ตัวอย่างเป้าหมาย:

- P0: triage ทันทีเมื่อทีมพร้อม
- P1: priority queue
- Routine document: ตามกำลัง reviewer

ห้ามลดคุณภาพ review เพื่อให้ทัน SLA
