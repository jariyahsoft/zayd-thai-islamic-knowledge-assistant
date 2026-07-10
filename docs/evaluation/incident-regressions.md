# Incident-derived regression cases

Confirmed (`resolved` or `closed`) incidents may create an evaluation-case candidate through:

```text
POST /admin/incidents/{incident_id}/regression-cases
```

The caller must hold both `feedback.manage` and `evaluations.manage`; the normal privileged API
access path also requires MFA. The request supplies a target private evaluation dataset and a full
evaluation case contract, including expected behavior and at least one source reference.

The endpoint always creates a **private draft**. It ignores caller-supplied provenance and never
copies the incident summary, feedback body, reporter identity, conversation, answer, or other
incident payload into the evaluation case. Instead, it stores only bounded provenance: incident ID,
severity, and policy versions. Promotion or approval remains a separate scholar/QA workflow.

Before persistence, deterministic redaction replaces recognized email addresses, Thai phone
numbers, and Thai national ID patterns in reviewer-supplied question, choices, expected-behavior
fields, and source-reference display metadata. Operators must still review the candidate for
contextual personal or restricted information that pattern matching cannot identify.

The action appends an immutable incident timeline event and an audit event containing IDs, schema
version, policy version, and redaction count only. It rejects unconfirmed incidents, public
datasets, non-draft/non-private cases, duplicate case keys, missing required source references or
expected behavior, and callers missing either permission.
