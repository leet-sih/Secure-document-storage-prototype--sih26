"""
totp.py — TOTP (Time-based One-Time Password) MFA helpers.

PROTOTYPE: no Redis replay guard. pyotp valid_window=1 (±30s).
Encrypt/decrypt goes through crypto.py (no inline AES here).
"""

import base64
import io

import pyotp
import qrcode
from flask import current_app

from app.core.crypto import decrypt_string, encrypt_string

_TOTP_INFO = b"totp-at-rest"


def generate_secret() -> str:
    return pyotp.random_base32()


def encrypt_secret(secret_b32: str) -> str:
    return encrypt_string(secret_b32, current_app.config["SECRET_KEY"], _TOTP_INFO)


def decrypt_secret(encrypted: str) -> str:
    return decrypt_string(encrypted, current_app.config["SECRET_KEY"], _TOTP_INFO)


def provisioning_uri(secret_b32: str, account_email: str) -> str:
    issuer = current_app.config.get("MFA_ISSUER", "PRAMAAN")
    return pyotp.TOTP(secret_b32).provisioning_uri(name=account_email, issuer_name=issuer)


def qr_png_base64(otpauth_uri: str) -> str:
    img = qrcode.make(otpauth_uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def verify(secret_b32: str, code: str) -> bool:
    if not code or not secret_b32:
        return False
    return bool(pyotp.TOTP(secret_b32).verify(code, valid_window=1))
