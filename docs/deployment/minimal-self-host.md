# Minimal self-host deployment

The minimal profile runs the user web application, API, worker, PostgreSQL/pgvector, Redis, and
private MinIO storage on one Ubuntu host. The default local-AI mode adds Ollama and requires no
proprietary API credential. This profile is intended for evaluation and small self-hosted
installations; it is not the production high-availability profile.

## Host prerequisites

- Ubuntu Server 24.04 LTS or a compatible Linux distribution
- Docker Engine with Compose v2
- OpenSSL, Git, at least 4 CPU cores, 16 GiB RAM, and sufficient encrypted disk space
- A firewall allowing only SSH and the intended web port; the API binds to loopback by default

## Fresh installation

```bash
git clone <repository-url> zayd
cd zayd
bash scripts/self-host.sh init
bash scripts/self-host.sh validate
bash scripts/self-host.sh up
bash scripts/self-host.sh migrate
bash scripts/self-host.sh seed-admin admin@example.org
bash scripts/self-host.sh health
```

`init` creates `.env.self-host` with mode `0600` and locally generated database, storage, JWT, and
session secrets. It does not print them. The file is ignored by Git; back it up through an approved
secret-management channel. `up` pulls the configured Ollama model in local mode. The initial admin
password is shown once by `seed-admin`; rotate it and enroll MFA immediately.

The dependency health response is available at `http://127.0.0.1:8000/health/dependencies`. It
reports only `ok` or `unavailable` for database, Redis, object storage, and the configured LLM
endpoint; it never returns URLs or credentials. `/health` remains the process liveness check.

## Provider modes

Local mode is the generated default:

```text
PROVIDER_MODE=local
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=http://ollama:11434
ENABLE_EXTERNAL_PROVIDERS=false
LLM_API_KEY=
```

For a cloud/OpenAI-compatible adapter, set `PROVIDER_MODE=cloud`, explicitly configure its HTTPS
base URL, model and secret API key, and set `ENABLE_EXTERNAL_PROVIDERS=true`. Review provider data
classification, retention, licensing, and user disclosure before enabling external transfer. Never
commit the resulting environment file.

## Operations

```bash
bash scripts/self-host.sh seed-demo       # synthetic/redistributable demo data only
bash scripts/self-host.sh upgrade         # pull/build, migrate, and recreate safely
bash scripts/self-host.sh down
```

Take an encrypted backup before every upgrade. The upgrade command applies forward migrations and
keeps named volumes. Rollback of application images must respect database migration compatibility;
use the documented restore process when a migration cannot be safely rolled back. Check container
health and the dependency endpoint after every change.

PostgreSQL, Redis, and MinIO are not published on host ports and share an internal data network.
Expose the web service through a TLS reverse proxy for any non-local use. The minimal profile is a
single failure domain and does not meet production availability targets.
