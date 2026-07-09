# Provider SDK

`TASK-08-01` defines the stable provider contracts used by orchestration and
provider adapters. Business logic imports these contracts instead of importing a
vendor SDK directly.

## Contract Families

The SDK covers five provider kinds:

- `llm`
- `embedding`
- `knowledge`
- `reranker`
- `vector_store`

Each provider exposes:

- identity and SDK/API version metadata
- capability declaration
- configuration validation
- health checks
- structured request and response objects

The Python implementation lives in
`services/orchestrator/src/zayd_service_orchestrator/provider_sdk.py`. The
TypeScript-facing contract lives in `packages/provider-sdk/src/index.ts` for UI
and plugin integration surfaces.

## Allow-Listed Loading

Providers must be registered in `AllowListedProviderRegistry` before they can be
loaded. Unknown providers fail with `PROVIDER_NOT_ALLOWED`, and disabled
registrations fail with `PROVIDER_DISABLED`.

This keeps provider loading explicit and prevents arbitrary runtime adapter
execution.

## Mock Providers

The orchestrator package includes deterministic mock implementations for:

- LLM generation and streaming
- embedding generation
- external knowledge search and document fetch
- reranking
- vector-store search, upsert, and delete

Mocks are intended for contract tests and local development. They do not call
external systems, do not require secrets, and return stable outputs.

## Security Rules

- Store and pass secret references, not secret values.
- Do not persist hidden chain-of-thought or raw provider credentials.
- Keep provider traces limited to SDK version, trace IDs, model/provider
  identity, and safe operational metadata.
- Validate provider configuration before use.
- Treat external provider content as untrusted input.

## Versioning

The initial SDK version is `provider-sdk-v1`. Future breaking contract changes
must introduce a new version and keep backward-compatibility tests for supported
versions.
