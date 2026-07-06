# Authentication API

All responses use JSON. Error responses use:

```json
{"error":{"code":"AUTH_INVALID_CREDENTIALS","message":"Invalid email or password."}}
```

## Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/auth/register` | Create a user and return access/refresh tokens |
| `POST` | `/auth/login` | Authenticate and return access/refresh tokens |
| `POST` | `/auth/refresh` | Rotate a refresh token and return a new token pair |
| `POST` | `/auth/logout` | Revoke the refresh token's session |
| `POST` | `/auth/password-reset/request` | Create a reset token for an existing user without email enumeration |
| `POST` | `/auth/password-reset/confirm` | Set a new password and revoke active sessions |
| `POST` | `/auth/sessions/revoke-all` | Revoke all active sessions for the bearer-token user |

## Token Response

```json
{
  "access_token": "<signed access token>",
  "refresh_token": "<opaque refresh token>",
  "token_type": "bearer",
  "expires_in": 900
}
```

Refresh tokens are shown only in API responses and stored server-side as hashes.
