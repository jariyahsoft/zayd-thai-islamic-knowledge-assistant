ALTER TABLE review_tasks
    ADD COLUMN IF NOT EXISTS row_version integer NOT NULL DEFAULT 1;

CREATE TABLE IF NOT EXISTS review_revisions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    review_task_id uuid NOT NULL REFERENCES review_tasks(id) ON DELETE CASCADE,
    document_version_id uuid NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE,
    actor_user_id uuid NOT NULL REFERENCES auth_users(id) ON DELETE RESTRICT,
    revision_number integer NOT NULL,
    base_task_row_version integer NOT NULL,
    text_before text,
    text_after text,
    metadata_before jsonb NOT NULL DEFAULT '{}'::jsonb,
    metadata_after jsonb NOT NULL DEFAULT '{}'::jsonb,
    diff_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_review_revisions_task_number UNIQUE (review_task_id, revision_number)
);

CREATE INDEX IF NOT EXISTS idx_review_revisions_task_created
    ON review_revisions (review_task_id, created_at);

CREATE TABLE IF NOT EXISTS review_decisions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    review_task_id uuid NOT NULL REFERENCES review_tasks(id) ON DELETE CASCADE,
    document_version_id uuid NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE,
    actor_user_id uuid NOT NULL REFERENCES auth_users(id) ON DELETE RESTRICT,
    decision text NOT NULL,
    reason text NOT NULL,
    base_task_row_version integer NOT NULL,
    resulting_task_status text NOT NULL,
    resulting_document_status text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_review_decisions_task_created
    ON review_decisions (review_task_id, created_at);

CREATE INDEX IF NOT EXISTS idx_review_decisions_actor
    ON review_decisions (actor_user_id);

CREATE TABLE IF NOT EXISTS review_comments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    review_task_id uuid NOT NULL REFERENCES review_tasks(id) ON DELETE CASCADE,
    author_id uuid NOT NULL REFERENCES auth_users(id) ON DELETE RESTRICT,
    body text NOT NULL,
    anchor_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    deleted_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_review_comments_task_created
    ON review_comments (review_task_id, created_at);

CREATE INDEX IF NOT EXISTS idx_review_comments_author
    ON review_comments (author_id);

COMMENT ON COLUMN review_tasks.row_version IS 'Optimistic concurrency version for review edit and decision operations';
COMMENT ON TABLE review_revisions IS 'Immutable document-review text and metadata revisions with human-readable diffs';
COMMENT ON TABLE review_decisions IS 'Immutable document-review decisions and resulting status transitions';
COMMENT ON TABLE review_comments IS 'Reviewer comments anchored to review task content or metadata';
