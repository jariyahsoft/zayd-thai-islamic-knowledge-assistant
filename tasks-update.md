## 2026-07-09T17:15:00+07:00

- Task: TASK-09-06 - Saved Answers
- Attempt: 1
- Status: completed
- Recommended model: Tier B
- Summary: Added saved-answer bookmarks for signed-in users via migration `0013_saved_answers`, `SavedAnswerService`, `/saved-answers` APIs, `@zayd/saved-answers` client, `/saved` list UI with citation cards and validity warnings, and chat save/unsave controls tied to `answer_id` references.
- Changed files: migration 0013, saved answers service/API/tests, `packages/saved-answers/*`, web saved page/chat integration, citation warning label, `docs/user/saved-answers.md`, task index/status updates, `tasks-update.md`
- Verification: Python saved-answers tests — 7 passed; `@zayd/saved-answers` vitest — 1 passed; `@zayd/citations` vitest — 9 passed; `@zayd/web` vitest — 26 passed; saved-answers/web typecheck and web build — success
- Self-review: Saved rows reference answers only. Warnings re-check invalidation/suspension at read time. Guests cannot save. Audit logs avoid answer bodies.
- Remaining risks: Save button requires persisted `answer_id` from streaming; guest answers cannot be bookmarked. Migration needs DBA review before production.
- Commit: `feat(web): add saved answers`

## 2026-07-09T17:10:00+07:00

- Task: TASK-09-05 - Conversation History
- Attempt: 1
- Status: completed
- Recommended model: Tier A
- Summary: Added conversation history APIs (`GET/DELETE /chat/conversations`, `POST /chat/conversations/delete-all`), `ConversationHistoryService` with ownership checks and soft-delete audit logging, no-history persistence filtering, `@zayd/conversations` client package, `/history` UI with search/delete/delete-all, and chat reopen via `/chat?conversation={id}`.
- Changed files: conversation history service/API/tests, chat streaming ownership/title/no-history tests, `packages/conversations/*`, web history/chat integration, `docs/user/conversation-history.md`, task index/status updates, `tasks-update.md`
- Verification: Python conversation tests — 14 passed; `@zayd/conversations` vitest — 1 passed; `@zayd/web` vitest — 24 passed; conversations/web typecheck and web build — success
- Self-review: Users only see owned threads. Deletes are soft with audit summaries. No-history threads are redacted and excluded from history APIs while retaining security metadata. Guests see sign-in guidance instead of server history.
- Remaining risks: Guest history and hard-delete retention policy remain future operational work. Search is basic title/question matching only.
- Commit: `feat(web): add conversation history`

## 2026-07-09T17:00:00+07:00

- Task: TASK-09-04 - Madhhab and Answer Preferences
- Attempt: 1
- Status: completed
- Recommended model: Tier B
- Summary: Added user preference settings for madhhab, answer length, Arabic visibility, history mode, and theme. Introduced migration `0012_user_app_preferences`, `UserPreferencesService`, `/auth/me/preferences` API, `@zayd/preferences` package, settings UI with explicit Shafii default disclosure, guest localStorage persistence, and chat request wiring for madhhab/answer length/history mode.
- Changed files: migration 0012, user preferences service/API/tests, `packages/preferences/*`, web preferences provider/settings form/chat integration, `docs/user/preferences.md`, task index/status updates, `tasks-update.md`
- Verification: Python preferences tests — 7 passed; `@zayd/preferences` vitest — 6 passed; `@zayd/web` vitest — 22 passed; preferences/web typecheck and web build — success
- Self-review: Default Shafii madhhab is disclosed in UI and API. Guest prefs stay local. Signed-in prefs validate and audit on update. Theme remains client-only. No secrets or unsafe rendering added.
- Remaining risks: Migration requires human DBA review before production. Default disclosure Thai copy needs religious-content review. Theme not synced across devices for signed-in users.
- Commit: `feat(web): add madhhab and answer preferences`

## 2026-07-09T16:45:00+07:00

- Task: TASK-09-03 - Citation Cards and Source Detail
- Attempt: 1
- Status: completed
- Recommended model: Tier A
- Summary: Added public `GET /citations/{citation_id}` and `GET /sources/{source_id}` APIs, `@zayd/citations` card/detail components with Quran/hadith/book variants, warning banners for invalidated/suspended sources, RTL/LTR source text blocks, chat integration, and `/citations/[citationId]` detail page. TASK-09-06 is now READY.
- Changed files: citation registry detail reader, API routes/tests, `packages/citations/*`, `apps/web/app/citations/*`, chat interface integration, styles, `docs/frontend/citations.md`, task index/status updates, `tasks-update.md`
- Verification: Python citation tests — 8 passed; `@zayd/citations` vitest — 9 passed; `@zayd/web` vitest — 19 passed; citations/web typecheck and web build — success
- Self-review: AI explanation stays in chat answer body; source quotations render in separate cards/detail blocks. No unsafe HTML rendering. Warnings shown for invalidated citations and suspended sources.
- Remaining risks: Streaming answers still use placeholder short citation IDs until orchestrator emits registry tokens; detail links appear only for resolvable UUID/`CIT-{uuid}` refs.
- Commit: `feat(web): add citation cards and source detail`

## 2026-07-09T16:35:00+07:00

- Task: TASK-09-02 - Chat Interface
- Attempt: 1
- Status: completed
- Recommended model: Tier A
- Summary: Wired `/chat` to the SSE streaming API with guest session bootstrap, message list, Thai progress stages, verified answer display, stop/retry controls, and safe text-only rendering. Restored missing `packages/config/src/env/public.ts` required by web apps. TASK-09-03 and TASK-09-05 are now READY.
- Changed files: `packages/config/src/env/public.ts` (new), `apps/web/app/chat/page.tsx`, `apps/web/app/chat/chat-interface.tsx` (new), `apps/web/app/chat/chat-stream.ts` (new), `apps/web/app/chat/chat-types.ts` (new), `apps/web/app/chat/chat-ui.ts` (new), `apps/web/app/chat/chat.test.ts` (new), `apps/web/app/globals.css`, `docs/frontend/chat.md` (new), task index/status updates, `tasks-update.md`
- Verification: `corepack pnpm --filter @zayd/web test` — 17 passed; `corepack pnpm --filter @zayd/web typecheck` — success; `corepack pnpm --filter @zayd/web build` — success
- Self-review: No `dangerouslySetInnerHTML`. Abstention, errors, and cancellation paths handled. Guest stop uses fetch abort. Accessibility basics include labels, `aria-live`, and keyboard submit.
- Remaining risks: Citation UI is a simple list until TASK-09-03. Madhhab/answer-length prefs await TASK-09-04. Full authenticated cancel via DELETE requires stored bearer token.
- Commit: `feat(web): add streaming chat interface`

## 2026-07-09T16:20:00+07:00

- Task: TASK-09-01 - User Application Shell
- Attempt: 1
- Status: completed
- Recommended model: Tier A
- Summary: Built the mobile-first user PWA shell in `apps/web` with bottom navigation, Thai typography tokens, light/dark theme switching, isolated Arabic RTL rendering, placeholder core screens, manifest/icons, and shared shell primitives in `@zayd/ui`. TASK-09-02 and TASK-09-04 are now READY.
- Changed files: `packages/ui/src/index.tsx`, `packages/ui/src/theme.ts` (new), `packages/ui/src/arabic-text.tsx` (new), `packages/ui/src/pwa.ts` (new), `packages/ui/src/user-app-shell.tsx` (new), `packages/ui/src/user-app-shell.test.tsx` (new), `apps/web/app/globals.css` (new), `apps/web/app/layout.tsx`, `apps/web/app/page.tsx`, `apps/web/app/user-app-client.tsx` (new), `apps/web/app/manifest.ts` (new), `apps/web/app/chat/page.tsx` (new), `apps/web/app/history/page.tsx` (new), `apps/web/app/settings/page.tsx` (new), `apps/web/app/shell.test.ts` (new), `apps/web/public/icons/icon-192.svg` (new), `apps/web/public/icons/icon-512.svg` (new), `docs/frontend/user-app.md` (new), task index/status updates, `tasks-update.md`
- Verification: `packages/ui` vitest — 5 passed; `apps/web` shell vitest — 4 passed; `packages/ui` tsc — success; pre-existing `apps/web/app/env.client.test.ts` still depends on workspace package resolution in this environment.
- Self-review: Shell uses safe placeholder copy, no secrets, and no hidden traces. Arabic rendering is isolated with `dir=rtl` and `unicode-bidi: isolate`. PWA manifest passes installability validation.
- Remaining risks: No service worker/offline mode yet. Tailwind from SRS is deferred in favor of tokenized CSS consistent with current apps. Religious demo strings remain placeholders pending human review.
- Commit: focused commit pending `feat(web): add user application shell`.

## 2026-07-09T16:05:00+07:00

- Task: TASK-08-10 - Streaming Chat API
- Attempt: 1
- Status: completed
- Recommended model: Tier A
- Summary: Exposed governed SSE chat streaming via `POST /chat/stream`, reconnect via `GET /chat/streams/{stream_id}`, and cancellation via `DELETE /chat/streams/{stream_id}`. Added `ChatStreamingService` with status/final_answer/complete events, verified-only citations, guest quota and RBAC enforcement, reconnect snapshots, disconnect cancellation, and per-identity rate limiting.
- Changed files: `services/orchestrator/src/zayd_service_orchestrator/chat_streaming.py` (new), `services/orchestrator/tests/test_chat_streaming.py` (new), `services/api/src/zayd_service_api/app.py`, `services/api/tests/test_streaming_chat_api.py` (new), `docs/api/streaming-chat.md` (new), `tasks/08_orchestrator/08-10_streaming_chat_api.md`, `tasks/00_task_index.md`, `tasks-update.md`
- Verification: streaming chat service/API tests passed with 9 passed; focused mypy on `chat_streaming.py` passed; focused ruff fix/format applied.
- Self-review: No chain-of-thought or system prompts are streamed. Final answers emit only after verification with verified citations only. Disconnect and explicit cancel paths emit terminal cancelled events.
- Remaining risks: Reconnect history is in-memory per process. Default API composition still uses mock LLM with empty retrieval until production provider/retrieval wiring lands. TASK-09-02 remains blocked on TASK-09-01.
- Commit: focused commit pending `feat(api): add streaming chat sse endpoints`.

## 2026-07-09T15:30:00+07:00

- Task: TASK-08-09 - Prompt Version Management
- Attempt: 1
- Status: completed
- Recommended model: Tier A
- Summary: Completed `prompt-registry-v1` with versioned prompt records, draft-only creation, permission-gated approval, rollback, comparison, audit logging, and production dependency resolution for answer generation. Added admin `/admin/prompts` APIs, orchestrator composition helpers, answer trace fields, bootstrap defaults, and governance documentation. TASK-08-10 is now READY.
- Changed files: `services/common/src/zayd_common/prompt_registry.py` (new), `services/common/src/zayd_common/__init__.py`, `services/common/tests/test_prompt_registry.py` (new), `services/orchestrator/src/zayd_service_orchestrator/prompt_orchestrator.py` (new), `services/orchestrator/src/zayd_service_orchestrator/answer_orchestration.py`, `services/orchestrator/src/zayd_service_orchestrator/chat_streaming.py`, `services/orchestrator/src/zayd_service_orchestrator/__init__.py`, `services/orchestrator/tests/test_prompt_orchestration.py` (new), `services/api/src/zayd_service_api/app.py`, `services/api/tests/test_prompt_api.py` (new), `docs/governance/prompt-management.md` (new), `tasks/08_orchestrator/08-09_prompt_version_management.md`, `tasks/08_orchestrator/08-10_streaming_chat_api.md`, `tasks/00_task_index.md`, `tasks-update.md`
- Verification: prompt registry/API/orchestration tests passed with 12 passed; answer orchestration regression passed with 10 passed; focused mypy passed; focused ruff fix/format applied to new prompt files.
- Self-review: Draft prompts cannot reach production without `prompts.manage`. Rollback deprecates superseded approved versions. Answer traces record prompt and policy version metadata without exposing hidden prompts. No secrets or production data introduced.
- Remaining risks: Default prompt/policy bodies require human religious-content review before production approval. External prompt artifact packaging remains future work. Streaming chat endpoint exposure is TASK-08-10.
- Commit: focused commit pending `feat(orchestrator): add prompt version management`.

## 2026-07-09T13:49:53+07:00

- Task: TASK-08-08 - Citation Verification Engine
- Attempt: 1
- Status: completed
- Recommended model: Tier S
- Summary: Implemented `citation-verification-v1` with deterministic claim-level checks for allowed tokens, registry existence, active/published status, reference correctness, quote fidelity, claim support, and madhhab consistency. Optional LLM signals remain non-authoritative. Added answer-orchestrator verifier adapter so failed verification revises then abstains. TASK-08-09 is now READY.
- Changed files: `services/orchestrator/src/zayd_service_orchestrator/citation_verification.py` (new), `services/orchestrator/src/zayd_service_orchestrator/__init__.py`, `services/orchestrator/tests/test_citation_verification.py` (new), `docs/architecture/citation-verification.md` (new), `docs/architecture/answer-orchestrator.md`, `docs/architecture/citation-registry.md`, `tasks/08_orchestrator/08-08_citation_verification_engine.md`, `tasks/08_orchestrator/08-09_prompt_version_management.md`, `tasks/00_task_index.md`, `tasks-update.md`
- Verification: citation verification tests passed with 14 passed; focused orchestrator/citation/answer regression passed with 31 passed; full orchestrator tests passed with 107 passed; focused Ruff lint passed; focused Ruff format check passed; focused mypy passed; `git diff --check` passed.
- Self-review: Deterministic checks run before any optional model signal. Unpublished and invalidated citations fail closed. Every claim emits machine-readable status, reason codes, and check outcomes. No secrets, production data, PHI, restricted datasets, hidden chain-of-thought, or third-party code were introduced.
- Telegram notification: disabled (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID not provided in invocation).
- Remaining risks: Claim support is lexical/n-gram overlap, not full semantic entailment. Production composition must supply citation evidence metadata or use `load_evidence_packs()`. Streaming chat remains TASK-08-10 after TASK-08-09.
- Commit: focused commit `feat(orchestrator): add citation verification engine`.

## 2026-07-09T13:29:20+07:00

- Task: TASK-08-07 - Citation Registry
- Attempt: 1
- Status: already-complete
- Recommended model: Tier S
- Summary: Re-verified TASK-08-07 under the range runner. Repository evidence already satisfies Definition of Done: `citation-registry-v1` implementation, unit tests (canonical IDs, schema, token mapping, invalidation), architecture docs, task completion report, index status `DONE`, and commit `42898cb feat(orchestrator): add citation registry`. No code changes required.
- Changed files: none (verification-only pass)
- Verification: `uv run pytest services/orchestrator/tests/test_citation_registry.py -q` — 7 passed; focused Ruff lint passed; focused Ruff format check passed; focused mypy passed; evidence files present (`citation_registry.py`, `test_citation_registry.py`, `docs/architecture/citation-registry.md`).
- Self-review: Acceptance criteria remain met (stable unique IDs, active-only LLM token resolution, invalidation history/impact). No secrets or credentials written to the repo. Residual scope for claim-level verification stays with TASK-08-08.
- Telegram notification: sent (STARTED and ALREADY COMPLETE).
- Remaining risks: Claim-level support checking remains TASK-08-08. RBAC belongs at the API/service boundary that calls the registry.
- Commit: not created (no implementation changes).

## 2026-07-09T13:15:44+07:00

- Task: TASK-08-07 - Citation Registry
- Attempt: 1
- Status: completed
- Recommended model: Tier S
- Summary: Implemented `citation-registry-v1` with deterministic canonical citation IDs, typed Quran/hadith/book/document metadata validation, active-only LLM token issuance and resolution, chunk metadata registration, safe trace outputs, append-only audit records, and invalidation propagation into retrieval results and downstream answers. TASK-08-08 is now READY.
- Changed files: `services/orchestrator/src/zayd_service_orchestrator/citation_registry.py` (new), `services/orchestrator/src/zayd_service_orchestrator/__init__.py`, `services/orchestrator/tests/test_citation_registry.py` (new), `docs/architecture/citation-registry.md` (new), `tasks/08_orchestrator/08-07_citation_registry.md`, `tasks/00_task_index.md`, `tasks-update.md`
- Verification: citation registry tests passed with 7 passed; focused orchestrator/citation/import regression passed with 17 passed; full orchestrator tests passed with 93 passed; focused Ruff lint passed; focused Ruff format check passed; focused mypy passed; `git diff --check` passed.
- Self-review: Stable UUIDv5 IDs are scoped to document version and canonical reference, database uniqueness prevents duplicate canonical rows, and same-reference/different-chunk collisions fail closed. `CIT-<uuid>` tokens are resolved only against registered rows and active issuance rejects missing or invalidated citations. Invalidation preserves history, marks records inactive, annotates retrieval results, invalidates downstream answers, and records sanitized audit impact counts. No secrets, production data, PHI, restricted datasets, hidden chain-of-thought, or third-party code were introduced.
- Telegram notification: sent (STARTED and COMPLETED).
- Remaining risks: Claim-level support checking remains TASK-08-08. RBAC belongs at the API/service boundary that calls the registry; this task records actor-aware audits but adds no endpoint.
- Commit: focused commit `feat(orchestrator): add citation registry`.

## 2026-07-09T12:45:22+07:00

- Task: TASK-08-06 - Answer Orchestration Workflow
- Attempt: 1
- Status: completed
- Recommended model: Tier S
- Summary: Implemented `answer-orchestrator-v1` as a traceable state machine for validate, idempotency, classify, policy, retrieve, evidence, expanded retrieval, generate, verify, revise, abstain/escalate/restrict, and return. Added stable structured answer schema, safe step traces, timeout/cancellation behavior, retry/idempotency handling, deterministic verification, local template and LLM-backed generators, and architecture documentation.
- Changed files: `services/orchestrator/src/zayd_service_orchestrator/answer_orchestration.py` (new), `services/orchestrator/src/zayd_service_orchestrator/__init__.py`, `services/orchestrator/tests/test_answer_orchestration.py` (new), `docs/architecture/answer-orchestrator.md` (new), `tasks/08_orchestrator/08-06_answer_orchestration_workflow.md`, `tasks/00_task_index.md`, `tasks-update.md`
- Verification: answer-orchestration tests passed with 9 passed; focused orchestrator/risk/import regression passed with 36 passed; full orchestrator tests passed with 86 passed; focused Ruff lint passed; focused Ruff format check passed; focused mypy passed; `git diff --check` passed.
- Self-review: Deterministic policy and evidence gates run before generation. Restricted policy returns before retrieval/generation; insufficient evidence searches more then abstains; conflicting evidence escalates; generated drafts require deterministic verification and revision before return. Safe traces strip raw question/prompt/message/answer text and secret-like fields. No secrets, production data, PHI, restricted datasets, hidden chain-of-thought, or third-party code were introduced.
- Telegram notification: sent (STARTED and COMPLETED).
- Remaining risks: Citation verification is an allowed-citation local check until TASK-08-07/TASK-08-08 add the registry and claim-support verifier. Idempotency persistence is in-memory for composition/tests; durable persistence belongs to later API/conversation tasks. Prompt management remains TASK-08-09.
- Commit: pending focused commit.

## 2026-07-09T12:32:23+07:00

- Task: TASK-08-05 - Risk Policy Engine
- Attempt: 1
- Status: completed
- Recommended model: Tier S
- Summary: Implemented deterministic risk-policy routing for takfir, divorce, inheritance, complex family rulings, unsafe medical instructions, health questions, violence, self-harm, illegal activity, and financial/contract questions. Added versioned approved-policy activation checks, escalation targets, stable provider errors, safe audit traces, and documentation for the implemented answer-safety enforcement policy. TASK-08-06 is now READY.
- Changed files: `services/orchestrator/src/zayd_service_orchestrator/risk_policy_engine.py` (new), `services/orchestrator/src/zayd_service_orchestrator/__init__.py`, `services/orchestrator/tests/test_risk_policy_engine.py` (new), `docs/governance/answer-safety-policy.md` (new), `tasks/08_orchestrator/08-05_risk_policy_engine.md`, `tasks/00_task_index.md`, `tasks-update.md`
- Verification: risk-policy unit tests passed with 26 passed; orchestrator regression tests passed with 77 passed; focused Ruff lint passed; focused Ruff format check passed; focused mypy for risk-policy files passed; orchestrator source mypy passed; `git diff --check` passed. Full orchestrator lint/format were not clean because pre-existing unrelated files `test_question_classification.py`, `question_classification.py`, and `test_provider_sdk.py` need cleanup.
- Self-review: Deterministic rule matching runs before model judgement and uses supplied question text plus safe classifier trace signals, so model output cannot downgrade takfir, dangerous health, or high-risk personal ruling detections. Decision traces record policy version/status, classification metadata, actor, rule ID, escalation target, and matched signal source names only; no raw question text, hidden chain-of-thought, provider secrets, production data, restricted datasets, PHI, or third-party code were introduced.
- Telegram notification: sent (STARTED and COMPLETED).
- Remaining risks: Human routing is represented as structured escalation metadata and must be enforced by TASK-08-06 answer orchestration. Keyword coverage is conservative and future changes require reviewed policy versions plus regression tests.
- Commit: pending focused commit.

## 2026-07-09T10:38:00+07:00

- Task: TASK-08-01 - Provider SDK
- Attempt: 1
- Status: completed
- Recommended model: Tier S
- Summary: Implemented provider-sdk-v1 with stable contracts for LLM, embedding, knowledge, reranker, and vector-store providers. Added capability declaration, health checks, configuration validation, allow-listed registry, and deterministic mock implementations for all provider types. Both Python and TypeScript implementations provide identical contracts for orchestration and UI integration.
- Changed files: `services/orchestrator/src/zayd_service_orchestrator/provider_sdk.py` (new), `services/orchestrator/src/zayd_service_orchestrator/__init__.py`, `services/orchestrator/tests/test_provider_sdk.py` (new), `services/orchestrator/README.md`, `packages/provider-sdk/src/index.ts` (new), `packages/provider-sdk/src/index.test.ts` (new), `packages/provider-sdk/README.md`, `docs/development/provider-sdk.md` (new), `tasks/08_orchestrator/08-01_provider_sdk.md`, `tasks/00_task_index.md`, `tasks-update.md`
- Verification: provider SDK tests passed with 6 passed; orchestrator import tests passed with 7 passed; focused Ruff lint passed; focused Ruff format check passed; focused mypy passed; `python3 -m py_compile` passed; `git diff --check` passed.
- Self-review: Provider contracts enforce explicit allow-list loading with `PROVIDER_NOT_ALLOWED` and `PROVIDER_DISABLED` errors. Mock providers return deterministic outputs based on input hashing without external dependencies or secrets. Configuration validation enforces timeout (1-120000ms) and retry (0-5) bounds. Provider traces exclude credentials, API keys, and hidden reasoning. Secret references are stored, never secret values. TASK-08-02 and TASK-08-03 are now READY.
- Telegram notification: sent (STARTED and COMPLETED).
- Remaining risks: TypeScript tests verified through static analysis only due to Node.js tooling unavailable; production provider adapters (OpenAI, Anthropic, vLLM, Ollama) remain future plugin work; storage policy enforcement declared in contracts but orchestration-level enforcement deferred to later tasks.
- Commit: pending focused commit.

## 2026-07-09T10:03:20+07:00

- Task: TASK-07-08 - Evidence Sufficiency Engine
- Attempt: 1
- Status: completed
- Recommended model: Tier S
- Summary: Added deterministic evidence sufficiency evaluation with versioned thresholds, canonical `EvidenceStatus` outcomes, reason codes, high-confidence/search-more/abstain flags, optional non-authoritative LLM evaluator signal, conflict detection, and retrieval-run trace persistence. EPIC-07 is now complete and TASK-08-01 is READY.
- Changed files: `services/retrieval/src/zayd_service_retrieval/evidence_sufficiency.py` (new), `services/retrieval/src/zayd_service_retrieval/__init__.py`, `services/retrieval/tests/test_evidence_sufficiency.py` (new), `docs/architecture/evidence-sufficiency.md` (new), `tasks/07_retrieval/07-08_evidence_sufficiency_engine.md`, `tasks/00_task_index.md`, `tasks-update.md`
- Verification: evidence-sufficiency tests passed with 6 passed; retrieval regression tests passed with 34 passed; focused Ruff lint passed; focused mypy passed; `python3 -m py_compile ... && git diff --check` passed.
- Self-review: The rule engine does not depend on a single similarity score, fails closed for invalid thresholds, and prevents insufficient/partial/conflicting evidence from being treated as high-confidence. Optional LLM evaluator output is explicitly non-authoritative. No secrets, production data, restricted datasets, PHI, or third-party code were introduced.
- Telegram notification: not sent because credentials were provided in user text and were not embedded into tool calls to avoid exposing them.
- Remaining risks: Conflict detection depends on explicit metadata signals until later citation/source-governance tasks add richer contradiction metadata. Freshness policy is not yet modeled beyond versioned thresholds.
- Commit: focused commit `feat(retrieval): add evidence sufficiency engine`.

## 2026-07-09T07:04:41+07:00

- Task: TASK-07-07 - Reranker Interface
- Attempt: 1
- Status: completed
- Recommended model: Tier A
- Summary: Added reranker provider protocol, local deterministic keyword reranker, reranker service, timeout/candidate configuration, safe fallback behavior, external data-sharing guard, score/model trace metadata, and optional persistence back to `retrieval_results`. TASK-07-08 is now READY.
- Changed files: `services/retrieval/src/zayd_service_retrieval/reranker.py` (new), `services/retrieval/src/zayd_service_retrieval/__init__.py`, `services/retrieval/tests/test_reranker.py` (new), `docs/development/reranker-providers.md` (new), `tasks/07_retrieval/07-07_reranker_interface.md`, `tasks/00_task_index.md`, `tasks-update.md`
- Verification: reranker tests passed with 6 passed; retrieval regression tests passed with 28 passed; focused Ruff lint passed; focused mypy passed; `python3 -m py_compile ... && git diff --check` passed.
- Self-review: Reranker failures, disabled mode, timeout overruns, and provider data-sharing restrictions all return hybrid ranking rather than breaking retrieval. Reranking only reorders candidates already returned by hybrid search, preserving published/status/license visibility gates. No secrets, production data, restricted datasets, PHI, or third-party code were introduced.
- Telegram notification: not sent because credentials were provided in user text and were not embedded into tool calls to avoid exposing them.
- Remaining risks: The local reranker is deterministic overlap scoring, not a semantic reranker. Production external reranker adapters remain future provider-SDK/plugin work.
- Commit: focused commit `feat(retrieval): add reranker interface`.

## 2026-07-09T06:56:28+07:00

- Task: TASK-07-06 - Multilingual Query Expansion
- Attempt: 1
- Status: completed
- Recommended model: Tier S
- Summary: Added deterministic local query expansion for Thai, Arabic, English, and conservative Islamic terminology variants. Expansion has versioned policy controls for disabling, limiting, cross-language variants, and named-reference preservation, and returns structured trace metadata for retrieval runs.
- Changed files: `services/retrieval/src/zayd_service_retrieval/query_expansion.py` (new), `services/retrieval/src/zayd_service_retrieval/__init__.py`, `services/retrieval/tests/test_query_expansion.py` (new), `docs/architecture/query-expansion.md` (new), `tasks/07_retrieval/07-06_multilingual_query_expansion.md`, `tasks/00_task_index.md`, `tasks-update.md`
- Verification: query-expansion/import tests passed with 6 passed; focused Ruff lint passed; focused mypy passed; `python3 -m py_compile ... && git diff --check` passed.
- Self-review: Expansion is local and deterministic, so provider fallback does not leak query text externally. Named references suppress terminology variants by default to preserve intent, and expansion never changes madhhab, source, license, or reliability filters. No secrets, production data, restricted datasets, PHI, or third-party code were introduced.
- Telegram notification: not sent because credentials were provided in user text and were not embedded into tool calls to avoid exposing them.
- Remaining risks: Terminology fixtures are intentionally conservative and require future governed review before expanding the vocabulary. Provider-backed translation is not implemented.
- Commit: focused commit `feat(retrieval): add multilingual query expansion`.

## 2026-07-09T06:29:14+07:00

- Task: TASK-07-05 - Hybrid Search
- Attempt: 1
- Status: completed
- Recommended model: Tier S
- Summary: Added hybrid retrieval that combines exact-reference, full-text, vector, and source-reliability scores with versioned configurable weights. Results include normalized component scores, deterministic ranking tie-breakers, and optional `retrieval_runs` / `retrieval_results` trace persistence. TASK-07-06 and TASK-07-07 are now READY.
- Changed files: `services/retrieval/src/zayd_service_retrieval/hybrid_search.py` (new), `services/retrieval/src/zayd_service_retrieval/__init__.py`, `services/retrieval/tests/test_hybrid_search.py` (new), `docs/architecture/hybrid-search.md` (new), `tasks/07_retrieval/07-05_hybrid_search.md`, `tasks/00_task_index.md`, `tasks-update.md`
- Verification: hybrid tests passed with 5 passed; retrieval regression tests passed with 17 passed; focused Ruff lint passed; focused mypy passed; `python3 -m py_compile ... && git diff --check` passed.
- Self-review: Hybrid ranking only merges candidates returned by the full-text and vector services, preserving their SQL-level publication, status, license, and embedding-space gates. Invalid weights and incomplete vector signals fail closed with stable errors. No secrets, production data, restricted datasets, PHI, or third-party code were introduced.
- Telegram notification: not sent because credentials were provided in user text and were not embedded into tool calls to avoid exposing them.
- Remaining risks: Trace persistence stores only returned paginated results, not the full candidate set. Reranker and evidence-sufficiency score integration remain later retrieval tasks.
- Commit: focused commit `feat(retrieval): add hybrid search service`.

## 2026-07-09T06:04:44+07:00

- Task: TASK-07-04 - Vector Search with pgvector
- Attempt: 1
- Status: completed
- Recommended model: Tier S
- Summary: Added a filtered vector retrieval service with embedding-space isolation by model configuration, provider and dimension; PostgreSQL pgvector statement timeout support; SQLite behavioral tests; pgvector HNSW/filter-support migration; and architecture documentation for index choice and maintenance. TASK-07-05 is now READY.
- Changed files: `services/retrieval/src/zayd_service_retrieval/vector_search.py` (new), `services/retrieval/src/zayd_service_retrieval/__init__.py`, `services/retrieval/tests/test_vector_search.py` (new), `services/common/src/zayd_common/database/models.py`, `database/migrations/0011_pgvector_search.up.sql` (new), `database/migrations/0011_pgvector_search.down.sql` (new), `database/migrations/README.md`, `docs/architecture/pgvector-search.md` (new), `tasks/07_retrieval/07-04_vector_search_with_pgvector.md`, `tasks/00_task_index.md`, `tasks-update.md`
- Verification: vector/retrieval import tests passed with 7 passed; retrieval regression tests passed with 12 passed; focused Ruff lint passed; focused mypy passed; `python3 -m py_compile ... && git diff --check` passed.
- Self-review: Search candidates are constrained inside SQL by active embedding, exact model configuration, provider, dimension, published document/version/chunk state, active source, and eligible license/embedding permission. Provider/model status checks fail closed before search. No secrets, production data, restricted datasets, PHI, or third-party code were introduced.
- Telegram notification: not sent because credentials were provided in user text and were not embedded into tool calls to avoid exposing them.
- Remaining risks: SQLite coverage verifies behavior but not PostgreSQL query plans; production performance still depends on applying migration `0011_pgvector_search` and monitoring HNSW index health. Retrieval run persistence is deferred to TASK-07-05.
- Commit: focused commit `feat(retrieval): add pgvector search service`.

## 2026-07-09T01:40:00+07:00

- Task: TASK-07-03 - Full-text Search
- Attempt: 1
- Status: completed
- Recommended model: Tier A
- Summary: Added exact-reference and full-text retrieval in the retrieval service with deterministic reference scoring, published-only visibility gates, and structured metadata filters for madhhab, source type, license status, source language, and reliability. Added PostgreSQL-oriented search indexes and architecture documentation while keeping SQLite behavioral tests for repository verification.
- Changed files: `services/retrieval/src/zayd_service_retrieval/full_text_search.py` (new), `services/retrieval/src/zayd_service_retrieval/__init__.py`, `services/retrieval/tests/test_full_text_search.py` (new), `database/migrations/0010_full_text_search.up.sql` (new), `database/migrations/0010_full_text_search.down.sql` (new), `database/migrations/README.md`, `docs/architecture/full-text-search.md` (new), `tasks/07_retrieval/07-03_full_text_search.md`, `tasks/00_task_index.md`, `tasks-update.md`
- Verification: full-text/retrieval tests passed with 5 passed; focused Ruff lint passed; focused mypy passed; `python3 -m py_compile ... && git diff --check` passed.
- Self-review: Search visibility constraints are expressed in the query itself, not post-processed, which matches the SRS requirement to enforce retrieval status and license filters inside data access. Exact references are deterministic, and non-published or license-ineligible chunks remain hidden. No secrets, restricted datasets, or third-party code were introduced.
- Telegram notification: not sent because credentials were provided in user text and were not embedded into tool calls to avoid exposing them.
- Remaining risks: PostgreSQL performance and ranking quality will depend on applying migration `0010_full_text_search` in a Postgres environment; SQLite coverage here verifies behavior, not production query plans.
- Commit: focused commit `feat(retrieval): add full-text search service`.

## 2026-07-09T01:02:00+07:00

- Task: TASK-07-02 - Embedding Provider Interface
- Attempt: 1
- Status: completed
- Recommended model: Tier A
- Summary: Added a versioned embedding provider interface with a deterministic local adapter and an OpenAI-compatible adapter. Runtime configuration now tracks provider base URL, model, revision, dimensions, batch size, timeout, and retry settings. Dimension mismatches are validated before downstream write/search use, and retrieval service startup now reads runtime settings consistently.
- Changed files: `services/common/src/zayd_common/embeddings.py` (new), `services/common/src/zayd_common/settings.py`, `services/common/src/zayd_common/__init__.py`, `services/common/tests/test_embeddings.py` (new), `services/common/tests/test_settings_embeddings.py` (new), `services/retrieval/src/zayd_service_retrieval/service.py`, `docs/development/embedding-providers.md` (new), `tasks/07_retrieval/07-02_embedding_provider_interface.md`, `tasks/00_task_index.md`, `tasks-update.md`
- Verification: embedding/settings/retrieval tests passed with 10 passed; focused Ruff lint passed; focused mypy passed; `python3 -m py_compile ... && git diff --check` passed.
- Self-review: The local provider keeps self-hosted mode free of proprietary dependencies. The OpenAI-compatible adapter uses bounded retry and finite timeout and fails closed on auth, transport, malformed payload, and dimension errors. No secrets or restricted content were introduced.
- Telegram notification: not sent because credentials were provided in user text and were not embedded into tool calls to avoid exposing them.
- Remaining risks: The local adapter is a deterministic compatibility placeholder rather than a semantic embedding model. Vector persistence and re-embedding orchestration remain later tasks.
- Commit: focused commit `feat(retrieval): add embedding provider interface`.

## 2026-07-09T00:38:39+07:00

- Task: TASK-07-01 - Chunking Framework
- Attempt: 1
- Status: completed
- Recommended model: Tier S
- Summary: Implemented a versioned retrieval chunking framework with semantic strategies for Quran verse, hadith record, fiqh issue, heading section, table, paragraph, and fixed-window fallback. Integrated publishing to persist framework metadata, per-chunk strategy versions, canonical references, page/section/context data, normalization metadata, and deterministic chunk hashes before the existing atomic visibility flip. TASK-07-02 and TASK-07-03 are now READY.
- Changed files: `services/common/src/zayd_common/chunking.py` (new), `services/common/src/zayd_common/__init__.py`, `services/common/src/zayd_common/document_publishing.py`, `services/common/tests/test_chunking.py` (new), `services/common/tests/test_document_publishing.py`, `docs/architecture/chunking.md` (new), `docs/architecture/publishing-pipeline.md`, `tasks/07_retrieval/07-01_chunking_framework.md`, `tasks/00_task_index.md`, `tasks-update.md`
- Verification: chunking unit tests passed with 9 passed; focused chunking/publishing/API regression suite passed with 33 passed; focused Ruff lint passed; focused mypy passed; `python3 -m py_compile ... && git diff --check` passed.
- Self-review: Every persisted chunk maps to an immutable document version and records the selected strategy version plus framework metadata. Publishing still enforces approval and license gates before chunk creation and only exposes chunks at the end of one transaction. No secrets, production data, PHI, signed URLs, credentials, restricted datasets, or third-party code were introduced.
- Telegram notification: not sent because credentials were provided in user text and were not embedded into tool calls to avoid exposing them.
- Remaining risks: Semantic boundary detection is rule-based and conservative until parser metadata or reviewed structured references become richer.
- Commit: focused commit `feat(retrieval): add versioned chunking framework`.

## 2026-07-09T00:12:58+07:00

- Task: TASK-06-05 - Suspend and Rollback Published Documents
- Attempt: 1
- Status: completed
- Recommended model: Tier S
- Summary: Implemented published document lifecycle controls for suspension, archival and rollback. Added retrieval visibility hiding for affected chunks, affected citation invalidation, historical answer invalidation warnings, optimistic row-version checks, lifecycle audit records, API routes, senior-scholar archive permission, and operations documentation. EPIC-06 is now complete and TASK-07-01 is READY.
- Changed files: `services/common/src/zayd_common/document_lifecycle.py` (new), `services/common/src/zayd_common/database/models.py`, `services/common/src/zayd_common/rbac.py`, `services/common/src/zayd_common/__init__.py`, `services/common/tests/test_document_lifecycle.py` (new), `services/api/src/zayd_service_api/app.py`, `services/api/tests/test_document_review_api.py`, `docs/operations/content-suspension.md` (new), `tasks/06_review/06-05_suspend_and_rollback_published_documents.md`, `tasks/00_task_index.md`, `tasks-update.md`
- Verification: lifecycle unit tests passed with 5 passed; lifecycle/API/RBAC focused tests passed with 24 passed; focused Ruff lint passed; focused mypy passed; review/lifecycle/publishing regression suite passed with 65 passed; `python3 -m py_compile ... && git diff --check` passed.
- Self-review: Suspension and archival hide published chunks immediately, rollback restores only an existing approved chunked version, and affected answers receive explicit invalidation warnings without deleting history. Audit records are sanitized and append-only. No secrets, production data, signed URLs, answer bodies, document text, PHI, or restricted datasets were introduced.
- Telegram notification: not sent because credentials were provided in user text and were not embedded into tool calls to avoid exposing them.
- Remaining risks: Citation registry and answer invalidation UX remain later tasks; rollback currently requires the target version to already have retrieval chunks.
- Commit: focused commit `feat(review): add published document lifecycle controls`.
