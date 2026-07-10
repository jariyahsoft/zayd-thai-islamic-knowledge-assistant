# Tracing

Zayd uses lightweight in-process tracing hooks to prepare observability without exposing sensitive religious or user content.

## Coverage

Current tracing spans cover:

- API request lifecycle
- Orchestrator answer execution
- Retrieval hybrid search
- LLM provider generate/health-check calls
- Worker lifecycle events

## Propagation

- `x-request-id` and `x-trace-id` enter through the API boundary.
- When trace headers are absent, the API generates them once and reuses them.
- Orchestrator and retrieval components reuse the propagated trace ID in span attributes.
- Worker processes create their own trace context for background execution.

## Sensitive Data Rules

Span attributes must not include:

- prompt bodies
- full user questions or answers
- raw document text
- tokens, secrets, or signed URLs

The telemetry sanitizer strips attribute keys that look like message, prompt, token, secret, or document body fields.

## Current Limitations

- Tracing is process-local for now; it is not yet exported to an external collector.
- Span history is kept in memory and intended for metrics/dashboard foundation work in this repository stage.
- Sampling is configurable through `TELEMETRY_SAMPLE_RATE` with a `0.0` to `1.0` range. The current implementation applies deterministic trace/request-based sampling inside the in-process registry.
