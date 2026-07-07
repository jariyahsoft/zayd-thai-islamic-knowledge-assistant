# Data License Governance

## Purpose

Zayd separates source-code licensing from knowledge-content licensing. A repository or provider API
being open does not imply the platform may store, embed, publish, or redistribute the content.

## Registry Policy

Every source used for ingestion must have a license record that captures:

- Storage permission.
- Embedding and indexing permission.
- Commercial-use permission.
- Redistribution permission.
- Attribution requirements.
- Permission evidence in private object storage.
- Validity dates and administrative notes.

## Fail-Closed Statuses

The registry must not authorize publication for:

- `unknown`
- `prohibited`
- `expired`

Licenses with `review_required` or `ephemeral_cache_only` also do not authorize publication. They may
only be used by later quarantine or transient-processing workflows that explicitly support those
states.

## Replacement and History

License changes are represented by creating a replacement license record. Existing rows are retained
so documents, audits, and incident reviews can resolve the exact license state that existed when an
operation occurred.

Do not edit historical license rows to reinterpret past permissions. If permission changes, create a
new row with updated dates, status, and evidence.

## Permission Evidence

Permission documents are private operational records. The registry stores the object key, not the
file contents. Access to permission-document metadata requires `licenses.read` and creates an audit
log entry.

Do not expose permission files through public URLs unless a later storage task adds signed URL support
with expiry, actor binding, and audit logging.

## Publication Authorization

The current service policy version is `license-registry-v1`.

Publication is authorized only when:

- The license is not date-expired.
- Status is `persistent_private` or `persistent_redistributable`.
- Storage permission is `allowed` or `conditional`.
- Embedding permission is `allowed` or `conditional`.
- For redistributable publication, redistribution is `allowed` or `conditional`.

The decision is deterministic service code. LLMs, prompts, and admin UI labels must not override it.

## Audit Requirements

The registry audits:

- License creation.
- License replacement.
- Permission-document metadata access.
- Publication authorization checks.

Audit summaries record policy-relevant metadata and whether permission evidence exists. They do not
store permission-document contents or external credentials.

## Operational Notes

Expired or revoked licenses should trigger downstream suspension workflows in later tasks. Until those
tasks exist, the registry provides the fail-closed check required by ingestion, review, publishing,
and retrieval services.
