# TASK-00-02 — Add Open-source License Files

## Status

`TODO`

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

- Pending

### Commands and Tests Executed

- Pending

### Acceptance Criteria Result

- Pending

### Security and License Review

- Pending

### Known Limitations

- Pending

### Follow-up Tasks

- Pending

### Commit

- Pending
