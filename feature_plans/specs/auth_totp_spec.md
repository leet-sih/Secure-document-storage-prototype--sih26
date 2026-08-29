# Auth TOTP (prototype MFA)

## What and why

Implement the second factor specified in `feature_plans/auth_plan.md` and `CLAUDE.md`: **TOTP** (authenticator app, 6-digit, `valid_window=1`). Password login cannot issue a full session when MFA is already enabled. First-time users get a short grace session only to change password and enroll TOTP.

**Out of this feature:** passkeys (WebAuthn), biometrics, Redis TOTP replay guard, refresh cookies. Those can be added later as additional factors without replacing TOTP.

## Exact files

Create: this spec; `backend/tests/test_totp.py`; `backend/migrations/alembic.ini`; `backend/migrations/env.py`; `backend/migrations/script.py.mako`; `backend/migrations/versions/001_departments_users_audit.py`.

Modify: `app/__init__.py`, `app/config.py`, `app/core/crypto.py` (secret wrap helpers only), `app/core/totp.py`, `app/core/security.py`, `app/core/errors.py`, `app/core/rbac.py`, `app/core/audit_events.py`, `app/schemas/auth_schemas.py`, `app/schemas/user_schemas.py`, `app/services/auth_service.py`, `app/blueprints/auth.py`, `app/blueprints/users.py` (`GET /me` only), `app/seed.py`.

Do not touch frontend, chunk store, cases, documents, or add WebAuthn.

## Data model

Existing `users.totp_secret` / `totp_secret_pending` (AES-GCM wrapped via `crypto.py`, key derived from `SECRET_KEY`). No new columns. Initial migration: `departments`, `users`, `audit_events` (auth records LOGIN / MFA events).

## API

| Method | Path | Auth | Body | Success |
|--------|------|------|------|---------|
| POST | `/api/v1/auth/login` | public, 5/min | `{email,password}` | `{mfa_required,temp_token}` or `{access_token,mfa_setup_required,expires_in}` |
| POST | `/api/v1/auth/mfa/verify` | public, 5/min | `{temp_token,totp_code}` | `{access_token,expires_in}` JWT includes `mfa_at` |
| GET | `/api/v1/auth/mfa/setup` | access JWT, not `purpose=mfa` | — | `{otpauth_uri,qr_code_base64}` pending secret stored |
| POST | `/api/v1/auth/mfa/confirm` | access JWT | `{totp_code}` | 204; pending → active |
| POST | `/api/v1/auth/mfa/step-up` | access JWT, 5/min | `{totp_code}` | `{access_token}` new `mfa_at` |
| POST | `/api/v1/auth/logout` | access JWT | — | 204; audit LOGOUT (stateless JWT; client discards) |
| GET | `/api/v1/users/me` | access JWT | — | user dump including `mfa_enabled`, `is_first_login` |

Temp JWT: 5 min, `purpose=mfa`. Must not work on `/users/me` or setup.

Errors: 401 `UNAUTHORIZED` (bad password/TOTP); 401 `MFA_REQUIRED` (stale `mfa_at`, do not clear session); 423 `LOCKED`; 403 inactive; 400 validation.

## Security

- TOTP never skipped when `totp_secret` is set.
- Secrets encrypted at rest; never logged.
- bcrypt cost ≥ 12; 72-byte password cap.
- Dummy bcrypt on unknown email (no user enumeration via timing).
- `@require_recent_mfa` reads `mfa_at`; 401 `MFA_REQUIRED` if older than `MFA_STEP_UP_MINUTES`.
- Passkeys later: new table + WebAuthn ceremony; login would choose TOTP *or* passkey. Biometrics on web = platform WebAuthn, not a separate API.

## Edge cases (`docs/EDGE_CASES.md`)

- 3.2 deactivate → 401 on next `/me`.
- 3.4 bcrypt 72-byte cap.
- 3.5 replay: **documented skip** (no Redis); pyotp window only.
- 3.6 clock skew: `valid_window=1`.
- 3.7 first-login: `is_first_login` on `/me`; UI gates pages (no extra JWT scope in prototype).

## Assumptions

- Prototype 8h access token, no refresh.
- Audit `record()` already commits; auth commits user row then records audit.
- `GET /health` unauthenticated.

## Review

1. **Security holes:** Temp tokens accepted as access tokens if we forget `purpose` check — mitigated by `require_access_jwt`. TOTP replay in 30s window accepted (prototype). localStorage JWT is existing prototype risk.
2. **Contradictions:** auth_plan Redis/refresh/15-min tokens deferred per CLAUDE.md / `security.py` comments. MFA_STEP_UP_* added to `audit_events.py` (already in `audit_trail_plan.md`).
3. **Simpler?** Yes vs WebAuthn; TOTP matches design and frontend.
4. **EDGE_CASES:** 3.5 documented skip; 3.6 handled; 3.7 UI flag not restricted JWT.
5. **Breakage:** None if routes were stubs. Frontend already calls these paths. Seed user required to demo.

## Later (not this branch)

- Passkeys: `POST /auth/webauthn/register` + `authenticate`.
- Biometrics: mobile/WebAuthn platform authenticator; `FUTURE_FEATURES.md` mobile app.
