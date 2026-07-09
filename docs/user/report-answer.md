# Report Answer

## Purpose

Signed-in users can report problems with completed answers. Reports link to the canonical `answers` row and optional citation references so reviewers can investigate without exposing internal traces to reporters.

## Access Model

- APIs require bearer authentication and `feedback.create`.
- Users can report only answers from conversations they own.
- Guests do not see report controls; sign in to submit feedback.

## Categories

| Value | Thai label |
|---|---|
| `incorrect_answer` | คำตอบไม่ถูกต้อง |
| `citation_error` | อ้างอิงผิดหรือไม่ตรง |
| `incomplete_answer` | คำตอบไม่ครบถ้วน |
| `inappropriate_content` | เนื้อหาไม่เหมาะสม |
| `other` | อื่นๆ |

## Web UI

- Chat completed answers — **รายงานปัญหา** opens an accessible form with category select and optional notes (max 2000 characters).
- After submission, the UI shows the API receipt message and hides the form.
- Rate-limited submissions return a stable error without internal diagnostics.

## Privacy and Audit

- Feedback rows store category, optional user notes, and answer/citation references.
- Audit logs record `feedback.submit` with version metadata (`retrieval_run_id`, model, prompt, policy) and `notes_length` only — not note text.
- Public API responses omit internal traces, retrieval payloads, and reviewer notes.