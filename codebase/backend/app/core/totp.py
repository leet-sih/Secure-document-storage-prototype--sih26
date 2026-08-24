"""
totp.py — TOTP (Time-based One-Time Password) MFA helpers.

RESPONSIBILITY:
    Generate a TOTP secret, encrypt/decrypt it with the app SECRET_KEY for storage, build the
    otpauth provisioning URI + QR code, and verify submitted 6-digit codes.

PROTOTYPE SIMPLIFICATION:
    No Redis replay guard. pyotp's valid_window=1 (±30s) is enough for the demo. Production
    re-adds a single-use guard so a code can't be replayed within its 30s window
    (see feature_plans/auth_plan.md).

Reference: ../../feature_plans/auth_plan.md
"""

# Implementation is small — pyotp does the heavy lifting:
#   generate_secret:   pyotp.random_base32()
#   provisioning_uri:  pyotp.TOTP(secret).provisioning_uri(email, issuer_name=MFA_ISSUER)
#   verify:            pyotp.TOTP(secret).verify(code, valid_window=1)
#   encrypt/decrypt:   AES-wrap the secret with SECRET_KEY before storing in User.totp_secret


def generate_secret() -> str:
    """RETURNS: a new base32 TOTP secret. TODO."""
    raise NotImplementedError


def encrypt_secret(secret_b32: str) -> str:
    """AES-encrypt the secret with SECRET_KEY for at-rest storage. RETURNS: ciphertext str. TODO."""
    raise NotImplementedError


def decrypt_secret(encrypted: str) -> str:
    """Reverse of encrypt_secret. RETURNS: base32 secret. TODO."""
    raise NotImplementedError


def provisioning_uri(secret_b32: str, account_email: str) -> str:
    """RETURNS: otpauth://... URI for authenticator apps. TODO."""
    raise NotImplementedError


def qr_png_base64(otpauth_uri: str) -> str:
    """RETURNS: base64-encoded PNG QR of the provisioning URI. TODO."""
    raise NotImplementedError


def verify(secret_b32: str, code: str) -> bool:
    """Verify a 6-digit code (valid_window=1 for ±30s drift). RETURNS: True if valid. TODO."""
    raise NotImplementedError
