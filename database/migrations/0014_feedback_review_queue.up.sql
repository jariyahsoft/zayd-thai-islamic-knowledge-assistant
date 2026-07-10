-- Migration 0014: Feedback Review Queue
-- Adds reviewer-side fields to the feedback table to support prioritized,
-- assignable triage with reviewer notes, root-cause classification, and
-- resolution tracking.

ALTER TABLE feedback
    ADD COLUMN IF NOT EXISTS reviewer_id       uuid        REFERENCES auth_users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS reviewer_notes    text        NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS root_cause        text,
    ADD COLUMN IF NOT EXISTS resolution        text,
    ADD COLUMN IF NOT EXISTS priority          text        NOT NULL DEFAULT 'normal',
    ADD COLUMN IF NOT EXISTS severity          text        NOT NULL DEFAULT 'p3',
    ADD COLUMN IF NOT EXISTS resolved_at       timestamptz;

-- Index to support prioritized queue listing (open items not soft-deleted).
CREATE INDEX IF NOT EXISTS idx_feedback_review_queue
    ON feedback (status, priority, created_at)
    WHERE deleted_at IS NULL;

-- Index to support assignment lookups.
CREATE INDEX IF NOT EXISTS idx_feedback_reviewer
    ON feedback (reviewer_id)
    WHERE reviewer_id IS NOT NULL AND deleted_at IS NULL;

INSERT INTO auth_role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM auth_roles r
JOIN auth_permissions p ON p.resource = 'feedback' AND p.action = 'manage'
WHERE r.name = 'reviewer' AND r.deleted_at IS NULL
ON CONFLICT (role_id, permission_id) DO NOTHING;
