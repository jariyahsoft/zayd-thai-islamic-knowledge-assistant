# Zayd License Guide

This document separates the rights for source code, documentation, trademarks,
and datasets. Open-source status for the repository does not grant rights over
religious texts, translations, books, or datasets unless a specific manifest or
license record says so.

## 1. Source Code

- Intended license: Apache-2.0
- Canonical file: [`../LICENSE`](../LICENSE)
- Notices: [`../NOTICE`](../NOTICE),
  [`../THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md),
  [`../CODE_PROVENANCE.md`](../CODE_PROVENANCE.md)

Apache-2.0 applies to repository source code unless a specific file or bundled
third-party component says otherwise.

## 2. Documentation

- Intended license: CC BY 4.0
- Scope: authored documentation in `docs/`, task documents, and repository
  guidance unless a page states another license

Documentation may be reused under CC BY 4.0 with required attribution, except
for content that includes third-party material or restricted data.

## 3. Trademarks and Branding

- Policy file: [`../TRADEMARK.md`](../TRADEMARK.md)
- Covered assets: project name, logos, icons, and brand marks

Trademark rights are separate from source-code and documentation licenses. No
open-source or documentation license grants branding rights by default.

## 4. Datasets and Religious Content

Each dataset must have its own manifest and approval record. Unless a dataset
manifest explicitly allows an action, treat the action as denied.

### Default Dataset Rights Statement

Every dataset manifest or related license record must cover:

- persistent storage
- embedding permission
- commercial use
- redistribution
- attribution
- expiry

Use the following default policy until explicit approval exists:

| Right | Default |
|---|---|
| Persistent storage | Denied |
| Embedding permission | Denied |
| Commercial use | Denied |
| Redistribution | Denied |
| Attribution | Required if the source terms require it; otherwise unresolved |
| Expiry | Treat as restricted until validity dates are known |

Unknown, expired, prohibited, or review-required datasets must not be treated
as redistributable sample data.

### Public Repository Rule

The repository may include only:

- manifests
- acquisition scripts that fetch content from authorized upstream sources
- checksums
- attribution metadata
- sample data that is public-domain or explicitly approved for redistribution

The repository must not include unapproved corpora, copyrighted books,
translations, API dumps, or private licensed religious content.

## 5. Third-party Code and Adapted Source

Imported or adapted source code requires:

1. A provenance entry in [`../CODE_PROVENANCE.md`](../CODE_PROVENANCE.md)
2. A notice entry in [`../THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md)
   when attribution is required
3. Preservation of upstream license and notice terms
4. Human license review before merge

When local code adapts upstream material, record the imported path, source
commit, original license, modified files, and a short modification summary.

## 6. Review and Enforcement

- Unknown data rights are restricted by default.
- Human license review is required before merging third-party code or data.
- Repository releases must verify required notice files, dataset manifests, and
  restricted-file rules.
- Questions about legal interpretation should be escalated to the project owner
  or qualified counsel.
