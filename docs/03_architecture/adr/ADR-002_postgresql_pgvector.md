# ADR-002 — PostgreSQL + pgvector for MVP

- Status: ACCEPTED
- Date: 5 กรกฎาคม 2026

## Context

MVP ต้องจัดการ transactional metadata, approvals, filters และ vector search โดยทีมขนาดเล็ก

## Decision

ใช้ PostgreSQL เป็น system of record และ pgvector เป็น vector index ใน MVP

## Rationale

- ลดจำนวนระบบที่ต้องดูแล
- ใช้ metadata filtering และ transaction ร่วมกัน
- backup/restore และ self-host ง่าย
- เปลี่ยน vector store ได้ภายหลังผ่าน interface

## Consequences

- ต้องวาง index และ query plan อย่างระมัดระวัง
- corpus ขนาดใหญ่มากอาจต้องย้ายไป Qdrant/OpenSearch ในอนาคต
- embedding dimensions ต้องถูก version และ validate
