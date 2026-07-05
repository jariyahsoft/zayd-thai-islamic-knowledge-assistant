# Security Architecture — Zayd

## 1. Security Objectives

- ป้องกันการเข้าถึงข้อมูลและหน้าผู้ตรวจโดยไม่ได้รับสิทธิ์
- ป้องกัน corpus และ workflow จากไฟล์/ข้อมูลอันตราย
- ป้องกัน prompt injection ที่พยายามเปลี่ยน system policy
- ปกป้อง secrets และข้อมูลผู้ใช้
- ทำให้ทุก action สำคัญตรวจย้อนหลังได้

## 2. Trust Zones

1. Public clients
2. Reverse proxy/API boundary
3. Application services
4. Privileged reviewer/admin zone
5. Data stores/private network
6. External providers
7. CI/CD and artifact registry

## 3. Authentication and Authorization

- Secure password hashing
- Rotating refresh tokens
- MFA สำหรับ privileged roles
- RBAC on every protected endpoint
- Separation of duties
- Session revocation
- No trust based on UI hiding

## 4. Application Security

- Input/schema validation
- Parameterized database access
- CSRF protection ตาม auth model
- Strict CORS
- Content Security Policy
- Output escaping and safe Markdown rendering
- Rate limiting and abuse controls
- SSRF prevention for URL ingestion/provider config

## 5. File Ingestion Security

- Allow-list MIME/extensions
- Size and decompression limits
- Malware scan
- Quarantine before parsing
- Sandboxed parsers when possible
- Random object keys; no user-controlled filesystem paths
- Signed URLs and private buckets

## 6. AI and Prompt Injection Defenses

- Treat documents and user text as untrusted data
- Delimit evidence from instructions
- Tools use typed schemas and allow-lists
- LLM cannot call arbitrary URLs/SQL/files
- Deterministic policy checks before/after LLM
- Do not expose hidden prompts or internal traces
- Citation verification outside generation model

## 7. Provider Security

- Provider allow-list
- Minimize payloads
- Redact PII
- Timeouts and circuit breakers
- Secret manager/env injection
- Never return provider keys to frontend
- Audit model/provider configuration changes

## 8. Data Security

- TLS in transit
- Encryption at rest where supported
- Least-privilege database roles
- Separate production credentials
- Backup encryption
- Retention and deletion controls
- Audit access to sensitive conversation data

## 9. Audit Logging

Record:

- actor, action, resource, outcome
- request/trace ID
- timestamp and source context
- before/after summary for configuration/content changes

Do not log:

- passwords/tokens
- full provider secrets
- chain-of-thought
- full personal conversations by default

## 10. Supply Chain

CI checks:

- secret scan
- dependency vulnerability scan
- license scan
- container scan
- SBOM
- pinned/locked dependencies
- protected branches and required reviews

## 11. Incident Severity

- P0: active serious harm/data breach/critical unsafe content
- P1: high-impact authorization/citation/content failure
- P2: contained security or quality issue
- P3: low-impact defect

## 12. Backup and Recovery

- Daily encrypted backups
- Off-site copy
- Monthly restore test
- Separate backup credentials
- Documented RPO/RTO
- Audit restore operations

## 13. Security Release Gates

- No known Critical vulnerability
- High findings have fixes or documented accepted risk
- Auth/RBAC E2E passes
- Upload and prompt-injection tests pass
- Secret and license scans pass
- Restore test passes before 1.0
