# Requirements Traceability Matrix

เอกสารนี้เชื่อม Product Goals, SRS Requirement IDs, Tasks และวิธีตรวจสอบ เพื่อป้องกัน requirement ตกหล่นระหว่างออกแบบและพัฒนา

| Domain / Product Goal | Requirements | Primary Tasks | Verification / Quality Gate |
|---|---|---|---|
| Open-source foundation | FR-OSS-001..013 | 00-01..04, 01-01..06, 13-05..08 | Clean clone/build, license/secret scan, self-host install |
| Modular provider architecture | FR-EXT-001, FR-OSS-004, SRS §9 | 08-01..03, 10-05 | Contract tests, mock provider tests, provider failover |
| Authentication and sessions | FR-AUTH-001..010, NFR-SEC-002..006 | 03-01..04 | Auth integration, token reuse, MFA and rate-limit tests |
| RBAC and separation of duties | SRS §10, NFR-SEC-006 | 03-03, 06-02..03, 10-06 | Authorization matrix, self-approval rejection tests |
| Immutable auditability | FR-AUTH-006, FR-ADM-008, SRS §35 | 03-05, 13-01..02 | Audit inspection, mutation trace tests |
| Source governance | FR-ADM-005, FR-EXT-002 | 04-01, 04-04 | Source lifecycle and inactive-source tests |
| License governance | FR-EXT-002..005, FR-EXT-011 | 04-02..04, 05-01, 06-04 | Deterministic license policy unit/integration tests |
| Document upload and parsing | FR-ING-001..006 | 05-01..04 | File validation, malware, parser integration tests |
| Thai/Arabic normalization | FR-ING-007 | 05-05 | Unicode fixtures, original-text preservation tests |
| Metadata extraction | FR-ING-008..009 | 05-06..07 | Unverified-label and review-task tests |
| Reviewer workflow | FR-REV-001..011 | 06-01..03, 10-01..03 | Review E2E, revision/diff, separation-of-duties tests |
| Safe publishing | FR-RET-009, FR-ING-010..013 | 06-04..05, 07-01..02 | Transaction/retry, publish/suspend/rollback E2E |
| Full-text retrieval | FR-RET-002..003, FR-RET-006 | 07-03 | Thai/Arabic search benchmark and metadata filters |
| Vector retrieval | FR-RET-004, FR-RET-006 | 07-02, 07-04 | pgvector integration and dimension compatibility tests |
| Hybrid retrieval | FR-RET-005, FR-RET-010 | 07-05 | Score-component tests and regression benchmark |
| Multilingual retrieval | FR-RET-007 | 07-06 | Thai–English–Arabic query fixtures and intent preservation |
| Reranking | FR-RET-008 | 07-07 | Reranker contract/fallback and ranking metrics |
| Evidence sufficiency | FR-RET-011..013, SRS §27 | 07-08, 08-06 | Sufficiency/abstention benchmark |
| Madhhab selection and consistency | FR-MADH-001..007 | 09-04, 07-06, 08-04..06 | Preference override, retrieval filter and madhhab consistency tests |
| Question classification | FR-CLASS-001..008 | 08-04 | Classification benchmark and structured-output tests |
| Answer safety and abstention | FR-SAFE-001..008, FR-ANS-005..007 | 08-05..06, 12-05 | Risk routing, abstention and unsafe-answer benchmark |
| High-risk routing | FR-CLASS-004, FR-ANS-007 | 08-05, 12-05 | High-risk routing accuracy and unsafe-answer rate |
| Answer orchestration | FR-ANS-001..010 | 08-06, 08-09..10 | Workflow state tests, cancellation, revision and abstention |
| Citation registry | FR-CIT-001..003, FR-CIT-009..010 | 08-07 | Canonical ID, version binding and invalidation tests |
| Citation verification | FR-CIT-004..008, FR-CIT-011 | 08-08, 12-04 | Fabricated citation rate, quote fidelity and claim support |
| Thai user PWA | FR-CHAT-001..014 | 09-01..06 | Mobile E2E, streaming, preferences, history/no-history |
| User feedback | FR-FDB-001..004 | 09-07, 11-01..02 | Feedback-to-review E2E |
| Incident response and invalidation | FR-FDB-005..010 | 11-03..05, 06-05 | P0/P1 workflow, answer invalidation, regression conversion |
| Admin control and audit visibility | FR-ADM-001..012 | 10-04..06, 04-04 | Admin E2E, secret masking, last-admin safeguard |
| Evaluation framework | SRS §36, FR-FDB-008 | 12-01..07 | Reproducible benchmark run and regression dashboard |
| Security hardening | NFR-SEC-001..018 | 13-04..06, 14-05 | SAST/DAST, upload, SSRF, XSS, authz and prompt-injection tests |
| Privacy | NFR-PRV-001..010 | 03-01..05, 09-05, 13-01..02 | No-history, deletion, redaction and access-control tests |
| Performance | NFR-PERF-001..008 | 14-04, 13-03 | Load test and latency dashboards |
| Availability and provider failure | NFR-AVL-001..008, FR-EXT-006..010 | 08-01..06, 13-03, 13-08..09 | Circuit-breaker, provider outage and read-only mode tests |
| Backup and disaster recovery | NFR-BCK-001..007 | 13-07 | Encrypted backup, restore and consistency test |
| Production release | SRS §47..49 | 14-01..07 | Pilot, security review, quality gates, SBOM/checksum release |

## Traceability Rules

เมื่อ Requirement เพิ่ม ลบ หรือเปลี่ยน:

1. อัปเดต PRD หากกระทบ product scope
2. อัปเดต SRS ฉบับเต็ม
3. อัปเดต matrix นี้
4. อัปเดต Task ที่เกี่ยวข้อง
5. เพิ่มหรือแก้ automated tests / benchmark cases
6. บันทึก ADR/RFC/Decision Log เมื่อมีผลต่อสถาปัตยกรรม นโยบาย หรือ backward compatibility
7. ระบุ migration plan หากกระทบข้อมูลหรือ API

## Release Traceability Gate

ก่อน release ต้องยืนยันว่า:

- Requirement ที่อยู่ใน MVP มี Task และ Verification อย่างน้อยหนึ่งรายการ
- Task สำคัญไม่มี Requirement ID ที่ไม่พบใน SRS
- Test failures ที่เกี่ยวกับ Security, Citation, License หรือ High-risk Routing ต้อง block release
- Known deviation ต้องมี owner, mitigation และวันหมดอายุ
