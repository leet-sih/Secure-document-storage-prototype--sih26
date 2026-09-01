"""
DocumentKey model — the WRAPPED master key for one document.

WHY THIS TABLE EXISTS (deliberate deviation from the parent plan's file KMS):
    Every document has a single 32-byte AES master key. All per-chunk keys are HKDF-derived
    from it (see core.crypto.derive_chunk_key), so this one key is the only secret that must be
    protected. It is stored here WRAPPED — AES-256-GCM encrypted under KMS_WRAPPING_KEY (an
    environment secret, NEVER in the DB) — so a stolen database dump yields only wrapped keys
    that cannot be unwrapped without BOTH the separate wrapping key AND the ciphertext (which
    lives in the chunk store, not here).

    NEVER stores the plaintext master key. NEVER stores KMS_WRAPPING_KEY.

    Access is always by known document_id (1:1 — document_id is the PK). Application code never
    LISTS this table — this mirrors the Vault "no list capability" rule.

    Production swaps this table for HashiCorp Vault; core.kms keeps the same three function
    signatures, so document_service never changes.

Full rationale + threat analysis: feature_plans/specs/document_encryption_keystore_spec.md
"""

from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID
from app.extensions import db


class DocumentKey(db.Model):
    __tablename__ = "document_keys"

    # 1:1 with documents — exactly one master key per document.
    document_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("documents.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    wrapped_key_hex = db.Column(db.Text, nullable=False)  # hex of AES-256-GCM(master_key)+tag (96 chars)
    wrap_iv_hex = db.Column(db.Text, nullable=False)      # hex of the 12-byte GCM nonce (24 chars)
    created_at = db.Column(
        db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
