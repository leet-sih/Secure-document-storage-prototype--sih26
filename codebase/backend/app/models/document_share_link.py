"""
DocumentShareLink model — a time-limited token letting an external party download ONE
document without an account.

STORES: SHA256(token) (never the raw token), creator, optional email gate, expiry,
max_uses / use_count, revocation state. The raw token is shown to the creator once and
never persisted — same principle as password hashing.

ACCESS: public endpoint hashes the presented token, looks up this row, and atomically
increments use_count only if not revoked/expired/exhausted (see sharing plan for the
race-safe UPDATE ... RETURNING). Expired/revoked/exhausted => 410.

Full design: ../../feature_plans/document_sharing_plan.md
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID
from app.extensions import db


class DocumentShareLink(db.Model):
    __tablename__ = "document_share_links"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = db.Column(UUID(as_uuid=True), db.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    token_hash = db.Column(db.Text, nullable=False, unique=True)   # SHA256(token), hex
    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=False)

    allowed_email = db.Column(db.Text)          # optional gate (case-insensitive compare)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    max_uses = db.Column(db.Integer, nullable=False, default=1)   # -1 = unlimited (admin only)
    use_count = db.Column(db.Integer, nullable=False, default=0)

    is_revoked = db.Column(db.Boolean, nullable=False, default=False)
    revoked_by = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"))
    revoked_at = db.Column(db.DateTime(timezone=True))
    note = db.Column(db.Text)                    # reason for sharing (audit context)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
