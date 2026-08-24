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
