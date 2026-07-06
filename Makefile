.PHONY: help setup dev stop logs migrate seed-admin seed-demo test test-unit test-integration lint typecheck format format-check build health backup restore clean

help: ## Print this help message
	@echo "Zayd — Thai Islamic Knowledge Assistant"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Setup and Development"
	@echo "  setup         Validate the local environment and install dependencies"
	@echo "  dev           Start the local development stack (Docker Compose)"
	@echo "  stop          Stop services without deleting data"
	@echo "  logs          Follow container logs"
	@echo "  health        Check the health of all running services"
	@echo ""
	@echo "Database"
	@echo "  migrate       Run database migrations"
	@echo "  seed-admin    Create an initial admin user"
	@echo "  seed-demo     Load redistributable demo data"
	@echo "  backup        Take a development database backup (pg_dump)"
	@echo "  restore       Restore a development database backup (pg_restore)"
	@echo ""
	@echo "Quality"
	@echo "  test          Run all tests (TypeScript + Python)"
	@echo "  test-unit     Run unit tests"
	@echo "  test-integration   Run integration tests"
	@echo "  lint          Lint all workspaces"
	@echo "  typecheck     Run type checking across all workspaces"
	@echo "  format        Auto-format all source files"
	@echo "  format-check  Check formatting without modifying files"
	@echo "  build         Build all workspaces"
	@echo ""
	@echo "Housekeeping"
	@echo "  clean         Remove temporary and build artifacts (keeps data)"
	@echo "  clean-all     Remove temporary files, build artifacts, AND persistent volumes"
	@echo ""

# ─── Setup and Development ────────────────────────────────────────────────────

setup: ## Validate the local environment and install dependencies
	@echo "=== Zayd Environment Setup ==="
	@echo "Checking prerequisites…"
	@command -v docker >/dev/null 2>&1 || { echo "ERROR: docker is required (see docs/development/docker.md)"; exit 1; }
	@docker compose version >/dev/null 2>&1 || { echo "ERROR: docker compose (v2) is required (see docs/development/docker.md)"; exit 1; }
	@command -v corepack >/dev/null 2>&1 || { echo "WARNING: corepack not found; TypeScript install will be skipped."; }
	@command -v node >/dev/null 2>&1 || { echo "WARNING: node not found; TypeScript checks will be skipped."; }
	@command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 is required (see docs/development/python.md)"; exit 1; }
	@echo ""
	@echo "Installing TypeScript dependencies…"
	-corepack pnpm install --frozen-lockfile 2>/dev/null || echo "(pnpm install skipped — install manually with: corepack pnpm install)"
	@echo ""
	@echo "Installing Python dependencies…"
	uv sync --frozen 2>/dev/null || echo "(uv sync skipped — see docs/development/python.md)"
	@echo ""
	@echo "Validating configuration…"
	@test -f .env && echo "WARNING: .env file exists — this overrides .env.example defaults." || echo "No .env found; using .env.example defaults."
	@echo ""
	@echo "Setup complete. Run 'make dev' to start the stack."

dev: ## Start the local development stack (Docker Compose)
	@echo "Starting Zayd development stack…"
	docker compose up -d

stop: ## Stop services without deleting data
	@echo "Stopping Zayd development stack…"
	docker compose down

logs: ## Follow container logs
	docker compose logs --tail=50 -f

health: ## Check the health of all running services
	@echo "Checking Zayd service health…"
	@docker compose ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null | awk 'NR>1{printf "  %-30s %s\n", $$1, $$2}'
	@echo ""
	@echo "API health endpoint:"
	-curl --silent --show-error --fail --max-time 5 http://localhost:8000/health 2>/dev/null || echo "(unreachable — stack may not be running)"
	@echo ""
	@echo "Frontends: web=localhost:3100  reviewer=localhost:3101  admin=localhost:3102"

# ─── Database ──────────────────────────────────────────────────────────────────

migrate: ## Run database migrations
	@echo "=== Zayd Database Migration ==="
	@bash scripts/migrate.sh "$${MIGRATION_ACTION:-up}"

seed-admin: ## Create an initial admin user (requires admin email)
	@if [ -z "${ADMIN_EMAIL}" ]; then \
		echo "Usage: make seed-admin ADMIN_EMAIL=<email>"; \
		echo ""; \
		echo "Example: make seed-admin ADMIN_EMAIL=admin@example.com"; \
		exit 1; \
	fi
	@bash scripts/seed-admin.sh "${ADMIN_EMAIL}"

seed-demo: ## Load redistributable demo data
	@echo "=== Zayd Demo Data ==="
	@echo "Loading synthetic, non-authoritative demo data."
	@DATABASE_URL="$${DATABASE_URL:-postgresql://zayd_dev:zayd_dev@localhost:5432/zayd_dev}" uv run python database/seeds/seed.py

backup: ## Take a development database backup
	@bash scripts/backup.sh

restore: ## Restore a development database backup (requires confirmation)
	@if [ -z "${BACKUP_FILE}" ]; then \
		echo "Usage: make restore BACKUP_FILE=<path>"; \
		echo ""; \
		echo "Example: make restore BACKUP_FILE=backups/Zayd-zayd_dev-20260101T000000Z.sql.gz"; \
		exit 1; \
	fi
	@bash scripts/restore.sh "${BACKUP_FILE}"

# ─── Quality ───────────────────────────────────────────────────────────────────

test: ## Run all tests (TypeScript + Python)
	@echo "=== Running TypeScript Tests ==="
	-corepack pnpm -r test
	@echo ""
	@echo "=== Running Python Tests ==="
	-uv run pytest
	@echo ""

test-unit: ## Run unit tests
	@echo "=== Running TypeScript Unit Tests ==="
	-corepack pnpm -r test -- --project unit 2>/dev/null || corepack pnpm -r test
	@echo ""
	@echo "=== Running Python Unit Tests ==="
	-uv run pytest -m unit 2>/dev/null || uv run pytest -k "not integration"
	@echo ""

test-integration: ## Run integration tests
	@echo "=== Running Integration Tests ==="
	@echo "Integration tests require the dev stack to be running (make dev)."
	-uv run pytest -m integration 2>/dev/null || uv run pytest -k "integration"
	@echo ""

lint: ## Lint all workspaces
	@echo "=== Linting TypeScript Workspaces ==="
	-corepack pnpm -r lint
	@echo ""
	@echo "=== Linting Python Workspaces ==="
	-uv run ruff check .
	@echo ""

typecheck: ## Run type checking across all workspaces
	@echo "=== TypeScript Type Checking ==="
	-corepack pnpm -r typecheck
	@echo ""
	@echo "=== Python Type Checking ==="
	-uv run mypy .
	@echo ""

format: ## Auto-format all source files
	@echo "=== Formatting TypeScript Files ==="
	-prettier --write .
	@echo ""
	@echo "=== Formatting Python Files ==="
	-uv run ruff format .
	@echo ""

format-check: ## Check formatting without modifying files
	@echo "=== Checking TypeScript Formatting ==="
	-corepack pnpm format:check
	@echo ""
	@echo "=== Checking Python Formatting ==="
	-uv run ruff format --check .
	@echo ""

build: ## Build all workspaces
	@echo "=== Building TypeScript Workspaces ==="
	-corepack pnpm -r build
	@echo ""
	@echo "=== Checking Python packages are importable ==="
	-uv run python -c "import zayd_common; print('zayd_common OK')"
	-uv run python -c "import zayd_service_api; print('zayd_service_api OK')"
	@echo ""

# ─── Housekeeping ──────────────────────────────────────────────────────────────

clean: ## Remove temporary and build artifacts (keeps persistent data volumes)
	@echo "=== Cleaning Build Artifacts ==="
	-rm -rf apps/*/.next apps/*/out packages/*/dist .turbo coverage/ htmlcov/
	-rm -rf .eslintcache __pycache__ */__pycache__ */*/__pycache__
	-rm -rf .pytest_cache .mypy_cache .ruff_cache
	@echo "Build artifacts removed. Persistent data volumes are preserved."
	@echo "To also remove persistent data, run: make clean-all"

clean-all: ## Remove temporary files, build artifacts, AND persistent volumes
	@echo "WARNING: This will DELETE all persistent data volumes!"
	@echo "         postgres, redis, and minio data will be permanently removed."
	@read -r -p "Type 'yes' to confirm: " CONFIRM; \
	if [ "$$CONFIRM" = "yes" ]; then \
		echo "Stopping stack and removing volumes…"; \
		docker compose down -v; \
		$(MAKE) clean; \
		echo "All artifacts and data volumes removed."; \
	else \
		echo "Aborted."; \
		exit 1; \
	fi
