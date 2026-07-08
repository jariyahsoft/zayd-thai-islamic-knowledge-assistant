DROP TABLE IF EXISTS review_comments;
DROP TABLE IF EXISTS review_decisions;
DROP TABLE IF EXISTS review_revisions;
ALTER TABLE review_tasks DROP COLUMN IF EXISTS row_version;
