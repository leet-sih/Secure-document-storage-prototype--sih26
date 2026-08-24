"""
test_crypto.py — the security-critical crypto unit tests (no DB needed).

These validate app.core.crypto directly. Fill in the bodies; the names are the contract.
Source: chunked_document_storage_plan.md "Testing Plan" (test_crypto.py).
"""

import pytest


def test_hkdf_different_indices_produce_different_keys():
    """derive_chunk_key with the same master/doc but different chunk_index -> different keys."""
    pytest.skip("TODO")


def test_hkdf_same_inputs_produce_same_key():
    """Determinism: identical inputs -> identical key (needed for decryption)."""
    pytest.skip("TODO")


def test_aes_gcm_encrypt_decrypt_roundtrip():
    """decrypt_chunk(encrypt_chunk(x)) == x for a range of sizes incl. the last partial chunk."""
    pytest.skip("TODO")


def test_aes_gcm_detects_ciphertext_modification():
    """Flipping a byte of ciphertext -> InvalidTag on decrypt."""
    pytest.skip("TODO")


def test_aes_gcm_detects_iv_modification():
    """Wrong IV -> InvalidTag on decrypt."""
    pytest.skip("TODO")


def test_integrity_hash_order_sensitive():
    """compute_integrity_hash is order-sensitive: swapping two chunk hashes changes the result."""
    pytest.skip("TODO")
