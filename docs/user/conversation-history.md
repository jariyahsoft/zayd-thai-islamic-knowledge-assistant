# Conversation History

## Purpose

Signed-in users can review past chat threads, search them, reopen a conversation in chat, delete individual threads, or delete all history. Guest users do not get server-side history.

## Access Model

- History APIs require bearer authentication and `conversations.manage_own`.
- Users can access only conversations where `conversations.user_id` matches their account.
- Cross-user access returns `CONVERSATION_NOT_FOUND` (404) without leaking ownership.
- Guest chat remains available through streaming APIs, but `/history` explains that server history requires sign-in.

## API Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/chat/conversations` | List/search paginated threads |
| `GET` | `/chat/conversations/{conversation_id}` | Open a thread with messages |
| `DELETE` | `/chat/conversations/{conversation_id}` | Soft-delete one thread |
| `POST` | `/chat/conversations/delete-all` | Soft-delete all owned threads |

List query parameters:

- `q` — search title or first user question (max 200 chars)
- `limit` — page size (default 50, max 100)
- `offset` — pagination offset

## Deletion and Retention

- Deletion is soft-delete via `conversations.deleted_at`.
- Deleted threads disappear from list/detail APIs but remain in the database for approved retention/audit policy.
- Delete mutations write audit logs:
  - `conversations.delete`
  - `conversations.delete_all`
- Audit summaries record IDs and counts only, not message bodies.

## No-History Mode

When a user disables history in settings:

- Chat sends `no_history: true` and does not continue an existing `conversation_id`.
- Streaming persistence stores `[no-history]` placeholders instead of readable question/answer text.
- Body hashes, trace metadata, retrieval runs, and answer lineage still persist for abuse/security review.
- No-history threads are excluded from `/chat/conversations` list and detail APIs.

## Web UI

- `/history` — search, delete, delete-all, and links to `/chat?conversation={id}`
- `/chat?conversation={id}` — reloads a saved thread for signed-in users with history mode enabled

## Privacy Notes

- History list/detail never returns redacted `[no-history]` threads.
- Message rendering in the web app uses text nodes only; no unsafe HTML rendering.
- Guests are told history stays local/off-server and can use settings to disable history before chatting.