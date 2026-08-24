# Security Reference — Secure DMS (leet / SIH26)

> **Prototype vs production:** this file documents the full security target. The **prototype**
> keeps all the crypto (AES-256-GCM chunks, HKDF, Ed25519, bcrypt, hash-chained audit, MFA, RBAC)
> but simplifies session/infra: **one 8h JWT (no refresh/rotation), in-memory rate limiting, no
> Redis, keys in a local file KMS, chunks on local disk, no Nginx/TLS (localhost).** Sections
> below that mention refresh tokens, Redis, or TLS/HSTS describe the **production** hardening we
> add when we expand — see docs/ARCHITECTURE.md "Future / Production".

## Cryptographic Standards

| Purpose | Algorithm | Parameters |
|---------|-----------|------------|
| Symmetric encryption | AES-GCM | 256-bit key, 96-bit random IV, 128-bit tag |
| Key derivation | HKDF-SHA256 | salt=doc_id, info=f"chunk-{i}" |
| Password hashing | bcrypt | cost factor ≥ 12 |
| Signatures | Ed25519 | — |
| Hashing (integrity) | SHA-256 | — |
| TLS | TLS 1.3 | ECDHE preferred |
| Token signing | HS256 (JWT) | 256-bit secret from env |

**Never use:** MD5, SHA-1, DES, 3DES, RC4, ECB mode, RSA < 2048-bit, PKCS#1v1.5 padding.

### Two subtle crypto rules (do not get these wrong)

1. **GCM nonce reuse is catastrophic — but structurally impossible here.** Reusing an (key, IV)
   pair under AES-GCM leaks the auth key. We avoid it by giving **every chunk its own key**
   (HKDF derives a distinct key per `chunk-{i}`). Each key therefore encrypts exactly one chunk,
   so a random 96-bit IV can never collide under the same key. Never "optimize" this by reusing
   one key across chunks with random IVs.

2. **bcrypt silently truncates at 72 bytes.** A 128-char password is only 72 bytes of entropy to
   bcrypt, and multibyte (e.g. Hindi) characters hit the limit sooner. Either cap password input
   at 72 bytes in the marshmallow schema, or pre-hash with SHA-256 and base64-encode before
   bcrypt. Pick one and apply it everywhere passwords are hashed.

---

## Secret Management

All secrets loaded from environment variables. Never hardcode. Never commit.

Required env vars for the **prototype** (full list in `codebase/.env.example`):
```
# Database  (Flask is synchronous — psycopg driver, NOT asyncpg)
DATABASE_URL=postgresql+psycopg://dms_app_user:devpassword@localhost:5432/dms

# Local storage (prototype replacements for MinIO + Vault)
CHUNK_STORAGE_DIR=./data/chunks    # encrypted chunks (never committed)
KMS_DIR=./data/keys                # AES-wrapped master keys (never committed)

# Auth  (prototype: one long-lived access token, no refresh flow)
JWT_SECRET=<32+ bytes random>      # access-token signing (HS256)
JWT_ACCESS_TTL_SECONDS=28800       # 8h (demo convenience)
MFA_ISSUER=SecureDMS
ACCOUNT_LOCKOUT_THRESHOLD=5
ACCOUNT_LOCKOUT_MINUTES=15

# Uploads
MAX_FILE_SIZE_MB=100
CHUNK_SIZE_BYTES=1048576           # 1 MB

# App
SECRET_KEY=<32+ bytes random>      # Flask signing + AES-wraps TOTP/master-key secrets
CORS_ORIGINS=http://localhost:5173 # the Vite dev server
ENVIRONMENT=development
```

> All `*_SECRET`/`*_KEY` values must be strong random values and are **never** committed.
> `.env.example` ships with placeholders only.
>
> **Production** adds back: `REDIS_URL`, `CELERY_*`, `MINIO_*`, `VAULT_*` (with `KMS_BACKEND=vault`),
> shorter `JWT_ACCESS_TTL_SECONDS` + a refresh-token TTL, and HTTPS origins. See docs/ARCHITECTURE.md.

---

## Authentication Flow

```
1. POST /auth/login {email, password}
   → Server: bcrypt.verify(password, hash)
   → If MFA enabled: return {mfa_required: true, temp_token}
   
2. POST /auth/mfa/verify {temp_token, totp_code}
   → Server: pyotp.TOTP(secret).verify(code, valid_window=1)
   → Issue: access_token (JWT, 15min) + refresh_token (opaque, httpOnly cookie)
   → Log: AuditEvent LOGIN

3. Every API request:
   → Bearer access_token in Authorization header
   → Middleware: verify JWT signature + expiry
   → Load user from DB, check is_active
   → RBAC: check user.role against endpoint permission

4. POST /auth/refresh (cookie auto-sent)
   → Validate refresh token in Redis (not expired, not revoked)
   → Rotate: issue new access_token + new refresh_token
   → Revoke old refresh token in Redis

5. POST /auth/logout
   → Delete refresh token from Redis
   → Log: AuditEvent LOGOUT
```

---

## RBAC Implementation

Define role hierarchy in `backend/app/core/rbac.py`:

```python
from enum import Enum
from functools import wraps
from flask import abort
from flask_jwt_extended import get_jwt_identity
from app.models.user import User
from app.services.audit import audit_service
from app.core.audit_events import AuditEventType

class Role(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    CASE_OFFICER = "CASE_OFFICER"
    INVESTIGATOR = "INVESTIGATOR"
    PROSECUTOR = "PROSECUTOR"
    AUDITOR = "AUDITOR"
    VIEWER = "VIEWER"

def require_roles(*roles: Role):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_id = get_jwt_identity()
            user = User.query.get_or_404(user_id)
            if user.role not in [r.value for r in roles]:
                audit_service.record(
                    AuditEventType.UNAUTHORIZED_ACCESS_ATTEMPT,
                    actor_user_id=user_id
                )
                abort(403, description="Insufficient permissions")
            return func(*args, current_user=user, **kwargs)
        return wrapper
    return decorator
```

---

## Input Validation Rules

| Input | Validation |
|-------|-----------|
| Email | RFC 5321 format, max 254 chars |
| Password | Min 12 chars (max 72 **bytes** — bcrypt limit), 1 upper, 1 lower, 1 digit, 1 special |
| File upload | Max 500 MB per file; MIME verified by **magic bytes**, not header/extension. Allowlist: pdf, docx, xlsx, jpg, png, tiff, mp4, mpeg/wav audio |
| Case number | `^[A-Za-z0-9\-\/]+$`, 3–50 chars |
| Search query | Max 200 chars; parameterized in SQL |
| User role | Must be one of Role enum values |
| JWT | Verify alg=HS256, exp not expired, iss claim present |

All validation via marshmallow schemas — never use `request.json` directly without schema `.load()`.
Reject unexpected fields (`Meta.unknown = RAISE`) so clients can't smuggle extra keys (e.g. a
`role` field into a self-profile update).

---

## HTTP Security Headers (Nginx config)

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

> This is the abbreviated set. The **canonical, complete** `AuditEventType` enum (30+ values,
> including sharing, playground, and system events) lives in `feature_plans/audit_trail_plan.md`.
> Keep that file as the single source of truth; add new events there first.

```python
class AuditEventType(str, Enum):
    # Auth
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    LOGIN_FAILED = "LOGIN_FAILED"
    MFA_ENABLED = "MFA_ENABLED"
    MFA_VERIFIED = "MFA_VERIFIED"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    TOKEN_REFRESHED = "TOKEN_REFRESHED"

    # User management
    USER_CREATED = "USER_CREATED"
    USER_DEACTIVATED = "USER_DEACTIVATED"
    ROLE_CHANGED = "ROLE_CHANGED"

    # Case
    CASE_CREATED = "CASE_CREATED"
    CASE_ACCESSED = "CASE_ACCESSED"
    CASE_UPDATED = "CASE_UPDATED"
    CASE_MEMBER_ADDED = "CASE_MEMBER_ADDED"

    # Document
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    DOCUMENT_DOWNLOADED = "DOCUMENT_DOWNLOADED"
    DOCUMENT_PREVIEWED = "DOCUMENT_PREVIEWED"
    DOCUMENT_DELETED = "DOCUMENT_DELETED"
    DOCUMENT_SIGNED = "DOCUMENT_SIGNED"
    DOCUMENT_SHARED = "DOCUMENT_SHARED"
    SHARE_LINK_REVOKED = "SHARE_LINK_REVOKED"

    # Security
    UNAUTHORIZED_ACCESS_ATTEMPT = "UNAUTHORIZED_ACCESS_ATTEMPT"
    INTEGRITY_VIOLATION = "INTEGRITY_VIOLATION"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
```

---

## Rate Limiting Policy

| Endpoint group | Limit | Window |
|---------------|-------|--------|
| POST /auth/login | 5 requests | 1 minute per IP |
| POST /auth/mfa/* | 5 requests | 1 minute per IP |
| POST /auth/refresh | 20 requests | 1 minute per user |
| File upload | 10 requests | 1 minute per user |
| Search | 60 requests | 1 minute per user |
| All other API | 120 requests | 1 minute per user |

Implemented via Redis with sliding window counter.

---

## Data Classification

| Data Type | Classification | Storage Rule |
|-----------|---------------|-------------|
| Document content | CONFIDENTIAL | Encrypted chunks in MinIO only |
| Document master keys | SECRET | Vault only, never in DB or logs |
| Passwords | SECRET | bcrypt hash in DB only |
| TOTP secrets | SECRET | Encrypted with app key before DB storage |
| Audit logs | RESTRICTED | DB, append-only, never exported in bulk |
| Document metadata | INTERNAL | PostgreSQL, access-controlled |
| User PII | INTERNAL | PostgreSQL, never in logs |
| Session tokens | INTERNAL | Redis only, never in DB |

---

## Checklist Before Every PR

- [ ] No secrets or credentials in code or comments
- [ ] No raw SQL string interpolation
- [ ] All user inputs validated with a marshmallow schema (`unknown=RAISE`)
- [ ] Auth + RBAC applied to new endpoints
- [ ] Case-scoped access checked (404, not 403, for non-members)
- [ ] Audit event recorded for every sensitive operation
- [ ] No document content written to disk unencrypted
- [ ] No PII or document content in log statements
- [ ] New crypto operations in `crypto.py` only — not inline
