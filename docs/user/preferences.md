# User Preferences

## Purpose

The user settings screen lets people adjust how Zayd answers questions and how the app looks. Preferences affect chat requests, Arabic source visibility, conversation continuity, and theme.

## Available Settings

| Setting | Guest (local) | Signed-in (synced) | Default |
|---|---|---|---|
| Madhhab | Yes | Yes | Shafii |
| Answer length | Yes | Yes | Normal |
| Show Arabic in sources | Yes | Yes | On |
| History mode | Yes | Yes | Enabled |
| Theme | Yes | Local only | System |

## Default Madhhab Disclosure

Zayd defaults to the **Shafii** madhhab. The settings page shows this explicitly in Thai before the madhhab selector:

> ค่าเริ่มต้นของ Zayd คือมัซฮับชาฟิอี คุณสามารถเปลี่ยนได้ด้านล่าง

The API also returns `default_madhhab: "shafii"` alongside the user's current `madhhab` so clients can display the default without guessing.

## Guest vs Signed-in Behavior

### Guest

- All preferences are stored in browser `localStorage` under `zayd.preferences.guest`.
- Nothing is sent to the server until the user signs in.
- The settings form shows: *โหมดผู้เยี่ยมชม: การตั้งค่าถูกเก็บในเครื่องของคุณเท่านั้น*.

### Signed-in

- Madhhab, answer length, Arabic visibility, and history mode sync through:
  - `GET /auth/me/preferences`
  - `PATCH /auth/me/preferences`
- Theme remains client-only and is not persisted in the database.
- Updates are audited as `users.preferences.update`.
- The settings form shows sync status while loading or after a successful save.

## Chat Integration

When a user asks a question, the chat client sends:

- `requested_madhhab` from the madhhab preference
- `answer_length` from the answer-length preference
- `no_history: true` when history mode is `disabled`

Arabic text from citations can be hidden in the chat UI when `show_arabic` is off. This is a display preference only; underlying source data is unchanged.

## Validation

Invalid values are rejected:

- API request bodies use pattern validation on `PATCH /auth/me/preferences`.
- The `@zayd/preferences` package validates client-side before persisting.
- Server-side `UserPreferencesService` enforces the same allowed value sets.

Allowed values:

- Madhhab: `shafii`, `hanafi`, `maliki`, `hanbali`
- Answer length: `short`, `normal`, `detailed`
- History mode: `enabled`, `disabled`

## Database

Migration `0012_user_app_preferences` adds to `auth_users`:

- `answer_length` (default `normal`)
- `show_arabic` (default `true`)
- `history_mode` (default `enabled`)

`preferred_madhhab` already existed and continues to store the user's madhhab choice.

## Privacy Notes

- Guest preferences never leave the device.
- Signed-in preference updates require a valid bearer access token.
- Preference mutations do not store full chat content; audit logs record before/after summaries of preference fields only.