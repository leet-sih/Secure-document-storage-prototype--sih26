"""
security.py — passwords + JWT access tokens.  (PROTOTYPE: no refresh-token flow)

RESPONSIBILITY:
    - Password hashing/verification (bcrypt, cost >= 12, 72-byte cap).
    - Issuing/decoding JWT access tokens (Flask-JWT-Extended).

PROTOTYPE SIMPLIFICATION:
    We use ONE JWT access token with a long TTL (8h, see config) and no refresh-token rotation
    or Redis. The frontend keeps it and sends it on each request. Production re-introduces
    short access tokens + httpOnly refresh cookies + rotation — see feature_plans/auth_plan.md
    ("Production hardening"). Keeping the token longer-lived is the deliberate trade for demo
    simplicity.

Reference: ../../feature_plans/auth_plan.md ; ../../docs/SECURITY.md
"""


def hash_password(plaintext: str) -> str:
    """bcrypt hash. Caller must reject > 72 bytes first (bcrypt truncates silently).
    RETURNS: hash string to store in User.password_hash. TODO."""
    raise NotImplementedError


def verify_password(plaintext: str, password_hash: str) -> bool:
    """RETURNS: True if the password matches. Constant-time via bcrypt. TODO."""
    raise NotImplementedError


def issue_access_token(user) -> str:
    """RETURNS: signed JWT (8h) with claims {sub: user.id, role, dept}. TODO."""
    raise NotImplementedError


def issue_temp_mfa_token(user) -> str:
    """RETURNS: short-lived (5-min) JWT with claim purpose='mfa', used between the password
    step and the TOTP step. TODO."""
    raise NotImplementedError
