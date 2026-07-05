# TASK-00-02 — Add Open-source License Files

## Status

`IN_REVIEW`

## Model Tier

Tier A

## Related Requirements

- SRS §5 License Structure
- SRS §4 Data License Separation
- FR-OSS-005 — Provide redistributable sample data only
- SRS §36.6 License Tests
- SRS §42 Data Contribution Workflow

## Objective

Establish the legal and provenance files required to release Zayd as an open-source platform while keeping software, documentation, trademarks and datasets under clearly separated terms.

## Scope

### In Scope

Create and document:

```text
LICENSE
NOTICE
THIRD_PARTY_NOTICES.md
CODE_PROVENANCE.md
TRADEMARK.md
docs/LICENSES.md
licenses/README.md
```

- Use Apache License 2.0 for the source code unless the project owner records a later decision.
- State that documentation is intended for CC BY 4.0.
- Define that each dataset has its own manifest and license.
- Define how adapted source code is attributed.
- Define basic permitted and restricted uses of the Zayd name and logo.

### Out of Scope

- Providing legal advice.
- Registering a trademark.
- Importing third-party code.
- Distributing religious texts or datasets.
- Selecting licenses for datasets that have not yet been approved.

## Dependencies

- TASK-00-01

## Expected Files

```text
LICENSE
NOTICE
THIRD_PARTY_NOTICES.md
CODE_PROVENANCE.md
TRADEMARK.md
docs/LICENSES.md
licenses/README.md
```

## Functional Requirements

1. `LICENSE` must contain the complete Apache License 2.0 text.
2. `NOTICE` must identify Zayd and explain that third-party notices may apply.
3. `THIRD_PARTY_NOTICES.md` must provide a standard entry format.
4. `CODE_PROVENANCE.md` must record source repository, commit hash, original license, imported path, modifications and review status.
5. `docs/LICENSES.md` must clearly distinguish software, documentation, trademark and dataset rights.
6. Dataset redistribution must be denied by default unless a dataset manifest explicitly allows it.

## Technical Requirements

Provide a provenance entry template with these fields:

```yaml
component:
source_repository:
source_commit:
source_path:
original_license:
imported_date:
modified_files:
modification_summary:
reviewed_by:
review_status:
```

Provide a dataset rights statement covering:

- persistent storage
- embedding permission
- commercial use
- redistribution
- attribution
- expiry

## Security Requirements

- Do not claim rights over Quran, hadith, translations or books merely because software is open source.
- Require a human license review before third-party code or data is merged.
- Mark all unknown data rights as restricted by default.

## Acceptance Criteria

- [ ] Apache-2.0 full text is present.
- [ ] Software, documentation, trademark and dataset rights are separated.
- [ ] Third-party code attribution format is documented.
- [ ] Dataset reuse is restricted by default pending explicit approval.
- [ ] No unapproved content or copyrighted corpus is included.
- [ ] Files are linked from the root README.

## Required Tests

### Automated Checks

- Run a license-file presence check.
- Confirm `LICENSE` is recognized as Apache-2.0 by the repository platform when possible.

### Manual Review

- Human project-owner review.
- Human license/compliance review before marking `DONE`.

## Documentation Updates

- Root `README.md`
- `CONTRIBUTING.md`
- `docs/LICENSES.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `LICENSE`
- `NOTICE`
- `THIRD_PARTY_NOTICES.md`
- `CODE_PROVENANCE.md`
- `TRADEMARK.md`
- `docs/LICENSES.md`
- `licenses/README.md`
- `README.md`
- `CONTRIBUTING.md`
- `tasks/00_open_source/00-02_add_open_source_license_files.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `test -f LICENSE -a -f NOTICE -a -f THIRD_PARTY_NOTICES.md -a -f CODE_PROVENANCE.md -a -f TRADEMARK.md -a -f docs/LICENSES.md -a -f licenses/README.md`
- `rg -n "Apache License|Version 2.0" LICENSE`
- `rg -n "docs/LICENSES.md|LICENSE|NOTICE|THIRD_PARTY_NOTICES.md|CODE_PROVENANCE.md|TRADEMARK.md|licenses/README.md" README.md`
- `git diff --check`
- Manual review of license separation, dataset default restrictions, and provenance template coverage

### Acceptance Criteria Result

- Passed: Apache-2.0 full text is present in `LICENSE`.
- Passed: Software, documentation, trademark, and dataset rights are separated in `docs/LICENSES.md`.
- Passed: Third-party code attribution and provenance formats are documented.
- Passed: Dataset reuse and redistribution are restricted by default pending explicit approval.
- Passed: No unapproved corpora, religious texts, or copyrighted datasets were added.
- Passed: Root `README.md` links to the new license and policy documents.

### Security and License Review

- No secrets, credentials, or restricted datasets were added.
- The dataset policy keeps unknown rights restricted by default.
- Third-party code and data require human license review before merge.
- Final task approval still requires human project-owner and compliance review.

### Known Limitations

- Repository-platform SPDX recognition was not verifiable from the local workspace alone.
- No third-party code entries exist yet; the notice and provenance files currently contain templates and policy guidance.

### Follow-up Tasks

- Human project-owner review of the selected license structure.
- Human legal/compliance review before changing task status from `IN_REVIEW` to `DONE`.
- Future selective reuse must populate `THIRD_PARTY_NOTICES.md`, `CODE_PROVENANCE.md`, and `licenses/` with real component records.

### Commit

- Pending focused commit creation
