"""
signing.py — Ed25519 digital signatures for documents.

RESPONSIBILITY:
    Generate a user's signing key pair, sign a document payload, and verify a signature.
    The PRIVATE key is stored (AES-wrapped with SECRET_KEY) in users.signing_private_key_enc.
    The PUBLIC key is stored in User.signing_public_key (public keys are safe in the DB).

SIGNED PAYLOAD (what a signature actually covers):
    SHA256( integrity_hash | document_id | signer_user_id | iso_timestamp )
    Binding all four means: tampering with the document, the timestamp, or swapping the
    public key all invalidate the signature.

Reference: ../../feature_plans/digital_signatures_plan.md
"""

import hashlib

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from flask import current_app

from app.core.crypto import decrypt_string, encrypt_string

_SIGNING_KEY_INFO = b"ed25519-signing-key-at-rest"


def generate_keypair() -> tuple[bytes, bytes]:
    """Generate a fresh Ed25519 key pair.
    RETURNS: (private_key_raw_bytes, public_key_raw_bytes) — each 32 bytes."""
    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    public_bytes = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return private_bytes, public_bytes


def build_signed_payload(
    integrity_hash: str, document_id: str, signer_user_id: str, ts_iso: str
) -> bytes:
    """RETURNS: the 32-byte SHA-256 digest that gets signed/verified.
    All four fields are bound so that tampering with any one invalidates the signature."""
    payload = "|".join([integrity_hash, str(document_id), str(signer_user_id), ts_iso])
    return hashlib.sha256(payload.encode()).digest()


def sign(private_key_bytes: bytes, signed_payload: bytes) -> str:
    """RETURNS: 128-char hex-encoded Ed25519 signature."""
    private_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
    return private_key.sign(signed_payload).hex()


def verify(public_key_bytes: bytes, signature_hex: str, signed_payload: bytes) -> bool:
    """RETURNS: True if valid, False on InvalidSignature or any decoding error."""
    try:
        public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        public_key.verify(bytes.fromhex(signature_hex), signed_payload)
        return True
    except (InvalidSignature, Exception):
        return False


def encrypt_private_key(private_key_bytes: bytes) -> str:
    """AES-256-GCM wrap raw Ed25519 private key bytes for DB storage.
    Domain-separated from TOTP wrapping via a distinct HKDF info tag.
    RETURNS: hex(iv || ciphertext+tag)."""
    return encrypt_string(
        private_key_bytes.hex(), current_app.config["SECRET_KEY"], _SIGNING_KEY_INFO
    )


def decrypt_private_key(enc_blob: str) -> bytes:
    """Reverse encrypt_private_key. RETURNS: raw 32-byte Ed25519 private key."""
    return bytes.fromhex(
        decrypt_string(enc_blob, current_app.config["SECRET_KEY"], _SIGNING_KEY_INFO)
    )
