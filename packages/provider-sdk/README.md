# Provider SDK Package

Owner category: provider interface maintainers.

TypeScript-facing provider interfaces and shared types. Provider-specific code belongs under `plugins/`.

The package exports the stable provider contract used by UI, admin, and plugin
integration code:

- LLM providers
- embedding providers
- knowledge providers
- rerankers
- vector stores

Provider loading must go through an explicit allow-list. Secret values must not
be stored in package objects; use secret references only.
