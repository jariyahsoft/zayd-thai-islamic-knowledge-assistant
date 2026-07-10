# Provider Management

The admin workspace now includes a dedicated Providers and Models section for
`TASK-10-05`.

## What admins can do

- Create provider records for `llm`, `embedding`, `knowledge`, `reranker`, and
  `vector_store` integrations
- Update provider status, base URL, terms URL, and data-policy metadata
- Store or rotate a provider `secret_ref` without reading the previous value
- Run audited provider connection tests
- Create and update model routes with:
  - allow-list flags
  - default-route selection
  - fallback model links
  - daily cost limits
  - structured configuration JSON

## Secret handling

- Secrets are write-only from the UI
- The API returns `secret_configured` plus a `secret_mask` status only
- Existing secret references are never echoed back to the browser after save

## Disable impact

Each provider row includes an impact summary before disablement:

- enabled model count attached to that provider
- impacted model types
- fallback readiness for each affected model type
- whether disablement is currently safe without breaking fallback coverage

This satisfies the requirement to surface fallback readiness before disabling a
provider.

## Connection tests

- Connection tests are exposed at `POST /admin/providers/{provider_id}/test-connection`
- Tests are audited with immutable audit events
- Repeated tests are rate-limited per actor and provider
- A disabled provider still returns configuration-validation feedback without
  exposing secrets

## Model routing

Model routes support:

- primary/default model selection by `model_type`
- fallback model selection for the same `model_type`
- allow-list status
- cost-limit metadata

Defaults require both:

- an enabled provider
- an enabled model

If an admin tries to remove the only enabled default route without a valid
replacement, the API fails closed.
