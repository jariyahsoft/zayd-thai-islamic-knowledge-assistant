# Answer Invalidation

Authorized senior scholars and admins can invalidate an answer with a reason and idempotency key.
The original answer row and content remain available for audit, while `invalidated_at` and a
structured warning are written immediately so saved and historical views display the warning on
their next read. Every invalidation also creates an append-only history record.

Affected-answer discovery accepts exactly one citation or source ID. Results are ordered,
offset-pageable, capped at 200 answers per request, and audited with IDs and counts only. Callers
can safely retry discovery and invalidation; the idempotency key prevents duplicate history records
and notifications.

The notification integration is injectable. Production must configure an application-owned
`AnswerInvalidationNotifier`; the default records `not_configured`. Notifications contain only the
answer ID, warning, and invalidation timestamp—not answer text or conversation data.

Protected API routes:

- `POST /admin/answers/{answer_id}/invalidate`
- `GET /admin/answers/affected?citation_id=...`
- `GET /admin/answers/affected?source_id=...`
