"""
crypto.py — the ONLY module allowed to perform raw cryptographic operations.

RESPONSIBILITY:
    Per-chunk AES-256-GCM encryption/decryption with HKDF-derived keys, plus the
    hashing helpers used by the chunked-storage pipeline.

WHY PER-CHUNK KEYS:
    Each chunk gets its own key via HKDF(master_key, salt=doc_id, info="chunk-{i}").
    Because every key encrypts exactly ONE chunk, a random 96-bit GCM IV can never
    collide under the same key — the catastrophic GCM nonce-reuse failure is
    structurally impossible. Do NOT "optimize" by sharing one key across chunks.

NOTE ON THE AUTH TAG:
    cryptography's AESGCM.encrypt() returns ciphertext WITH the 16-byte tag appended;
    decrypt() expects the same. We therefore never store the tag separately — it lives
    inside the ciphertext object in MinIO, and chunk_hash = SHA256(that object).

Reference: ../../feature_plans/chunked_document_storage_plan.md
"""

import hashlib
import os
import secrets

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


def generate_master_key() -> bytes:
    """Return 32 fresh random bytes to serve as a document's master key.
    Stored ONLY in the KMS/Vault, never in the DB or MinIO."""
    return secrets.token_bytes(32)


def derive_chunk_key(master_key: bytes, document_id: str, chunk_index: int) -> bytes:
    """Deterministically derive a unique 32-byte key for one chunk.
    RETURNS: 32-byte key. Same (master_key, document_id, chunk_index) -> same key."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=str(document_id).encode(),
        info=f"chunk-{chunk_index}".encode(),
    )
    return hkdf.derive(master_key)


def encrypt_chunk(chunk_key: bytes, plaintext: bytes) -> tuple[bytes, bytes]:
    """Encrypt one chunk.
    RETURNS: (iv, ciphertext) where iv is 12 random bytes and ciphertext already
    includes the 16-byte GCM auth tag."""
    iv = os.urandom(12)
    ciphertext = AESGCM(chunk_key).encrypt(iv, plaintext, None)
    return iv, ciphertext


def decrypt_chunk(chunk_key: bytes, iv: bytes, ciphertext: bytes) -> bytes:
    """Decrypt one chunk. Raises cryptography.exceptions.InvalidTag if the ciphertext
    or tag was modified. RETURNS: plaintext bytes."""
    return AESGCM(chunk_key).decrypt(iv, ciphertext, None)


def sha256_hex(data: bytes) -> str:
    """RETURNS: hex SHA-256 of `data`. Used for chunk_hash (over ciphertext)."""
    return hashlib.sha256(data).hexdigest()


def compute_integrity_hash(chunk_hashes_in_order: list[str]) -> str:
    """RETURNS: hex SHA-256 over the ordered concatenation of chunk hashes.
    This is Document.integrity_hash — re-checked on every download."""
    return hashlib.sha256("".join(chunk_hashes_in_order).encode()).hexdigest()


# ──────────────────────────────────────────────────────────────────
# Master-key wrapping (for the Postgres keystore — see core.kms)
# ──────────────────────────────────────────────────────────────────
# The document master key is stored WRAPPED (AES-256-GCM encrypted) under KMS_WRAPPING_KEY,
# which is a separate env secret from SECRET_KEY/JWT_SECRET and NEVER lives in the DB.
# See feature_plans/specs/document_encryption_keystore_spec.md.

def _wrapping_key_bytes(wrapping_secret: str) -> bytes:
    """Derive a fixed 32-byte AES key from the KMS_WRAPPING_KEY env secret.
    The secret is already high-entropy (generated via secrets.token_urlsafe), so a plain
    SHA-256 is sufficient to map an arbitrary-length string to a 256-bit key — no salt needed."""
    return hashlib.sha256(wrapping_secret.encode()).digest()


def wrap_master_key(wrapping_secret: str, master_key: bytes) -> tuple[bytes, bytes]:
    """Wrap (encrypt) a document master key for at-rest storage in the DB keystore.
    RETURNS: (iv, wrapped) where iv is 12 random bytes and wrapped is AES-256-GCM ciphertext
    (32-byte key + 16-byte tag = 48 bytes). Wrapped under KMS_WRAPPING_KEY — NOT SECRET_KEY."""
    iv = os.urandom(12)
    wrapped = AESGCM(_wrapping_key_bytes(wrapping_secret)).encrypt(iv, master_key, None)
    return iv, wrapped


def unwrap_master_key(wrapping_secret: str, iv: bytes, wrapped: bytes) -> bytes:
    """Reverse wrap_master_key. Raises cryptography.exceptions.InvalidTag if the wrapped key
    or the wrapping secret is wrong. RETURNS: the 32-byte master key."""
    return AESGCM(_wrapping_key_bytes(wrapping_secret)).decrypt(iv, wrapped, None)


# ──────────────────────────────────────────────────────────────────
# Small-secret wrapping (for TOTP seeds — see core.totp)
# ──────────────────────────────────────────────────────────────────

def _aes_key_from_secret(secret: str, info: bytes) -> bytes:
    """HKDF-SHA256 → 32-byte AES key. `secret` is an app env string (e.g. SECRET_KEY)."""
    hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=b"pramaan-aes", info=info)
    return hkdf.derive(secret.encode("utf-8"))


def encrypt_string(plaintext: str, wrapping_secret: str, info: bytes) -> str:
    """AES-256-GCM wrap for small secrets (TOTP seed). RETURNS: hex(iv || ciphertext+tag)."""
    key = _aes_key_from_secret(wrapping_secret, info)
    iv, ciphertext = encrypt_chunk(key, plaintext.encode("utf-8"))
    return (iv + ciphertext).hex()


def decrypt_string(blob_hex: str, wrapping_secret: str, info: bytes) -> str:
    """Reverse of encrypt_string. Raises InvalidTag if tampered."""
    raw = bytes.fromhex(blob_hex)
    iv, ciphertext = raw[:12], raw[12:]
    key = _aes_key_from_secret(wrapping_secret, info)
    return decrypt_chunk(key, iv, ciphertext).decode("utf-8")


# ──────────────────────────────────────────────────────────────────
# Database text-field encryption (OCR text, future: annotations)
# ──────────────────────────────────────────────────────────────────
# OCR text is sensitive legal content that must not sit plaintext in PostgreSQL.
# These helpers encrypt/decrypt arbitrary UTF-8 text under a key derived from the
# document's existing master key, using a field-specific `info` tag so that
# different fields on the same document are cryptographically independent.
#
# Storage format: hex( iv[12] || ciphertext_with_tag[n+16] )
# Callers: document_service._encrypt_ocr_* / _decrypt_ocr_fields

def encrypt_field(plaintext: str, master_key: bytes, info: bytes) -> str:
    """Encrypt a text field under a sub-key derived from `master_key` with `info`.
    RETURNS: hex(iv || ciphertext_with_tag)."""
    field_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"pramaan-field",
        info=info,
    ).derive(master_key)
    iv, ciphertext = encrypt_chunk(field_key, plaintext.encode("utf-8"))
    return (iv + ciphertext).hex()


def decrypt_field(blob_hex: str, master_key: bytes, info: bytes) -> str:
    """Reverse of encrypt_field. Raises InvalidTag if tampered or wrong key/info."""
    raw = bytes.fromhex(blob_hex)
    iv, ciphertext = raw[:12], raw[12:]
    field_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"pramaan-field",
        info=info,
    ).derive(master_key)
    return decrypt_chunk(field_key, iv, ciphertext).decode("utf-8")
