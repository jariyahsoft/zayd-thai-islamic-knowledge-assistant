# Source and License Admin UI

## Purpose

The admin source and license console is the operational UI for:

- Searching source records.
- Creating and editing sources.
- Suspending sources with visible downstream-impact warnings.
- Creating replacement license versions without overwriting history.
- Reviewing private permission-document metadata.
- Inspecting deterministic policy decisions for ingestion, retrieval, and export workflows.

## Access Model

The UI calls RBAC-protected admin APIs directly.

- Read flows require `licenses.read`.
- Mutations require `licenses.manage`.
- Privileged users inherit the backend MFA requirement.

Current implementation detail:

- The console accepts a temporary bearer token in an in-memory field.
- The token is not persisted to local storage, cookies, or committed files.
- Refreshing the page clears the token.

This keeps the task within current repository scope until a shared admin auth/session client exists.

## Main Workflows

### Source Management

Admins can:

- Search sources by name.
- Review active vs. suspended status.
- Create new sources with reliability, language, owner, website, and country metadata.
- Edit source metadata.
- Suspend a source after reviewing downstream impact text.

### License Management

For the selected source, admins can:

- Review all license versions, newest first.
- Create a new license version.
- Replace an existing version by creating a new row.
- Review permission states for storage, embedding, commercial use, and redistribution.
- Review private permission-document object keys when available.

### Policy Visibility

Admins can switch between:

- `retrieval`
- `ingestion`
- `export`

The UI displays:

- current workflow decision
- reason codes
- source license version
- warnings for unknown or incomplete permissions

## Warnings

The console highlights:

- missing active license coverage
- incomplete or unknown permission states
- missing attribution templates when attribution is required
- missing permission-evidence metadata
- suspension state
- policy-denied workflows

These warnings are informational but designed to fail closed operationally when the backend denies a mutation or policy decision.

## Limitations

- The console depends on a manually pasted bearer token because shared frontend auth is not implemented yet.
- Permission-document content is not exposed; only metadata is shown.
- Downstream ingestion, retrieval, and export services still need to consume the policy engine in their own tasks.
