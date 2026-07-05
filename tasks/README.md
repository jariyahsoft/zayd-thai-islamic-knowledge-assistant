# Zayd Tasks

This directory contains the complete implementation task plan for Zayd 1.0.

## Contents

- `00_task_index.md` — master board for all 95 tasks.
- `00_open_source/` through `14_release/` — task files grouped by epic.
- Every task contains scope, dependencies, acceptance criteria, required tests, security requirements, documentation updates and a completion report.

## Execution Order

1. Open `00_task_index.md`.
2. Work only on a task whose status is `READY`.
3. Read the PRD, SRS and all listed dependencies before implementation.
4. Fill the completion report and run required checks.
5. Mark the task `DONE`, create a focused commit and update newly unblocked tasks to `READY`.

## Important Boundaries

- Never commit API keys, production credentials, user conversations or restricted religious texts.
- Source-code licensing and dataset licensing are separate.
- AI-generated religious metadata or answers are never considered reviewed source material.
- Tier S tasks require a strong reasoning model and human review for security, architecture, migrations, RAG, citation and policy work.
