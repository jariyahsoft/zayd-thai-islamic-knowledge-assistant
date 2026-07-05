# Code Provenance

Record every imported or adapted third-party code component here before merge.
This log supports the repository's selective-reuse policy and does not apply to
datasets, which must use dataset manifests and license records instead.

## Rules

- Record one entry per imported component or logical import batch.
- Complete the entry before merge.
- Keep the source repository, commit, license, imported paths, and modification
  summary exact enough for later audit.
- Preserve upstream notices and add a matching entry to
  `THIRD_PARTY_NOTICES.md` when attribution is required.
- Require human license review for every imported component.

## Provenance Template

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

## Current Entries

No third-party code has been imported into this repository yet.
