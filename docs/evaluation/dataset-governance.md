# Dataset Governance Policy

To guarantee correctness, authenticity, and compliance with copyright restrictions, the Zayd Thai Islamic Knowledge Assistant follows a strict data governance framework for all benchmark and evaluation case materials.

## Scholar Approval Requirement
- Plausibility checklist checks: No auto-generated case, question, or reference is valid for evaluation unless a human reviewer has signed off on the record.
- Seeding tasks and case uploads require a valid `reviewed_by` actor ID referring to an active scholar or administrator in the database.
- AI-generated draft answers can be used for initial drafting during benchmark case development, but they **must not** be marked approved or used in test sets without scholar sign-off.

## Separation of Public and Private Assets
To avoid leaking copyrighted textual resources or violating software/content licenses:
1. **Public Subsets (`public_cases.json`)**: Contains queries and reference links built from redistributable content only (such as Public Domain or CC-BY-SA license types).
2. **Private Subsets (`private_cases.json`)**: Contains safety-critical, proprietary, or contractually protected textual materials. These cases must not be redistributed beyond their allowed permission.

## Licences and Provenance manifests
Each case contract records a strict `sources` list declaring:
- `source_id` pointing to the canonical document registry.
- `license_name` and `license_status` fields (e.g. `persistent_redistributable`, `persistent_private`).
- `redistributable` boolean.

The creation service rejects public visibilities when one or more sources are not redistributable.
Public exports of evaluation runs (visible to users without `evaluations.read` clearance) exclude private cases and redact evaluator notes to prevent privacy breaches.
