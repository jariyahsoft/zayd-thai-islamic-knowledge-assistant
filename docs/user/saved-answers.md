# Saved Answers

## Purpose

Signed-in users can bookmark answers they want to revisit. Saved records reference the canonical `answers` row instead of copying source text into a separate store.

## Access Model

- APIs require bearer authentication and `conversations.manage_own`.
- Users can save only answers from conversations they own.
- Guests see guidance to sign in; chat hides save controls without a bearer token.

## API Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/saved-answers` | List saved answers for the current user |
| `POST` | `/saved-answers` | Save an answer by `answer_id` |
| `DELETE` | `/saved-answers/{saved_answer_id}` | Remove a saved bookmark |

`POST` body:

```json
{ "answer_id": "uuid" }
```

List/detail responses resolve answer text and citations from the linked `answers.answer_json` at read time.

## Validity Warnings

Saved answer views re-check source validity when loaded:

- `answer_invalidated` — answer row has `invalidated_at`
- `citation_invalidated` — linked citation is no longer active
- `source_suspended` — source is inactive

Warnings render through `SourceStatusWarnings` and do not hide the saved record.

## Web UI

- `/saved` — list saved answers with warnings and citation cards
- Chat completed answers — **บันทึกคำตอบ** / **ยกเลิกการบันทึก** controls for signed-in users with `answer_id`
- Home page links to `/saved`

## Privacy and Audit

- Saved rows store only `user_id` and `answer_id` references.
- Save/unsave mutations write audit logs (`saved_answers.save`, `saved_answers.unsave`) without message bodies.
- Removal is soft-delete via `saved_answers.deleted_at`.