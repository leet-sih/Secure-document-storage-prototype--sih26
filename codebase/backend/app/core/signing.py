"""
signing.py — Ed25519 digital signatures for documents.

RESPONSIBILITY:
    Generate a user's signing key pair, sign a document payload, and verify a signature.
    The PRIVATE key is stored (AES-wrapped) in the KMS/Vault; the PUBLIC key is stored in
    User.signing_public_key (public keys are safe in the DB).

SIGNED PAYLOAD (what a signature actually covers):
    SHA256( integrity_hash | document_id | signer_user_id | iso_timestamp )
    Binding all four means: tampering with the document, the timestamp, or swapping the
    public key all invalidate the signature.

Reference: ../../feature_plans/digital_signatures_plan.md
"""

import hashlib


def generate_keypair() -> tuple[bytes, bytes]:
    """RETURNS: (private_key_raw_bytes, public_key_raw_bytes) for Ed25519. TODO."""
    raise NotImplementedError


def build_signed_payload(integrity_hash: str, document_id: str, signer_user_id: str, ts_iso: str) -> bytes:
    """RETURNS: the 32-byte SHA-256 digest that gets signed/verified."""
    payload = "|".join([integrity_hash, str(document_id), str(signer_user_id), ts_iso])
    return hashlib.sha256(payload.encode()).digest()


def sign(private_key_bytes: bytes, signed_payload: bytes) -> str:
    """RETURNS: hex-encoded Ed25519 signature. TODO."""
    raise NotImplementedError


def verify(public_key_bytes: bytes, signature_hex: str, signed_payload: bytes) -> bool:
    """RETURNS: True if valid, False otherwise (catch InvalidSignature). TODO."""
    raise NotImplementedError
