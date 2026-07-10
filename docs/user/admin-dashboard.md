# Admin Dashboard

The Admin Dashboard displays aggregate operational indicators for authorized admins and auditors. It is intended for service monitoring, not for viewing user conversations, source text, provider credentials, or private request payloads.

## Access and privacy

- `GET /admin/dashboard` requires a valid bearer token, MFA for privileged access, and the server-side `audit.read` permission.
- The dashboard accepts `window_minutes` from 1 to 1440. Invalid values are rejected by the API.
- The response contains only aggregate counts and configured model-cost limits. It never returns Prometheus text, raw telemetry labels, document content, conversation content, signed URLs, or provider secrets.

## Available indicators

- Registered-user, review-queue, open-feedback, and open-incident counts.
- Provider health, local RAG hits, external fallback, citation-failure, and error counters.
- Configured daily provider/model cost limits.

## Telemetry outages

The dashboard fails safely: if telemetry cannot be loaded, the UI clears stale values and displays an availability message. Repository-stage telemetry is process-local, so the selected window is bounded and validated for the dashboard request but is not a replacement for durable production monitoring storage.
