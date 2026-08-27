# Security Reference — PRAMAAN: Secure Evidence Vault (leet / SIH26)

> **Prototype vs production:** this file documents the full security target. The **prototype**
> keeps all the crypto (AES-256-GCM chunks, HKDF, Ed25519, bcrypt, hash-chained audit, MFA,
> RBAC, step-up MFA) but simplifies session/infra: **one 8h JWT (no refresh/rotation),
> in-memory rate limiting, no Redis, keys in a local file KMS, chunks on local disk (Server B),
> no Nginx/TLS (localhost).** Sections below that mention refresh tokens, Redis, or TLS/HSTS
> describe the **production** hardening — see docs/ARCHITECTURE.md "Future / Production".

See `docs/THREAT_MODEL.md` for the full three-column threat scope table.

---

## Cryptographic Standards

| Purpose | Algorithm | Parameters |
|---------|-----------|------------|
| Symmetric encryption | AES-GCM | 256-bit key, 96-bit random IV, 128-bit tag |
| Key derivation | HKDF-SHA256 | salt=doc_id, info=f"chunk-{i}" |
| Password hashing | bcrypt | cost factor ≥ 12 |
| Signatures | Ed25519 | — |
| Hashing (integrity, audit chain) | SHA-256 | — |
| TLS | TLS 1.3 | ECDHE preferred |
| Token signing | HS256 (JWT) | 256-bit secret from env |

**Never use:** MD5, SHA-1, DES, 3DES, RC4, ECB mode, RSA < 2048-bit, PKCS#1v1.5 padding.

### Two subtle crypto rules (do not get these wrong)

1. **GCM nonce reuse is catastrophic — but structurally impossible here.** Reusing an (key, IV)
   pair under AES-GCM leaks the auth key. We avoid it by giving **every chunk its own key**
   (HKDF derives a distinct key per `chunk-{i}`). Each key therefore encrypts exactly one chunk,
   so a random 96-bit IV can never collide under the same key.

2. **bcrypt silently truncates at 72 bytes.** Cap password input at 72 bytes in the marshmallow
   schema, or pre-hash with SHA-256 + base64 before bcrypt. Pick one and apply it everywhere.

---

## Secret Management

All secrets loaded from environment variables. Never hardcode. Never commit.

**Three separate secrets — never share values between them:**

```
SECRET_KEY        — Flask cookie/session signing ONLY.
KMS_WRAPPING_KEY  — wraps document master keys in local file KMS. NEVER equals SECRET_KEY.
JWT_SECRET        — signs JWT access tokens. Also separate.
```

Required env vars for the **prototype** (full list in `codebase/.env.example`):

```bash
# Database
DATABASE_URL=postgresql+psycopg://dms_app_user:devpassword@localhost:5432/dms

# Chunk store (two-server topology)
CHUNK_STORE_BACKEND=local           # local | sftp
CHUNK_STORE_HOST=                   # Server B hostname (sftp demo)
CHUNK_STORAGE_DIR=./data/chunks     # path on Server B
CHUNK_STORE_USER=                   # OS user on Server B
CHUNK_STORE_KEYFILE=                # SSH private key path (no passwords)

# KMS
KMS_DIR=./data/keys
KMS_WRAPPING_KEY=<32+ bytes random> # wraps master keys — NOT the same as SECRET_KEY

# Auth
JWT_SECRET=<32+ bytes random>
JWT_ACCESS_TTL_SECONDS=28800        # 8h prototype
MFA_ISSUER=PRAMAAN
MFA_STEP_UP_MINUTES=15
ACCOUNT_LOCKOUT_THRESHOLD=5
ACCOUNT_LOCKOUT_MINUTES=15

# Uploads
MAX_FILE_SIZE_MB=500                # 500 MB prototype limit
CHUNK_SIZE_BYTES=1048576            # 1 MB

# App
SECRET_KEY=<32+ bytes random>       # Flask signing ONLY
CORS_ORIGINS=http://localhost:5173
ENVIRONMENT=development
```

---

## Key Lifecycle

| Phase | What happens | Status |
|-------|-------------|--------|
| Generation | `secrets.token_bytes(32)` at document upload time | Implemented (TODO) |
| Storage | AES-GCM wrap with KMS_WRAPPING_KEY → KMS_DIR/{doc_id}.key | Implemented (TODO) |
| Access | Read and unwrap on every download (no caching) | Implemented (TODO) |
| Rotation | KMS_WRAPPING_KEY rotation: re-wrap all key files with new value | **Required hardening** |
| Backup | KMS_DIR must be backed up separately from CHUNK_STORAGE_DIR | **Required hardening** |
| Recovery | Restore KMS_DIR + .env KMS_WRAPPING_KEY → full document access restored | **Required hardening** |
| Revocation | Delete KMS_DIR/{doc_id}.key → document permanently unreadable | Implemented (TODO) |
| Destruction | On hard delete: delete_key() removes the file | Implemented (TODO) |
| Compromise response | Rotate KMS_WRAPPING_KEY, re-wrap all keys, audit all recent accesses | **Required hardening** |

> In production, HashiCorp Vault handles rotation, backup, and audit natively.
> These are the prototype gaps where the local file KMS is weakest.

---

## Authentication Flow

```
1. POST /auth/login {email, password}
   → bcrypt.verify(password, hash)
   → If MFA enabled: return {mfa_required: true, temp_token (5 min)}

2. POST /auth/mfa/verify {temp_token, totp_code}
   → pyotp.TOTP(secret).verify(code, valid_window=1)
   → Issue access_token (JWT, 8h prototype) with claims:
       { sub: user_id, role, dept, iat, exp, mfa_at: now() }
   → Log: AuditEvent LOGIN

3. Every API request:
   → Bearer access_token in Authorization header
   → Verify JWT signature + expiry
   → Load user from DB, check is_active
   → RBAC: check user.role against endpoint permission

4. Sensitive actions (sign, share, delete, manage users):
   → @require_recent_mfa(minutes=15) checks: now - mfa_at <= 900s
   → If stale: return 401 { "code": "MFA_REQUIRED" }
   → Frontend: prompt for fresh TOTP code (not full re-login)

5. POST /auth/mfa/step-up {totp_code}
   → Verify TOTP against user's secret
   → Issue re-stamped access_token with fresh mfa_at = now()

6. POST /auth/logout
   → Clear token client-side; log AuditEvent LOGOUT
```

---

## RBAC Implementation

Define role hierarchy in `backend/app/core/rbac.py`. Two decorators:

```python
@require_roles(Role.CASE_OFFICER, Role.INVESTIGATOR)   # role check
@require_recent_mfa(minutes=15)                         # step-up MFA check
```

`@require_recent_mfa` reads the `mfa_at` claim from the JWT. If the gap exceeds the
window, it returns `401 { "code": "MFA_REQUIRED" }` — the frontend should prompt for a
TOTP code and call `POST /auth/mfa/step-up`, then retry the original request.

Audit `UNAUTHORIZED_ACCESS_ATTEMPT` is recorded on both role failures and MFA step-up rejections.

---

## Sharing Security

`allowed_email` is **required** for all share links in the prototype (CHANGES.md §9).
No anonymous open links. An email gate does not stop forwarding — it is a named recipient
restriction, not a cryptographic binding. The UI should communicate this clearly.

Every `SHARE_LINK_ACCESSED` audit event captures: IP address, user agent, share_id, document_id.

---

## Input Validation Rules

| Input | Validation |
|-------|-----------|
| Email | RFC 5321 format, max 254 chars |
| Password | Min 12 chars (max 72 **bytes** — bcrypt limit), 1 upper, 1 lower, 1 digit, 1 special |
| File upload | Max 500 MB; MIME verified by **magic bytes** (not header/extension). Allowlist: pdf, docx, xlsx, jpg, png, tiff, mp4, wav |
| Case number | `^[A-Za-z0-9\-\/]+$`, 3–50 chars |
| Search query | Max 200 chars; parameterized in SQL |
| User role | Must be one of Role enum values |
| JWT | Verify alg=HS256, exp not expired, mfa_at claim present for sensitive actions |
| Share email | RFC 5321 format; **required** — no anonymous links |

All validation via marshmallow schemas (`unknown=RAISE`). Never use `request.json` directly.

---

## HTTP Security Headers (Nginx — production)

```nginx
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Referrer-Policy "no-referrer" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none';" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
```

---

## Audit Event Types

> Abbreviated. The canonical, complete `AuditEventType` enum (30+ values) lives in
> `feature_plans/audit_trail_plan.md` — that is the single source of truth.

New events added for step-up MFA:
```python
MFA_STEP_UP_VERIFIED  = "MFA_STEP_UP_VERIFIED"    # successful step-up
MFA_STEP_UP_FAILED    = "MFA_STEP_UP_FAILED"       # wrong code at step-up
```

---

## Rate Limiting Policy

| Endpoint group | Limit | Window |
|---------------|-------|--------|
| POST /auth/login | 5 requests | 1 minute per IP |
| POST /auth/mfa/* | 5 requests | 1 minute per IP |
| POST /auth/mfa/step-up | 5 requests | 1 minute per user |
| File upload | 10 requests | 1 minute per user |
| Search | 60 requests | 1 minute per user |
| GET /share/* | 5 requests | 1 hour per IP |
| All other API | 120 requests | 1 minute per user |

**Prototype:** in-memory (Flask-Limiter `memory://`). **Production:** Redis-backed.

---

## Data Classification

| Data Type | Classification | Storage Rule |
|-----------|---------------|-------------|
| Document content | CONFIDENTIAL | Encrypted chunks in chunk store only (never DB) |
| Document master keys | SECRET | Local file KMS only — never DB, never chunk store |
| Passwords | SECRET | bcrypt hash in DB only |
| TOTP secrets | SECRET | AES-encrypted with app key before DB storage |
| Audit logs | RESTRICTED | DB, append-only (REVOKE UPDATE/DELETE), never bulk-exported |
| Document metadata | INTERNAL | PostgreSQL, access-controlled |
| User PII | INTERNAL | PostgreSQL, never in logs |
| Session tokens | INTERNAL | localStorage (prototype); Redis only (production) |

---

## Checklist Before Every PR

- [ ] No secrets or credentials in code or comments
- [ ] No raw SQL string interpolation
- [ ] All user inputs validated with a marshmallow schema (`unknown=RAISE`)
- [ ] Auth + RBAC applied to new endpoints
- [ ] `@require_recent_mfa` applied to all sensitive action endpoints
- [ ] Case-scoped access checked (404, not 403, for non-members)
- [ ] Audit event recorded for every sensitive operation (incl. MFA step-up failures)
- [ ] No document content written to disk unencrypted
- [ ] No PII or document content in log statements
- [ ] New crypto operations in `crypto.py` only — not inline
- [ ] Share link creation requires `allowed_email` (non-null, validated)
- [ ] Chunk storage keys are opaque (secrets.token_hex(16)) — not path-based
