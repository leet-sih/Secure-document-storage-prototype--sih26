"""
DocumentShareLink model — a time-limited token granting an external party access to either
a single document, all documents in a case, or the full case view.

SCOPES:
  DOCUMENT       — document_id required; single file download
  CASE_DOCUMENTS — case_id required; all non-deleted docs in the case
  CASE_FULL      — case_id required; case metadata + members + all docs

STORES: SHA256(token) (never the raw token), creator, optional email gate, expiry,
max_uses / use_count, revocation state. The raw token is shown to the creator once and
never persisted — same principle as password hashing.

ACCESS: public endpoint hashes the presented token, looks up this row, and atomically
increments use_count only if not revoked/expired/exhausted (see sharing plan for the
race-safe UPDATE ... RETURNING). Expired/revoked/exhausted => 410.

Full design: ../../feature_plans/document_sharing_plan.md
Scope extension: ../../feature_plans/specs/secure_sharing_spec.md
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID
from app.extensions import db

SHARE_SCOPES = ("DOCUMENT", "CASE_DOCUMENTS", "CASE_FULL")


class DocumentShareLink(db.Model):
    __tablename__ = "document_share_links"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Scope determines which of document_id / case_id is required.
    share_scope = db.Column(db.Text, nullable=False, default="DOCUMENT")

    # DOCUMENT scope: document_id required. CASE_* scopes: NULL.
    document_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=True,
    )
    # CASE_* scopes: case_id required. DOCUMENT scope: set for context (case the doc belongs to).
    case_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("cases.id", ondelete="SET NULL"),
        nullable=True,
    )

    token_hash = db.Column(db.Text, nullable=False, unique=True)   # SHA256(token), hex
    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=False)

    allowed_email = db.Column(db.Text)          # required gate (case-insensitive compare)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    max_uses = db.Column(db.Integer, nullable=False, default=1)   # -1 = unlimited (admin only)
    use_count = db.Column(db.Integer, nullable=False, default=0)

    is_revoked = db.Column(db.Boolean, nullable=False, default=False)
    revoked_by = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"))
    revoked_at = db.Column(db.DateTime(timezone=True))
    note = db.Column(db.Text)                    # reason for sharing (audit context)
    allow_download = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
