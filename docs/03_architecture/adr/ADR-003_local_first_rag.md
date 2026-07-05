# ADR-003 — Local-first RAG

- Status: ACCEPTED
- Date: 5 กรกฎาคม 2026

## Decision

ทุกคำถามต้องค้น Local Knowledge Base ก่อน External Knowledge Provider

## External fallback ใช้เมื่อ

- local evidence insufficient
- ผู้ใช้ขอแหล่งที่ไม่มีใน local corpus
- ข้อมูลมีความเปลี่ยนแปลงและ policy อนุญาต

## Storage rules

- Provider response มี `storage_policy`
- Cache ชั่วคราวตาม TTL
- Persistent data ต้องผ่าน license check และ human review
- ห้ามสะสม API responses เป็น corpus หากไม่ได้รับสิทธิ์

## Benefits

- ลด vendor lock-in และค่าใช้จ่าย
- ทำงานต่อได้เมื่อ provider ล่ม
- ควบคุม corpus และ review status ได้
