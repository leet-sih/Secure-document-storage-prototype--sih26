"""TOTP helpers — no database."""

import pyotp
from flask import Flask

from app.core.crypto import decrypt_string, encrypt_string
from app.core.totp import decrypt_secret, encrypt_secret, generate_secret, provisioning_uri, qr_png_base64, verify


def _app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "unit-test-secret-key"
    app.config["MFA_ISSUER"] = "PRAMAAN"
    return app


def test_generate_and_verify_current_code() -> None:
    secret = generate_secret()
    assert verify(secret, pyotp.TOTP(secret).now())
    assert not verify(secret, "00000a")


def test_encrypt_roundtrip_and_qr() -> None:
    app = _app()
    with app.app_context():
        secret = generate_secret()
        wrapped = encrypt_secret(secret)
        assert wrapped != secret
        assert decrypt_secret(wrapped) == secret
        uri = provisioning_uri(secret, "officer@ncrb.gov.in")
        assert uri.startswith("otpauth://totp/")
        png = qr_png_base64(uri)
        assert len(png) > 20


def test_tampered_secret_blob_fails() -> None:
    blob = encrypt_string("JBSWY3DPEHPK3PXP", "unit-test-secret-key", b"totp-at-rest")
    raw = bytes.fromhex(blob)
    tampered = (raw[:-1] + bytes([raw[-1] ^ 0x01])).hex()
    try:
        decrypt_string(tampered, "unit-test-secret-key", b"totp-at-rest")
        assert False, "expected InvalidTag"
    except Exception:
        pass
