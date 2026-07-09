ALTER TABLE auth_users DROP CONSTRAINT IF EXISTS chk_auth_users_history_mode;
ALTER TABLE auth_users DROP CONSTRAINT IF EXISTS chk_auth_users_answer_length;
ALTER TABLE auth_users DROP COLUMN IF EXISTS history_mode;
ALTER TABLE auth_users DROP COLUMN IF EXISTS show_arabic;
ALTER TABLE auth_users DROP COLUMN IF EXISTS answer_length;