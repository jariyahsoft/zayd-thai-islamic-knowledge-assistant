# TASK-09-03 — Citation Cards and Source Detail

## Status

`DONE`

## Model Tier

Tier A

## Related Requirements

- FR-CIT-005
- FR-CIT-008

## Objective

Create distinct citation cards for Quran, hadith and books plus a source-detail view showing original text, Thai translation, metadata and verification state.

## Scope

### In Scope

- Create distinct citation cards for Quran, hadith and books plus a source-detail view showing original text, Thai translation, metadata and verification state.

### Out of Scope

- Unrelated features from later milestones.
- Importing restricted datasets or production secrets.
- Changing approved product, religious-content or license policy outside the task scope.

## Dependencies

- TASK-08-07
- TASK-09-02

## Expected Files

- Implementation files under the relevant `09_user_web` application/service/package area.
- Unit and integration tests for the new behavior.
- Configuration, migration or API contract changes required by the task.
- Documentation files listed below.

## Functional Requirements

- Implement the behavior described in this task using the approved PRD, SRS and architecture boundaries.
- Return stable, documented errors for invalid input, forbidden operations and unavailable dependencies.
- Record required version, status, actor and trace metadata so the behavior can be audited and evaluated.
- Preserve backward compatibility unless the task explicitly includes a migration or version change.

## Technical Requirements

- Use generated API clients/contracts where available.
- Meet responsive, accessibility and safe-rendering requirements.

## Security Requirements

- Do not commit secrets, production data or restricted religious content.
- Enforce RBAC and audit sensitive mutations.
- Validate all external input and fail closed for security- or license-critical decisions.
- Sanitize rendered content and avoid leaking internal traces.

## Acceptance Criteria

- [x] AI explanation is visually separated from source text.
- [x] Invalidated/suspended sources show clear warnings.
- [x] RTL/LTR content is rendered correctly.

## Required Tests

### Unit and Contract Tests

- Citation component tests
- Source detail E2E
- Accessibility tests

### Integration and End-to-End Tests

- Add integration or end-to-end coverage for the main success path and at least one failure path.
- Confirm permission, audit and data-visibility behavior where applicable.
- Run lint, type checks and relevant security/license scans.

## Documentation Updates

- `docs/frontend/citations.md`

## Completion Report

> Fill this section before changing the status to `DONE`.

### Files Changed

- `services/orchestrator/src/zayd_service_orchestrator/citation_registry.py`
- `services/orchestrator/src/zayd_service_orchestrator/__init__.py`
- `services/orchestrator/tests/test_citation_detail.py` (new)
- `services/api/src/zayd_service_api/app.py`
- `services/api/tests/test_citations_api.py` (new)
- `packages/citations/package.json`
- `packages/citations/tsconfig.json`
- `packages/citations/src/types.ts` (new)
- `packages/citations/src/labels.ts` (new)
- `packages/citations/src/api.ts` (new)
- `packages/citations/src/safe-text.tsx` (new)
- `packages/citations/src/source-warning.tsx` (new)
- `packages/citations/src/citation-card.tsx` (new)
- `packages/citations/src/citation-detail.tsx` (new)
- `packages/citations/src/index.tsx` (new)
- `packages/citations/src/citations.test.ts` (new)
- `apps/web/package.json`
- `apps/web/app/chat/chat-interface.tsx`
- `apps/web/app/citations/[citationId]/page.tsx` (new)
- `apps/web/app/citations/citations.test.ts` (new)
- `apps/web/app/globals.css`
- `docs/frontend/citations.md` (new)
- `tasks/09_user_web/09-03_citation_cards_and_source_detail.md`
- `tasks/09_user_web/09-06_saved_answers.md`
- `tasks/00_task_index.md`
- `tasks-update.md`

### Commands and Tests Executed

- `uv run pytest services/orchestrator/tests/test_citation_detail.py services/api/tests/test_citations_api.py -q` — 8 passed
- `corepack pnpm --filter @zayd/citations test` — 9 passed
- `corepack pnpm --filter @zayd/web test` — 19 passed
- `corepack pnpm --filter @zayd/citations typecheck` — success
- `corepack pnpm --filter @zayd/web build` — success

### Acceptance Criteria Result

- Passed. Chat answers keep AI explanation in the message body while `CitationCardList` renders governed source references separately with an explicit notice. `CitationDetailView` shows original Arabic (`dir=rtl`) and Thai translation in dedicated blocks. Warning banners surface `citation_invalidated`, `source_suspended`, and `document_version_unavailable`.

### Security and License Review

- No secrets, production data, or restricted religious content added. Public APIs expose only governed registry metadata and reviewed chunk text. UI uses text nodes/`ArabicText` only; no `dangerouslySetInnerHTML`.

### Known Limitations

- Streaming chat still emits placeholder short `citation_id` values until orchestrator maps answers to registry tokens; cards show detail links only for UUID/`CIT-{uuid}` references.
- Source detail page does not yet include full document browser or license viewer.

### Follow-up Tasks

- TASK-09-06 — saved answers can reuse citation cards
- Orchestrator follow-up — emit registry `CIT-{uuid}` tokens in streaming `final_answer`

### Commit

- `feat(web): add citation cards and source detail`
