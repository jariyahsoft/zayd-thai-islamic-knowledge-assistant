# Prompt Management

This document records the implementation-facing prompt governance used by
`PromptRegistryService` for TASK-08-09. The source requirements remain SRS §28
and FR-ADM-004.

## Active Registry

| Field | Value |
|---|---|
| Registry version | `prompt-registry-v1` |
| Default answer prompt | `answer-generation` / `v1` |
| Default policy | `answer-safety` / `v1` |
| Production rule | Only `approved` prompt versions may be resolved for answer generation |

## Versioned Prompt Records

Each prompt version stores:

- `name` and `version`
- `prompt_body` and `prompt_hash`
- `purpose`, `owner`, `input_schema`, `output_schema`
- `changelog` and `test_cases`
- `status` (`draft`, `approved`, `deprecated`, `archived`)
- `created_by`, `approved_by`, timestamps, and registry metadata

New prompts are always created as `draft`. Activation requires the
`prompts.manage` permission through the approve endpoint.

## Production Restrictions

- `resolve_answer_dependencies()` fails closed when no approved prompt exists.
- Draft, archived, or deprecated prompts cannot be used for answer generation.
- Rollback re-approves a prior `approved` or `deprecated` version and records an
  audit event.
- Comparison is read-only and reports body, schema, owner, changelog, and test
  case differences between two versions.

## Answer Trace Requirements

Every generated answer must record:

- `prompt_version`
- `prompt_version_id`
- `policy_version_id`
- `model_configuration_id`

The trace must not expose hidden system prompts, provider secrets, or hidden
chain-of-thought to end users.

## Audit Metadata

Sensitive prompt mutations write append-only audit records for:

- `prompts.create`
- `prompts.approve`
- `prompts.rollback`

Audit entries include actor, resource id, trace id, and safe before/after
summaries only.

## API Surface

Admin endpoints under `/admin/prompts` require `prompts.manage`:

- create draft prompt versions
- list and fetch prompt versions
- approve draft or deprecated versions
- rollback to a prior approved version
- compare two versions
- bootstrap default prompt, policy, and LLM model records for development

## Regression Requirements

Prompt changes require:

- lifecycle tests for create, approve, rollback, and compare
- RBAC tests proving draft activation is permission-gated
- orchestration trace tests proving generated answers record prompt versions
- approval before using a non-approved prompt in runtime configuration