# TASK-03-04 — Implement MFA for Privileged Users

## Status

`TODO`

## Model Tier

Tier A

## Related Requirements

- FR-AUTH-004
- NFR-SEC-004

## Objective

Add TOTP-based MFA for reviewer, senior scholar and admin roles.

## Scope

### In Scope

- Add TOTP-based MFA for reviewer, senior scholar and admin roles.
- Provide single-use recovery codes and secure reset workflow.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-03-03

## Expected Files

- Implementation files under the relevant `03_auth` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Use server-side enforcement and least privilege.
- Do not log credentials, tokens or sensitive recovery material.
- Return stable, non-enumerating error responses.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Apply OWASP authentication/session guidance and rate limiting.

## Acceptance Criteria

- [ ] Privileged access is blocked until MFA is configured and verified.
- [ ] Recovery codes are hashed, single-use and rotatable.
- [ ] MFA reset is audited and requires elevated verification.

## Required Tests

### Unit and Contract Tests

- TOTP verification tests
- Recovery-code reuse test
- Privileged-login E2E tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/security/mfa.md`
- `docs/user/admin-mfa.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- Pending

### Commands and Tests Executed

- Pending

### Acceptance Criteria Result

- Pending

### Security and License Review

- Pending

### Known Limitations

- Pending

### Follow-up Tasks

- Pending

### Commit

- Pending
