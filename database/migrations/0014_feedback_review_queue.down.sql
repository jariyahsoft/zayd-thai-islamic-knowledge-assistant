-- Migration 0014 rollback: Feedback Review Queue
DROP INDEX IF EXISTS idx_feedback_reviewer;
DROP INDEX IF EXISTS idx_feedback_review_queue;

ALTER TABLE feedback
    DROP COLUMN IF EXISTS resolved_at,
    DROP COLUMN IF EXISTS severity,
    DROP COLUMN IF EXISTS priority,
    DROP COLUMN IF EXISTS resolution,
    DROP COLUMN IF EXISTS root_cause,
    DROP COLUMN IF EXISTS reviewer_notes,
    DROP COLUMN IF EXISTS reviewer_id;
