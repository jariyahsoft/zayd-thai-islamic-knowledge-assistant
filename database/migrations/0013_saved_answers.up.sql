CREATE TABLE saved_answers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
  answer_id uuid NOT NULL REFERENCES answers(id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  deleted_at timestamptz
);

CREATE UNIQUE INDEX uq_saved_answers_user_answer_active
  ON saved_answers (user_id, answer_id)
  WHERE deleted_at IS NULL;

CREATE INDEX idx_saved_answers_user_updated
  ON saved_answers (user_id, updated_at)
  WHERE deleted_at IS NULL;

CREATE TRIGGER trg_saved_answers_updated_at
  BEFORE UPDATE ON saved_answers
  FOR EACH ROW EXECUTE FUNCTION zayd_set_updated_at();