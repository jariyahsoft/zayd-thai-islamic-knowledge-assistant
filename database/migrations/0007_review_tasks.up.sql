CREATE TABLE IF NOT EXISTS review_tasks (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_version_id uuid NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE,
    document_id uuid NOT NULL,
    assigned_to uuid REFERENCES auth_users(id) ON DELETE SET NULL,
    review_level text NOT NULL,
    status      text NOT NULL DEFAULT 'open',
    priority    text NOT NULL DEFAULT 'normal',
    category    text,
    language    text,
    madhhab     text,
    due_at      timestamptz,
    created_by  uuid NOT NULL REFERENCES auth_users(id) ON DELETE RESTRICT,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_review_tasks_open_level
    ON review_tasks (document_version_id, review_level)
    WHERE status IN ('open', 'in_progress');

CREATE INDEX IF NOT EXISTS idx_review_tasks_queue
    ON review_tasks (status, review_level, due_at);

COMMENT ON TABLE review_tasks IS 'One active review task per document version and review level';
COMMENT ON COLUMN review_tasks.review_level IS 'Level of review required (e.g. initial, scholar)';
COMMENT ON COLUMN review_tasks.status IS 'open | in_progress | completed | cancelled';
COMMENT ON COLUMN review_tasks.priority IS 'low | normal | high | urgent';
COMMENT ON COLUMN review_tasks.category IS 'Document category hint for reviewer matching';
COMMENT ON COLUMN review_tasks.language IS 'Document language for reviewer matching';
COMMENT ON COLUMN review_tasks.madhhab IS 'Madhhab for reviewer matching';
COMMENT ON COLUMN review_tasks.due_at IS 'Optional deadline for review completion';
