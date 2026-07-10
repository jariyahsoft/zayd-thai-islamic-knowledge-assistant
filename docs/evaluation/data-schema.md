# Evaluation Data Schema

Schema version `evaluation-case-v1` defines six deterministic case types: multiple choice,
open-ended, retrieval-only, citation, abstention, and risk routing. Unknown fields are rejected.
Type-specific validation requires the corresponding outcome and, for multiple choice, unique choices
plus valid expected choice keys.

Every case records source references, license name/status, redistributability, expected behavior,
risk level, reviewer status, reviewer ID when reviewed, provenance, and public/private visibility.
Public cases must be approved and every source must be redistributable. Private cases require
`evaluations.read`; creation requires MFA-backed `evaluations.manage`.

Dataset versions are immutable identities keyed by name and version. Evaluation cases are unique by
dataset and case key. Case content must not be copied into audit summaries; audits contain only IDs,
case key, type, visibility, and schema version.

The source-of-truth runtime contract is
`services/evaluation/src/zayd_service_evaluation/schema.py`. Migration `0017` upgrades the initial
evaluation tables and adds evaluation-specific RBAC grants.
