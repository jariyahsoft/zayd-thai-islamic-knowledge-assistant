# Chat Interface

Implementation notes for TASK-09-02 in `apps/web`.

## Architecture

| Area | Location |
|---|---|
| Chat page | `apps/web/app/chat/page.tsx` |
| Client UI | `apps/web/app/chat/chat-interface.tsx` |
| SSE client | `apps/web/app/chat/chat-stream.ts` |
| Types and helpers | `apps/web/app/chat/chat-types.ts`, `chat-ui.ts` |
| Styles | `apps/web/app/globals.css` (`.zayd-chat*` classes) |

## API Integration

The chat UI connects to the governed streaming API documented in `docs/api/streaming-chat.md`.

| Action | Endpoint | Notes |
|---|---|---|
| Start guest session | `POST /auth/guest/start` | Token stored in `localStorage` |
| Stream answer | `POST /chat/stream` | `text/event-stream` via `fetch` + `ReadableStream` |
| Stop generation | Abort `fetch` | Disconnect cancels guest streams |
| Authenticated cancel | `DELETE /chat/streams/{stream_id}` | Requires bearer token |

Request body fields used by the UI:

- `question`
- `conversation_id` (thread continuity)
- `guest_token` (guest mode)

## Event Handling

| SSE event | UI behavior |
|---|---|
| `status` | Updates Thai progress label (`accepted` → `verifying`) |
| `final_answer` | Renders verified answer text, citations, limitations, warning |
| `error` | Shows stable error code message and enables retry |
| `complete` | Maps `completed`, `abstained`, `cancelled`, or `failed` end states |

Abstained answers may not include `final_answer`; the UI shows a governed abstention message when `complete.status=abstained`.

## Security and Safe Rendering

- No `dangerouslySetInnerHTML`; all answer text is rendered as React text nodes.
- Arabic citations use `ArabicText` with `dir="rtl"` and `unicode-bidi: isolate`.
- Hidden chain-of-thought, prompts, and internal traces are never requested or displayed.
- Guest tokens are stored locally only; no server secrets appear in the browser bundle.

## Accessibility

- Landmark section with `aria-labelledby` heading.
- Message log uses `role="log"` and `aria-live="polite"`.
- Composer textarea has an associated `<label>`.
- Progress and streaming states announce via `aria-live`.
- Primary actions are keyboard reachable; Enter submits, Shift+Enter inserts a newline.

## Tests

- `apps/web/app/chat/chat.test.ts` — SSE parsing, mocked streaming success/failure/cancel paths, XSS contract checks.

## Follow-up Tasks

- TASK-09-04 — user preference controls (madhhab, answer length) in `/settings`.
- TASK-09-05 — conversation history list in `/history`.