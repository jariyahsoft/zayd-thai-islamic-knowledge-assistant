# Streaming Chat API

Server-Sent Events (SSE) endpoint for governed Thai Islamic knowledge answers.
Responses use `text/event-stream` and never expose hidden chain-of-thought or raw
system prompts.

## Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/chat/stream` | Start a streaming answer workflow |
| `GET` | `/chat/streams/{stream_id}` | Reconnect and replay events after `Last-Event-ID` |
| `DELETE` | `/chat/streams/{stream_id}` | Cancel an active stream |

## Authentication

Authenticated users must send `Authorization: Bearer <access_token>` and hold
`conversations.manage_own`.

Guest users may pass `guest_token` in the request body. Guest quota is consumed
before the stream starts.

## Request Body

```json
{
  "question": "ละหมาดคืออะไร",
  "conversation_id": null,
  "requested_madhhab": "shafii",
  "answer_length": "normal",
  "no_history": false,
  "guest_token": null
}
```

## SSE Event Schema

Every event uses schema version `chat-stream-v1` and includes `trace_id` and
`timestamp`.

| Event | Purpose |
|---|---|
| `status` | Workflow stage updates: `accepted`, `classifying`, `retrieving`, `verifying`, `completed`, `cancelled` |
| `final_answer` | Verified structured answer emitted only after orchestration verification succeeds |
| `error` | Stable machine-readable failure |
| `complete` | Stream terminal marker |

Example frame:

```text
id: 7f0c2f1a-4d2a-4f0b-9f0a-111111111111
event: status
data: {"schema_version":"chat-stream-v1","trace_id":"trace-1","timestamp":"2026-07-09T08:00:00+00:00","stage":"accepted","stream_id":"stream-..."}

```

`final_answer` citations include only entries with `verification_status=verified`.

## Reconnect Strategy

Clients may call `GET /chat/streams/{stream_id}` with `Last-Event-ID` to replay
missed events from the in-memory stream history. Completed streams remain
readable until process restart.

## Cancellation

- Client disconnect cancels in-flight processing for `POST /chat/stream`
- `DELETE /chat/streams/{stream_id}` cancels an active stream explicitly

Cancelled streams emit `status: cancelled` and `complete` with
`status=cancelled`.

## Rate Limits

- Authenticated users: `20` stream starts per `60` seconds per identity
- Guests: message quota enforced before stream start (`429 GUEST_QUOTA_EXCEEDED`)

## Error Codes

| Code | Meaning |
|---|---|
| `CHAT_AUTH_REQUIRED` | Missing bearer token and guest token |
| `CHAT_INPUT_INVALID` | Empty question |
| `CHAT_RATE_LIMITED` | Authenticated stream rate limit exceeded |
| `CHAT_STREAM_NOT_FOUND` | Unknown or inactive stream id |
| `GUEST_QUOTA_EXCEEDED` | Guest message quota exhausted |
| `RBAC_FORBIDDEN` | Missing `conversations.manage_own` |