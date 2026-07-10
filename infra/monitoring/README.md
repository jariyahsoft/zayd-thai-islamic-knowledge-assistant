# Monitoring

Owner category: operations maintainers.

This directory contains baseline local monitoring assets for observability tasks.

## Current Assets

- `grafana-dashboard.json` — starter dashboard definition for API, latency, queue, provider, citation, and cost views
- `prometheus.yml` — placeholder configuration; direct scraping is disabled until a protected Prometheus-compatible endpoint is provisioned

## Endpoint

- API metrics snapshot: `GET /admin/dashboard?window_minutes=60` (requires `audit.read` and privileged MFA)

The endpoint returns aggregate JSON only:

- structured JSON summary for repository tests and admin integration

## Runbook Links

Dashboard panels should point operators to:

- `docs/operations/logging.md`
- `docs/operations/tracing.md`
- `docs/operations/metrics.md`

## Notes

- The current repository stage uses in-memory telemetry and dashboard scaffolding.
- Tracing sample rate can be tuned with `TELEMETRY_SAMPLE_RATE` for local observability load control.
- Before production use, move scrape/export state to durable operations infrastructure and review alert thresholds with human operators.
