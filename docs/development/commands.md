# Developer Commands

Zayd uses `make` at the repository root as its portable command interface. Every command delegates to the underlying workspace tooling (pnpm, uv, Docker Compose).

## Prerequisites

- GNU Make 4.x
- Docker Engine 24+ with Compose v2 plugin
- Node.js 24.18 + corepack + pnpm 9.15
- Python 3.12 + uv
- OpenSSL (for password generation)

## Quick Start

```bash
# Validate environment and install dependencies
make setup

# Start the full development stack
make dev

# Verify everything is healthy
make health
```

## Available Commands

### Setup and Development

| Command | Description |
|---|---|
| `make setup` | Validate prerequisites, install TypeScript and Python dependencies, check config |
| `make dev` | Start the full development stack via `docker compose up -d` |
| `make stop` | Stop all services without removing persistent volumes |
| `make logs` | Tail container logs (follow mode) |
| `make health` | Print service status and hit the API `/health` endpoint |

### Database

| Command | Description |
|---|---|
| `make migrate` | Run database migrations (placeholder — implemented under EPIC-02) |
| `make seed-admin ADMIN_EMAIL=<email>` | Create an initial admin user; password is printed once |
| `make seed-demo` | Load redistributable demo data and print temporary demo credentials once |
| `make backup` | Take a pg_dump of the development database into `backups/` |
| `make restore BACKUP_FILE=<path>` | Restore a development backup (requires interactive confirmation) |

The backup and restore commands are **development-only helpers**. Production backup policy and hardening will be implemented under EPIC-13.

### Quality

| Command | Description |
|---|---|
| `make test` | Run all TypeScript and Python tests |
| `make test-unit` | Run unit tests only |
| `make test-integration` | Run integration tests (requires dev stack) |
| `make lint` | Lint TypeScript (`eslint`) and Python (`ruff`) workspaces |
| `make typecheck` | Run TypeScript (`tsc`) and Python (`mypy`) type checking |
| `make format` | Auto-format TypeScript (`prettier`) and Python (`ruff format`) |
| `make format-check` | Check formatting without modifying files |
| `make build` | Build all workspaces |

### Housekeeping

| Command | Description |
|---|---|
| `make clean` | Remove temporary and build artifacts (preserves PostgreSQL, Redis, and MinIO volumes) |
| `make clean-all` | Remove everything including persistent volumes (requires interactive confirmation) |

## Dangerous Commands

The following commands require explicit confirmation or arguments:

- **`make restore BACKUP_FILE=<path>`** — requires the backup file path and interactive confirmation of the database name.
- **`make clean-all`** — requires interactive "yes" confirmation before removing volumes.
- **`make seed-admin ADMIN_EMAIL=<email>`** — requires an email argument; the password is never printed after generation.

## Secrets and Security

- Commands never echo passwords, tokens, or complete connection strings.
- Demo seed data must contain no private, copyrighted, or restricted content.
- Backup files contain database snapshots and must not be committed to Git.

## Ubuntu Quick Start

```bash
# Install prerequisites (Ubuntu Server 24.04)
sudo apt-get update
sudo apt-get install -y make docker.io docker-compose-v2 nodejs python3.12 openssl

# Clone and set up
git clone <repository-url> zayd
cd zayd

# Install uv (Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Enable corepack and install pnpm
corepack enable
corepack prepare pnpm@9.15.0 --activate

# Run setup
make setup

# Start development
make dev
```

## See Also

- [Configuration Guide](configuration.md)
- [Docker Workflow](docker.md)
- [TypeScript Workspace Guide](typescript.md)
- [Python Workspace Guide](python.md)
- [Monorepo Architecture](../architecture/monorepo.md)
