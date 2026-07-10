# Scholar Approval Workspace

## Purpose

The scholar approval workspace gives senior scholars and admins one place to inspect evidence, source status, license policy state, madhhab metadata, revision history, and approval records before they create or revoke an approval.

## Access

The workspace uses these APIs:

- `GET /reviews/{review_task_id}/draft`
- `GET /sources/{source_id}`
- `GET /admin/licenses/{license_id}`
- `GET /admin/licenses/{license_id}/policy-decision?workflow=retrieval`
- `GET /documents/{document_version_id}/approval-requirements`
- `GET /documents/{document_version_id}/approvals`
- `POST /reviews/{review_task_id}/approvals`
- `POST /review-approvals/{approval_id}/revoke`

All calls remain subject to server-side RBAC and MFA enforcement. The UI does not treat hidden controls as authorization.

## Main Workflow

1. Open a scholar-level review task.
2. Confirm the document identity, source, and original file metadata.
3. Inspect source reliability, public warnings, license record, and license-policy decision for retrieval workflow.
4. Review editable metadata, madhhab, and recent revision history for potential conflicts.
5. Choose the active content-risk tier to see required, satisfied, and missing approval levels.
6. Create an approval with a reason, or revoke an existing approval with an audited reason.

## Separation of Duties

The backend remains authoritative for self-approval restrictions. If the same actor is not allowed to approve, the workspace surfaces `SCHOLAR_APPROVAL_SELF_APPROVAL_DENIED` as an explicit error and does not guess client-side exceptions.

## Evidence and License Visibility

Before approval, the workspace shows:

- document title, type, canonical ID, language, and madhhab
- original file key and current editable text preview
- source name, reliability level, and public warnings
- license name, version, status, and policy reason codes
- revision history summary and previous approval records

This satisfies the requirement that evidence and license status are visible before approval without exposing secrets, signed URLs, or raw internal traces.

## Current Limitations

- Source display uses public source detail plus license/admin policy endpoints; there is no dedicated scholar aggregate endpoint yet.
- Node-based reviewer test/typecheck/build verification still requires a Node-enabled environment.
- The workspace shows text and metadata previews only; it does not embed original-file download/preview flows.
