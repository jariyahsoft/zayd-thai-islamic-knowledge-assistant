CREATE TABLE IF NOT EXISTS review_approvals (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_version_id uuid NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE,
    review_task_id uuid NOT NULL REFERENCES review_tasks(id) ON DELETE CASCADE,
    approver_id uuid NOT NULL REFERENCES auth_users(id) ON DELETE RESTRICT,
    approval_level text NOT NULL,
    content_risk text NOT NULL,
    status text NOT NULL DEFAULT 'active',
    reason text NOT NULL,
    valid_until timestamptz,
    revoked_at timestamptz,
    revoked_by uuid REFERENCES auth_users(id) ON DELETE SET NULL,
    revoke_reason text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT ck_review_approvals_status CHECK (status IN ('active', 'expired', 'revoked')),
    CONSTRAINT ck_review_approvals_level CHECK (approval_level IN ('initial', 'scholar', 'board'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_review_approvals_active_level
    ON review_approvals (document_version_id, approval_level)
    WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_review_approvals_version_status
    ON review_approvals (document_version_id, status);

CREATE INDEX IF NOT EXISTS idx_review_approvals_approver
    ON review_approvals (approver_id);

COMMENT ON TABLE review_approvals IS 'Explicit senior-scholar and board approvals with expiry and revocation state';
COMMENT ON COLUMN review_approvals.valid_until IS 'Optional validity horizon for approval; expired approvals do not satisfy publishing requirements';
COMMENT ON COLUMN review_approvals.revoked_at IS 'Timestamp when approval was explicitly revoked';
