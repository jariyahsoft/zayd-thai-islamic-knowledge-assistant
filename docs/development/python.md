# Python Services

## Tooling

Zayd uses Python 3.12.3 with `uv` for locking and installation. Shared quality commands are run from the repository root:

- `uv sync --frozen`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run mypy .`
- `uv run pytest`

## Service Boundaries

- Each Python service is an independently importable package under `services/*/src`.
- Shared settings, health models, and logging helpers live in `services/common`.
- Services must not import each other's internal modules directly.
- Provider-specific adapters remain outside service packages.

## Settings and Secrets

- Typed settings use `pydantic-settings`.
- Secrets use `SecretStr` and must remain redacted in representations and logs.
- Do not commit real provider tokens, database passwords, or production URLs.

## Async Conventions

- Async entry points should be explicit and testable.
- `pytest-asyncio` is configured for future async tests.
- Service health endpoints and placeholder functions must not disclose sensitive configuration.
