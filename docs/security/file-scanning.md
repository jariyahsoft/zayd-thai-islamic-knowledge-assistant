# File Scanning and Quarantine

Zayd treats every uploaded document as untrusted until it passes malware scanning. This page documents the TASK-05-03 quarantine-first controls for ingestion operators and maintainers.

## Pipeline

1. `POST /documents` validates the source/license, content type, size, filename, and checksum before writing the original bytes to private object storage under the server-derived `uploads/quarantine/...` prefix.
2. New `document_versions` are created with `malware_scan_status: pending` and `parser_eligible: false` metadata. Parsers must not consume pending versions.
3. `POST /documents/{document_version_id}/scan` reads the private quarantine object server-side and runs the configured scanner through the `MalwareScanner` port.
4. Clean results update the version to `status: scanned_clean`, record engine/version metadata, write an immutable audit event, and set `parser_eligible: true`.
5. Infected results keep the object in quarantine, mark the document/version rejected for ingestion, create a P1 incident, write a security audit event, and keep `parser_eligible: false`.
6. `GET /documents/{document_version_id}/parser-eligibility` is the fail-closed parser gate. It returns success only when the version has a clean scan result.

The initial adapter is the deterministic `SignatureMalwareScanner`, including the standard EICAR test signature and a Zayd test signature for local tests. Production deployments can replace this port with a ClamAV or managed scanning adapter without changing parser code.

## Recorded metadata

Per version, Zayd records only sanitized scan metadata:

- `malware_scan_status`: `pending`, `clean`, or `infected`
- `malware_scan_engine`
- `malware_scan_engine_version`
- `malware_signature` when an infection is found
- `malware_scanned_bytes`
- `malware_scan_policy_version`
- `malware_incident_id` for infected files
- `parser_eligible`

Audit events and API responses never expose local filesystem paths, bucket names, internal object paths beyond the existing upload response contract, scanner command lines, raw file content, stack traces, or credentials.

## Scanner unavailable behavior

If the scanner is unavailable, Zayd fails closed:

- The scan endpoint returns a stable `MALWARE_SCANNER_UNAVAILABLE` error.
- The document version remains `pending` and `parser_eligible: false`.
- A sanitized `documents.malware_scan.unavailable` audit event is recorded.
- Operators may retry the same scan later; terminal clean/infected scan results are idempotent and do not create duplicate incidents or duplicate scan audit events.

## False-positive review procedure

False positives require human security review; operators must not manually flip `parser_eligible` in the database.

1. Open the generated incident and confirm the affected `document_id`, `document_version_id`, scanner engine/version, and signature name.
2. Obtain a second scan using an approved offline scanner or sandboxed analysis environment. Do not move the file out of private quarantine storage except through approved security tooling.
3. If the detection is confirmed, keep the document rejected and follow the deletion procedure below.
4. If the detection is determined to be a false positive, document the alternate scan evidence in the incident and create a follow-up remediation task to add an explicit reviewed override workflow. Until that workflow exists, re-upload a clean replacement file and scan it normally.
5. Close or mitigate the incident only after the replacement version has passed the normal scan gate.

## Deletion procedure for infected files

Deletion of quarantined infected objects is an operational security action:

1. Verify the incident, source, license, and document version identifiers.
2. Confirm no parser, review, chunk, embedding, or publication record references the infected version.
3. Delete the private object using least-privilege storage credentials; do not expose or paste signed URLs into tickets or chat.
4. Keep the document/version metadata and audit logs for traceability unless a later retention policy explicitly allows redacted deletion.
5. Add an incident note with the deletion time, operator, storage provider, and sanitized result. Do not include object-storage credentials, signed URLs, or raw scanner logs.

## Security notes

- Upload file type validation and malware scanning are separate controls; both must pass before parsing.
- Signed download URLs are short-lived and intended for authorized operators only.
- Uploaded documents and extracted text remain untrusted after malware scanning; parser sandboxing and prompt-injection defenses still apply in later ingestion stages.
