ALTER TABLE auth_users
  ADD COLUMN answer_length text NOT NULL DEFAULT 'normal',
  ADD COLUMN show_arabic boolean NOT NULL DEFAULT true,
  ADD COLUMN history_mode text NOT NULL DEFAULT 'enabled';

ALTER TABLE auth_users
  ADD CONSTRAINT chk_auth_users_answer_length
    CHECK (answer_length IN ('short', 'normal', 'detailed'));

ALTER TABLE auth_users
  ADD CONSTRAINT chk_auth_users_history_mode
    CHECK (history_mode IN ('enabled', 'disabled'));