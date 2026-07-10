# Logging and Request IDs

Zayd uses structured JSON logs for API and worker runtime events. Every request or background execution should carry:

- `request_id`
- `trace_id`
- `service`
- log `level`
- a sanitized `message`

## Request Context

- The API accepts `x-request-id` and `x-trace-id`.
- When headers are missing, the API generates stable IDs and returns them in response headers.
- Worker lifecycle logs generate their own request/trace context.
- Services should reuse propagated IDs instead of inventing unrelated values mid-flow.

## Redaction Rules

The logging layer redacts sensitive keys and token-like values by default, including:

- passwords
- tokens
- secrets
- cookies
- authorization headers
- signed URLs
- prompt bodies

Avoid logging:

- full conversation text
- prompt contents
- provider credentials
- raw uploaded documents

## Failure Behavior

Logging must not break request handling. The stream handler swallows formatter/output failures and falls back to normal application execution.

## Operational Notes

- Use response headers `x-request-id` and `x-trace-id` to correlate client-visible failures with logs.
- Audit logs remain the source of truth for privileged mutations; runtime logs provide execution context only.
