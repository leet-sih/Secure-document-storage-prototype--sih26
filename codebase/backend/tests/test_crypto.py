"""
test_crypto.py — the security-critical crypto unit tests (no DB needed).

These validate app.core.crypto directly.
Source: chunked_document_storage_plan.md "Testing Plan" (test_crypto.py).
"""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-kms-ok")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-not-for-kms-ok")
os.environ.setdefault("KMS_WRAPPING_KEY", "test-kms-wrapping-key-32b-ok")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from cryptography.exceptions import InvalidTag

from app.core.crypto import (
    compute_integrity_hash,
    decrypt_chunk,
    derive_chunk_key,
    encrypt_chunk,
    generate_master_key,
)


def test_hkdf_different_indices_produce_different_keys():
    """derive_chunk_key with the same master/doc but different chunk_index -> different keys."""
    master = generate_master_key()
    doc = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    a = derive_chunk_key(master, doc, 0)
    b = derive_chunk_key(master, doc, 1)
    assert a != b
    assert len(a) == 32 and len(b) == 32


def test_hkdf_same_inputs_produce_same_key():
    """Determinism: identical inputs -> identical key (needed for decryption)."""
    master = generate_master_key()
    doc = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert derive_chunk_key(master, doc, 3) == derive_chunk_key(master, doc, 3)


def test_aes_gcm_encrypt_decrypt_roundtrip():
    """decrypt_chunk(encrypt_chunk(x)) == x for a range of sizes incl. the last partial chunk."""
    key = generate_master_key()
    for size in (0, 1, 15, 16, 1024, 1048576):
        plaintext = os.urandom(size) if size else b""
        iv, ciphertext = encrypt_chunk(key, plaintext)
        assert decrypt_chunk(key, iv, ciphertext) == plaintext


def test_aes_gcm_detects_ciphertext_modification():
    """Flipping a byte of ciphertext -> InvalidTag on decrypt."""
    key = generate_master_key()
    iv, ciphertext = encrypt_chunk(key, b"evidence-bytes")
    tampered = bytearray(ciphertext)
    tampered[0] ^= 0x01
    try:
        decrypt_chunk(key, iv, bytes(tampered))
        raise AssertionError("expected InvalidTag")
    except InvalidTag:
        pass


def test_aes_gcm_detects_iv_modification():
    """Wrong IV -> InvalidTag on decrypt."""
    key = generate_master_key()
    iv, ciphertext = encrypt_chunk(key, b"evidence-bytes")
    bad_iv = bytes(b ^ 0x01 for b in iv)
    try:
        decrypt_chunk(key, bad_iv, ciphertext)
        raise AssertionError("expected InvalidTag")
    except InvalidTag:
        pass


def test_integrity_hash_order_sensitive():
    """compute_integrity_hash is order-sensitive: swapping two chunk hashes changes the result."""
    a = "aa" * 32
    b = "bb" * 32
    assert compute_integrity_hash([a, b]) != compute_integrity_hash([b, a])
    assert compute_integrity_hash([a, b]) == compute_integrity_hash([a, b])
