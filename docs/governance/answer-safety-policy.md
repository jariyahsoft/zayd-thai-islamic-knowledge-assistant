# Answer Safety Policy Enforcement

This document records the implementation-facing policy used by
`RiskPolicyEngine` for TASK-08-05. The source governance policy remains
`docs/06_islamic_governance/answer_safety_policy.md`.

## Active Policy

| Field | Value |
|---|---|
| Policy version | `risk-policy-v1` |
| Policy status | `approved` |
| Approval requirement | A new policy version must be reviewed and receive regression tests before activation. |
| Trace rule | Store policy metadata and matched rule IDs only. Do not store raw question text or hidden reasoning. |

## Deterministic Routing

The engine applies deterministic rules before model judgement. LLM output and
classification fallback may add context, but cannot downgrade a restricted or
high-risk rule match.

| Category | Action | Route |
|---|---|---|
| Takfir or judging a named person outside Islam | `restrict` | Scholar route when enabled |
| Violence, terrorism, weapons, illegal activity, or evading law/safety | `restrict` | Legal or safety authority route when enabled |
| Self-harm or unsafe medical instructions | `restrict` | Medical or crisis support route when enabled |
| Divorce, inheritance, marriage, adoption, custody, and complex family rulings | `escalate_to_scholar` | Scholar route |
| Health questions that are not direct unsafe instructions | `require_disclaimer` | Medical professional route |
| Financial contracts, investment, loans, and similar case-specific questions | `require_disclaimer` | Scholar or regulated professional route |
| Medium-risk fiqh or personal advice | `allow_with_warning` | Include madhhab and circumstance warning |
| Low-risk informational questions | `allow` | Normal answer workflow |

## Audit Metadata

Each policy decision records:

- `policy_version`
- `policy_status`
- classification schema version, method, confidence, risk, intent, and madhhab
- matched `rule_id` and safe matched signal source names
- selected action, risk level, restriction reason, and escalation target
- actor identifier supplied by the orchestration layer

The trace must not include provider secrets, raw user text, hidden
chain-of-thought, full conversations, or production payloads.

## Regression Requirements

Policy changes require:

- decision-table tests for each affected category
- adversarial phrasing tests proving model output cannot downgrade restrictions
- policy-version and policy-status trace tests
- approval before using a non-draft policy in runtime configuration
