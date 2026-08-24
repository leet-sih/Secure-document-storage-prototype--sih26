"""
core/ — security primitives and framework glue shared across the app.

    crypto.py        AES-256-GCM + HKDF (the ONLY place raw crypto lives)
    kms.py           master-key storage abstraction (env stub | Vault)
    signing.py       Ed25519 key generation / sign / verify
    security.py      password hashing, JWT issue/verify, refresh-token helpers
    rbac.py          Role enum + @require_roles decorator
    totp.py          TOTP secret gen/encrypt/verify + QR provisioning
    rate_limit.py    named Flask-Limiter limit strings
    audit_events.py  canonical AuditEventType enum
    errors.py        uniform JSON error envelope + handlers
"""
