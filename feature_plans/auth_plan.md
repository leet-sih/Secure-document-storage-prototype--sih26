# Feature Plan: Authentication, MFA & Step-Up MFA

## What Is This Feature?

The authentication system is the front door to the entire platform. Every user — officer, investigator, prosecutor, auditor — must prove their identity before accessing any data. It is composed of four layers:

1. **Credential authentication** — email + password verified against a bcrypt hash
2. **Multi-Factor Authentication (TOTP)** — a 6-digit time-based one-time password from an authenticator app
3. **Session management** — JWT access tokens (8h in prototype)
4. **Step-up MFA** — TOTP re-check required before sensitive actions if session's last MFA check is older than 15 minutes

This feature has no "nice to have" parts. Every component is P0.

---

## Why Is It Needed?

Legal and investigative documents are high-value targets. A single compromised account in a paper-based or single-factor system can expose entire case files, witness identities, and evidence chains. MFA ensures that a stolen password alone is not sufficient — the attacker also needs the physical device of the user. JWT with short expiry limits the damage window if a token is intercepted.

---

## Threat Model for This Feature

| Threat | Mitigation |
|--------|-----------|
| Brute-force password | Rate limit (5 req/min), account lockout after 5 failures |
| Credential stuffing | Same as above + bcrypt makes bulk verification slow |
| Stolen access token | 15-minute expiry limits damage window |
| Stolen refresh token | httpOnly cookie (JS cannot read it), rotation on every use, stored hash in Redis |
| MFA bypass | TOTP verified server-side before any token is issued; no way to skip |
| Session fixation | New token pair issued on every login; old tokens invalidated |
| Replay attack (TOTP) | Each TOTP code is single-use; Redis marks used codes for 30-second window |

---

## How It Works — Full Flow

### Step 1: Password Login

```
POST /api/v1/auth/login
Body: { "email": "...", "password": "..." }

Server:
  1. Load user by email from DB
  2. Check user.is_active — if False, return 403
  3. Check user.locked_until — if in future, return 423 (locked)
  4. bcrypt.checkpw(password, user.password_hash)
     - If fail: increment user.failed_logins
                if failed_logins >= 5: set locked_until = now + 15min
                record AuditEvent: LOGIN_FAILED
                return 401
  5. Reset user.failed_logins = 0
  6. If user.totp_secret is NULL (MFA not set up yet):
       → Issue full token pair (first-login grace)
       → Return: { access_token, mfa_setup_required: true }
  7. If user.totp_secret is SET:
       → Create a short-lived temp_token (JWT, 5 min, claim: {"purpose":"mfa","sub": user_id})
       → Return: { mfa_required: true, temp_token }
```

### Step 2: MFA Verification

```
POST /api/v1/auth/mfa/verify
Body: { "temp_token": "...", "totp_code": "123456" }

Server:
  1. Decode temp_token — verify signature, expiry, purpose == "mfa"
  2. Load user by sub claim
  3. Decrypt user.totp_secret (was encrypted before storage)
  4. pyotp.TOTP(secret).verify(totp_code, valid_window=1)
     - valid_window=1 allows ±30 seconds clock drift
  5. Check Redis: has this code been used for this user in the last 60s?
     - If yes: return 401 (replay attempt)
     - Mark code as used in Redis with 60s TTL
  6. Issue token pair:
     - access_token: JWT, HS256, 15-min expiry
       payload: { sub: user_id, role: user.role, dept: user.department_id, iat, exp }
     - refresh_token: 32-byte random hex string
       store SHA256(refresh_token) in Redis with key "refresh:{user_id}:{token_hash}"
       TTL = 7 days
  7. Return access_token in JSON body
     Prototype: no refresh token/cookie — single 8h access token
     Token payload includes `mfa_at: unix_timestamp_now` (epoch seconds)
  8. Record AuditEvent: LOGIN
```

### Step 3: MFA Setup (first time)

```
GET /api/v1/auth/mfa/setup
(requires valid access_token, user must have mfa_setup_required flag)

Server:
  1. Generate TOTP secret: pyotp.random_base32()
  2. Encrypt secret with app SECRET_KEY before storing
  3. Save encrypted secret to user.totp_secret_pending (not active yet)
  4. Return:
     {
       "otpauth_uri": "otpauth://totp/PRAMAAN:email@example.com?secret=...&issuer=PRAMAAN",
       "qr_code_base64": "<PNG base64>"  # generated with qrcode library
     }

POST /api/v1/auth/mfa/confirm
Body: { "totp_code": "123456" }

Server:
  1. Verify code against pending secret
  2. Move pending → active: user.totp_secret = user.totp_secret_pending
  3. Clear user.totp_secret_pending
  4. Record AuditEvent: MFA_ENABLED
```

### Step 4: Token Refresh

```
POST /api/v1/auth/refresh
(no Authorization header — reads httpOnly cookie)

Server:
  1. Read refresh_token from cookie
  2. Compute token_hash = SHA256(refresh_token)
  3. Look up Redis key "refresh:{user_id}:{token_hash}"
     - If missing/expired: return 401
  4. Delete old key (rotation — old token invalidated)
  5. Issue new access_token + new refresh_token
  6. Set new cookie
  7. Record AuditEvent: TOKEN_REFRESHED
```

### Step 5: Step-Up MFA (prototype — new requirement from deck slide 2)

Sensitive actions are guarded by `@require_recent_mfa(minutes=15)` in `core/rbac.py`.
The decorator reads the `mfa_at` claim from the JWT. If `now() - mfa_at > 900s`, it returns:

```
HTTP 401
{ "code": "MFA_REQUIRED", "message": "Please verify your identity to continue." }
```

The frontend must detect `code == "MFA_REQUIRED"` (not the same as a full 401 session expiry)
and show a step-up TOTP prompt instead of redirecting to /login.

```
POST /api/v1/auth/mfa/step-up
Body: { "totp_code": "123456" }
(requires valid access_token — not a new login)

Server:
  1. @jwt_required() — verify token is valid
  2. Load user; decrypt totp_secret
  3. pyotp.TOTP(secret).verify(totp_code, valid_window=1)
     - If fail: increment step-up failure counter; AuditEvent: MFA_STEP_UP_FAILED; return 401
  4. Issue new access_token with mfa_at = now() (all other claims identical)
  5. AuditEvent: MFA_STEP_UP_VERIFIED
  6. Return { "access_token": "..." }
```

Rate limit: 5/minute per user on `/auth/mfa/step-up`.

**Sensitive action set (requires step-up MFA):**
- `POST /documents/{id}/sign`
- `POST /documents/{id}/share`
- `DELETE /documents/{id}`
- `POST /users` (create user)
- `PATCH /users/{id}/deactivate`
- `PATCH /users/{id}/role`

### Step 6: Logout

```
POST /api/v1/auth/logout
(requires valid access_token)

Server:
  1. Clear token client-side (prototype has no server-side revocation)
  2. Record AuditEvent: LOGOUT
```

---

## Database Changes

```sql
-- users table (auth-relevant columns)
ALTER TABLE users ADD COLUMN IF NOT EXISTS
  password_hash       TEXT NOT NULL,
  totp_secret         TEXT,           -- AES-encrypted TOTP secret
  totp_secret_pending TEXT,           -- unconfirmed setup secret
  is_active           BOOLEAN DEFAULT TRUE,
  failed_logins       INTEGER DEFAULT 0,
  locked_until        TIMESTAMPTZ,
  last_login_at       TIMESTAMPTZ,
  password_changed_at TIMESTAMPTZ DEFAULT now();
```

No refresh tokens in DB — they live in Redis only (fast lookup, automatic TTL expiry).

---

## Redis Key Schema

| Key | Value | TTL |
|-----|-------|-----|
| `refresh:{user_id}:{token_hash}` | `"valid"` | 7 days |
| `login_attempts:{ip}` | count (integer) | 1 minute (sliding) |
| `user_locked:{user_id}` | `"1"` | 15 minutes |
| `totp_used:{user_id}:{code}` | `"1"` | 60 seconds |
| `access_blocklist:{jti}` | `"1"` | until token exp |

---

## Flask Implementation Structure

```
backend/app/
├── blueprints/
│   └── auth.py              # Blueprint with all /auth/* routes
├── core/
│   ├── security.py          # JWT config, token creation, cookie helpers
│   ├── totp.py              # TOTP generate/verify/encrypt helpers
│   └── rate_limit.py        # Flask-Limiter decorators
├── schemas/
│   └── auth_schemas.py      # marshmallow: LoginSchema, MFAVerifySchema
├── models/
│   └── user.py              # User SQLAlchemy model
└── services/
    └── auth_service.py      # Business logic (verify_credentials, issue_tokens, etc.)
```

### Key Flask-JWT-Extended config

```python
app.config["JWT_SECRET_KEY"] = os.environ["JWT_SECRET"]
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=15)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=7)
app.config["JWT_TOKEN_LOCATION"] = ["headers"]  # access token in header
app.config["JWT_COOKIE_SECURE"] = True
app.config["JWT_COOKIE_SAMESITE"] = "Strict"
```

Refresh token is NOT managed by Flask-JWT-Extended's built-in cookie system — we implement it manually as an opaque token in Redis to support rotation and revocation.

---

## marshmallow Schemas

```python
# schemas/auth_schemas.py
from marshmallow import Schema, fields, validate, validates, ValidationError
import re

class LoginSchema(Schema):
    email = fields.Email(required=True, load_only=True)
    password = fields.Str(required=True, load_only=True, validate=validate.Length(min=1, max=128))

class MFAVerifySchema(Schema):
    temp_token = fields.Str(required=True)
    totp_code = fields.Str(required=True, validate=validate.Regexp(r'^\d{6}$'))

class MFAConfirmSchema(Schema):
    totp_code = fields.Str(required=True, validate=validate.Regexp(r'^\d{6}$'))

class PasswordChangeSchema(Schema):
    current_password = fields.Str(required=True, load_only=True)
    new_password = fields.Str(required=True, load_only=True)

    @validates("new_password")
    def validate_password_strength(self, value):
        if len(value) < 12:
            raise ValidationError("Password must be at least 12 characters")
        # bcrypt only reads the first 72 BYTES; anything beyond is silently ignored,
        # which is a security footgun (two different long passwords can hash equal).
        # Reject over-long input rather than let bcrypt truncate it.
        if len(value.encode("utf-8")) > 72:
            raise ValidationError("Password must be at most 72 bytes")
        if not re.search(r'[A-Z]', value):
            raise ValidationError("Must contain an uppercase letter")
        if not re.search(r'[a-z]', value):
            raise ValidationError("Must contain a lowercase letter")
        if not re.search(r'\d', value):
            raise ValidationError("Must contain a digit")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise ValidationError("Must contain a special character")
```

> **bcrypt 72-byte rule (applies everywhere a password is hashed):** enforce the 72-byte cap in
> the schema *or* pre-hash with SHA-256 + base64 before bcrypt — pick one project-wide. Note the
> cap is in **bytes**, so multibyte scripts (Devanagari, Tamil) reach it in far fewer characters.
> The temporary-password generator in `user_management_plan.md` produces ASCII, so it is unaffected.

---

## Frontend Components

| Component | Route | Description |
|-----------|-------|-------------|
| `LoginForm` | `/login` | Email + password fields, error states, loading spinner |
| `MFAStep` | `/login` (step 2) | 6-digit code input, countdown timer showing code validity, "lost access" link |
| `MFASetup` | `/mfa-setup` | QR code display + confirmation code input |
| `SessionTimeout` | Global | Modal warning 2 min before access token expiry; auto-refresh on activity |

### Frontend session strategy (prototype)
- `access_token` stored in localStorage (TOKEN_KEY = "dms_access_token") for prototype convenience
- `AuthContext.tsx` (React Context + useReducer) holds user and status; reads token from localStorage on mount
- `apiFetch()` reads token directly from localStorage — works outside the component tree
- On 401 with `{ code: "MFA_REQUIRED" }`: show step-up TOTP modal, call `/auth/mfa/step-up`, replace token, retry
- On 401 without that code: clear localStorage and redirect to /login
- No Zustand, no Axios (removed in CHANGES.md §5)
- No document data cached in browser storage ever

---

## Rate Limiting

Using Flask-Limiter with Redis backend:

```python
# Per-IP on login
@auth_bp.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
@limiter.limit("20 per hour")
def login(): ...

# Per-IP on MFA
@auth_bp.route("/mfa/verify", methods=["POST"])
@limiter.limit("5 per minute")
def mfa_verify(): ...
```

When rate limit is exceeded: return 429, record AuditEvent: RATE_LIMIT_EXCEEDED.

---

## Edge Cases & Error Handling

| Scenario | Behaviour |
|----------|-----------|
| Wrong password | 401, generic message ("Invalid credentials" — do not say which field is wrong) |
| Account locked | 423, message: "Account temporarily locked. Try again after {time}." |
| Expired temp_token | 401 — user must start login again |
| TOTP clock drift > 30s | Fail — tell user to sync device clock |
| TOTP code reused within 60s | 401 — "Code already used" |
| MFA not yet set up | Issue full tokens but set `mfa_setup_required: true` in response — frontend forces MFA setup before dashboard |
| Refresh token cookie missing | 401 — redirect to login |
| Concurrent logins | Allowed — each issues a new refresh token; all can be active simultaneously |
| Admin force-logout user | Delete all `refresh:{user_id}:*` keys in Redis |
| **Refresh-rotation race (two tabs)** | Both tabs send the same refresh token near-simultaneously. Rotation deletes it on first use, so the second gets 401. Mitigate on the client: single-flight the refresh call (one in-flight refresh shared across tabs via a mutex/broadcast channel), and give the just-rotated token a short (~10s) Redis grace key so an in-flight second request still succeeds. |
| **Access token expires mid-request during a long upload/download** | Auth is checked once at request start; a 10-min streaming download continues even if the 15-min token would expire mid-stream. Acceptable. Do NOT re-check auth mid-stream (would abort a valid transfer). |
| User deactivated while holding a valid access token | Remains usable until token expiry (≤15 min) because the JWT is stateless. `is_active` is re-checked on every request via the user load, so deactivation takes effect on the next request — but a cached-identity fast path (if added) must not skip that check. |
| Clock skew between backend and Redis/DB hosts | Use `expires_at` computed by the app (single clock) for token TTLs; rely on Redis TTL only as a backstop. Keep all containers on NTP. |
| System time moves backward (NTP correction) | TOTP `valid_window=1` absorbs ±30s; larger jumps reject the code — user retries. Never widen the window to "fix" this. |

---

## Testing Plan

```
tests/auth/
├── test_login.py
│   ├── test_valid_credentials_triggers_mfa_step
│   ├── test_wrong_password_returns_401
│   ├── test_wrong_password_increments_failed_count
│   ├── test_fifth_wrong_password_locks_account
│   ├── test_locked_account_returns_423
│   ├── test_inactive_user_returns_403
│   └── test_rate_limit_after_5_requests
├── test_mfa.py
│   ├── test_valid_totp_issues_token_pair
│   ├── test_invalid_totp_returns_401
│   ├── test_expired_temp_token_returns_401
│   ├── test_totp_replay_returns_401
│   └── test_mfa_setup_confirm_flow
├── test_tokens.py
│   ├── test_refresh_issues_new_access_token
│   ├── test_refresh_rotates_refresh_token
│   ├── test_old_refresh_token_rejected_after_rotation
│   └── test_logout_invalidates_refresh_token
```

---

## Dependencies (requirements.txt additions)

```
flask-jwt-extended==4.7.*
flask-limiter[redis]==3.8.*
bcrypt==4.2.*
pyotp==2.9.*
qrcode[pil]==8.0.*
cryptography==43.*       # for TOTP secret encryption
```

---

## Implementation Order

1. User model + migration (include `mfa_at` in JWT payload — not a DB column)
2. `auth_service.py` — `verify_credentials()`, `issue_tokens()` (with `mfa_at` claim), `verify_totp()`
3. `auth.py` blueprint — `/login`, `/mfa/verify`, `/mfa/step-up`, `/logout`
4. `core/rbac.py` — `@require_roles` + `@require_recent_mfa(minutes)` decorators
5. Rate limiting setup (in-memory for prototype)
6. `/mfa/setup` + `/mfa/confirm`
7. Frontend: LoginForm → MFAStep flow (AuthContext.tsx, no Zustand)
8. Frontend: Step-up MFA modal (triggered on MFA_REQUIRED 401)
9. Frontend: MFASetup page
10. Tests — add `test_step_up_mfa.py`
