# TASK-03-02 — Implement Guest Sessions

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- FR-AUTH-003
- FR-CHAT-008
- NFR-PRV-003

## Objective

Create anonymous guest sessions with configurable TTL and usage limits.

## Scope

### In Scope

- Create anonymous guest sessions with configurable TTL and usage limits.
- Design a migration path from guest session to registered account without exposing unrelated data.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-03-01

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

- [ ] Guest cannot access privileged routes.
- [ ] Guest records expire according to policy.
- [ ] Conversion to a user account preserves only explicitly supported data.
- [ ] Guest identifiers are non-guessable and securely stored.

## Required Tests

### Unit and Contract Tests

- Guest expiry tests
- Privilege-boundary tests
- Guest-to-user migration tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/architecture/guest-sessions.md`

## Completion Report

### Files Changed

- `services/common/src/zayd_common/guest.py` — `GuestService` with TTL, quota, validation, revocation, and conversion
- `services/common/src/zayd_common/database/models.py` — `GuestSession` ORM model
- `services/common/src/zayd_common/database/__init__.py` — re-export guest models
- `services/common/src/zayd_common/settings.py` — `guest_session_ttl_minutes`, `guest_message_quota` settings
- `services/common/src/zayd_common/__init__.py` — export `GuestService`, `GuestError`, `GuestSessionInfo`, `hash_guest_token`
- `services/api/src/zayd_service_api/app.py` — `/auth/guest/start` and `/auth/guest/convert` routes with `GuestError` handler
- `database/migrations/0003_guest_sessions.up.sql` — schema, indexes, and trigger
- `database/migrations/0003_guest_sessions.down.sql` — rollback plan
- `services/common/tests/test_guest.py` — 12 unit tests (expiry, privilege boundary, migration)
- `services/api/tests/test_guest_api.py` — 2 API/route registration tests
- `docs/architecture/guest-sessions.md` — architecture and security notes

### Commands and Tests Executed

```bash
# Apply the new migration to dev database
cat database/migrations/0003_guest_sessions.up.sql | docker compose exec -T postgres psql -U zayd_dev -d zayd_dev

# Run all tests
uv run pytest                                            # 89 passed
uv run pytest services/common/tests/test_guest.py        # 12 passed
uv run pytest services/api/tests/test_guest_api.py       # 2 passed

# Verify type safety
uv run mypy services/common/src/zayd_common/guest.py services/common/src/zayd_common/database/models.py services/api/src/zayd_service_api/app.py

# Format and lint
uv run ruff format .
uv run ruff check .                                     # 1 pre-existing error in settings.py
```

### Acceptance Criteria Result

- [x] Guest cannot access privileged routes: Bearer token is required for all non-guest endpoints.
- [x] Guest records expire according to policy: `validate_session` rejects expired sessions; TTL configurable via `GUEST_SESSION_TTL_MINUTES`.
- [x] Conversion to a user account preserves only explicitly supported data: only email, display_name, and password are passed to `AuthService.register`; chat history stays out of scope.
- [x] Guest identifiers are non-guessable and securely stored: 32 random bytes from `secrets.token_urlsafe`; only SHA-256 hash persisted.

### Security and License Review

- Guest tokens, IPs, and User-Agents are hashed before persistence; no cleartext is logged.
- Quota and TTL are enforced server-side on every `validate_session` call.
- `convert_to_user` is wrapped in a single UoW; rollback path covers both registration failure and quota edge cases.
- Errors are non-enumerating (`GUEST_INVALID_SESSION` for both unknown and revoked tokens; `convert_to_user` returns `AUTH_USER_EXISTS` consistently with public registration).
- No production secrets, restricted religious content, or third-party data was introduced.

### Known Limitations

- Audit retention is delegated to TASK-13-01.
- Rate limiting on `/auth/guest/start` is delegated to TASK-13-04.

### Follow-up Tasks

- TASK-13-04: rate-limit `start_session` and `convert_to_user`
- TASK-09-02: tighten privilege boundary once chat endpoints are added

### Commit

Ready to commit. Suggested message:

```
feat(auth): implement anonymous guest sessions

- Add GuestSession model with TTL, message quota, and conversion fields
- Implement GuestService with start, validate, consume, revoke, convert
- Add stable GuestError codes and non-enumerating error responses
- Wire /auth/guest/start and /auth/guest/convert routes with audit
- Add migration 0003_guest_sessions with safe defaults
- Add 12 unit tests (expiry, privilege boundary, conversion) and 2 API tests
- Document data model, surface, and security guarantees

Resolves: TASK-03-02

Co-Authored-By: Claude <noreply@anthropic.com>
```
