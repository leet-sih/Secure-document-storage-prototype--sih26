"""
DocumentSignature model — an Ed25519 signature over a document's integrity hash.

STORES: who signed which document, the integrity_hash snapshot at signing time, the
signed-payload hash, the signature (hex), and cached validity. One signature per user
per document (UNIQUE) — re-signing requires an explicit revoke first.

VERIFICATION: recompute payload = SHA256(integrity_hash_at_signing | doc_id | signer_id | ts),
verify with the signer's User.signing_public_key, AND check the document's CURRENT
integrity_hash still equals integrity_hash_at_signing (else it was modified after signing).

Full design: ../../feature_plans/digital_signatures_plan.md
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID
from app.extensions import db


class DocumentSignature(db.Model):
    __tablename__ = "document_signatures"
    __table_args__ = (
        db.UniqueConstraint("document_id", "signer_user_id", name="uq_one_sig_per_user_per_doc"),
    )

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = db.Column(UUID(as_uuid=True), db.ForeignKey("documents.id"), nullable=False)
    signer_user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=False)

    integrity_hash_at_signing = db.Column(db.Text, nullable=False)
    signed_payload_hash = db.Column(db.Text, nullable=False)
    signature_hex = db.Column(db.Text, nullable=False)   # Ed25519 signature (128 hex chars)

    is_valid = db.Column(db.Boolean)                     # NULL until first verify
    last_verified_at = db.Column(db.DateTime(timezone=True))
    revoked_at = db.Column(db.DateTime(timezone=True))
    comment = db.Column(db.Text, nullable=True)          # optional note from signer (max 500 chars enforced in schema)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
