# Zayd

**Zayd — Thai Islamic Knowledge Assistant** เป็นโครงการโอเพนซอร์สสำหรับสร้างผู้ช่วยค้นคว้าความรู้อิสลามภาษาไทย โดยเน้นหลักฐานที่ตรวจสอบย้อนกลับได้ การแยกทัศนะตามมัซฮับ และกระบวนการตรวจทานโดยผู้รู้

> Zayd ไม่ใช่มุฟตี AI และไม่ใช่ระบบออกฟัตวาอัตโนมัติ

## เอกสารก่อนเริ่ม Coding

เอกสารหลักอยู่ใน [`docs/`](docs/README.md):

- Master Development Plan: [`docs/00_project/01_master_development_plan.md`](docs/00_project/01_master_development_plan.md)
- Product Requirements Document: [`docs/01_product/PRD.md`](docs/01_product/PRD.md)
- Software Requirements Specification 1.1: [`docs/02_requirements/SRS.md`](docs/02_requirements/SRS.md)
- System Architecture: [`docs/03_architecture/system_architecture.md`](docs/03_architecture/system_architecture.md)
- Data License Policy: [`docs/05_data/license_policy.md`](docs/05_data/license_policy.md)
- Madhhab Policy: [`docs/06_islamic_governance/madhhab_policy.md`](docs/06_islamic_governance/madhhab_policy.md)
- Scholar Review Policy: [`docs/06_islamic_governance/scholar_review_policy.md`](docs/06_islamic_governance/scholar_review_policy.md)
- Answer Safety Policy: [`docs/06_islamic_governance/answer_safety_policy.md`](docs/06_islamic_governance/answer_safety_policy.md)
- Security Architecture: [`docs/07_security/security_architecture.md`](docs/07_security/security_architecture.md)
- Evaluation Plan: [`docs/08_evaluation/evaluation_plan.md`](docs/08_evaluation/evaluation_plan.md)
- AI Coding Agent Policy: [`docs/09_development/ai_coding_agent_policy.md`](docs/09_development/ai_coding_agent_policy.md)

## Baseline v1.4

Baseline v1.4 ปรับปรุง `docs/02_requirements/` โดยกำหนด `SRS.md` ฉบับเต็มเป็น canonical specification เก็บฉบับย่อเป็น `SRS_summary.md` และขยาย Requirements Traceability Matrix ให้เชื่อมกับ Tasks และ Quality Gates อย่างละเอียด

## งานพัฒนา

โฟลเดอร์ [`tasks/`](tasks/README.md) มี Task ทั้งหมด 95 งาน ครอบคลุม EPIC-00 ถึง EPIC-14

เริ่มจาก:

1. อ่านเอกสารใน `docs/`
2. ตรวจ [`tasks/00_task_index.md`](tasks/00_task_index.md)
3. เริ่มจาก `TASK-00-01`
4. ทำงานตาม dependency
5. อัปเดต Completion Report และสถานะ Task ทุกครั้ง

## Monorepo Structure

Zayd is organized as a monorepo with frontend apps, backend services, shared packages, plugins, database assets, infrastructure placeholders, and documentation:

- [`apps/`](apps/README.md) — user, reviewer, and admin applications
- [`services/`](services/README.md) — API, orchestration, retrieval, ingestion, worker, and evaluation services
- [`packages/`](packages/README.md) — shared TypeScript packages and SDK interfaces
- [`plugins/`](plugins/README.md) — allow-listed provider and storage adapters
- [`database/`](database/README.md) — migrations, schemas, seeds, and database tests
- [`infra/`](infra/README.md) — Docker, Compose, proxy, monitoring, and operational scripts
- [`docs/architecture/monorepo.md`](docs/architecture/monorepo.md) — dependency boundaries and ownership rules

## Repository Foundation

- Repository hygiene is defined in [`.gitignore`](.gitignore), [`.editorconfig`](.editorconfig), and [`.gitattributes`](.gitattributes).
- Commit conventions and protected-branch recommendations are documented in [CONTRIBUTING.md](CONTRIBUTING.md).
- Source-code, documentation, dataset, and trademark rights are documented in [docs/LICENSES.md](docs/LICENSES.md).
- The repository Apache-2.0 license text and notice files are in [LICENSE](LICENSE), [NOTICE](NOTICE), [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), [CODE_PROVENANCE.md](CODE_PROVENANCE.md), and [TRADEMARK.md](TRADEMARK.md).
- Community governance and support documents are in [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), [GOVERNANCE.md](GOVERNANCE.md), [SECURITY.md](SECURITY.md), [SUPPORT.md](SUPPORT.md), [ROADMAP.md](ROADMAP.md), and [CHANGELOG.md](CHANGELOG.md).
- Supplemental bundled license materials belong under [licenses/README.md](licenses/README.md).
- The default branch should be `main`.

## สถานะ

เอกสารชุดนี้เป็น **Baseline v1.4 ก่อนเริ่ม Coding** และต้องผ่านการทบทวนจากทีมผลิตภัณฑ์ ทีมเทคนิค และคณะผู้รู้ก่อนเปลี่ยนสถานะเป็น Approved

## Support and Governance

- Project governance and RFC guidance: [GOVERNANCE.md](GOVERNANCE.md)
- Contribution expectations: [CONTRIBUTING.md](CONTRIBUTING.md)
- Private security reporting: [SECURITY.md](SECURITY.md)
- Community support boundaries: [SUPPORT.md](SUPPORT.md)

## Developer Commands

Zayd uses `make` as its portable command interface. See the full reference at [`docs/development/commands.md`](docs/development/commands.md).

```bash
make setup       # validate environment and install dependencies
make dev         # start the development stack
make stop        # stop services (preserves data)
make test        # run all tests (TypeScript + Python)
make lint        # lint all workspaces
make build       # build all workspaces
make help        # list all available commands
```

Individual tool commands are also available directly:

- `corepack pnpm install --frozen-lockfile`
- `corepack pnpm lint`
- `corepack pnpm typecheck`
- `corepack pnpm test`
- `corepack pnpm build`
- `corepack pnpm format:check`
- `uv sync --frozen`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run mypy .`
- `uv run pytest`
- `docker compose up -d`
- `docker compose down`
- `docker compose down -v`

## Docker Development Stack

- Root Compose entrypoint: `docker-compose.yml`
- Development stack definition: `infra/compose/development.yml`
- Published ports: `8000` for API, `3100` for web, `3101` for reviewer, and `3102` for admin
- Detailed Docker workflow: [`docs/development/docker.md`](docs/development/docker.md)
- Configuration reference: [`docs/development/configuration.md`](docs/development/configuration.md)
