"""
AuditEvent model — append-only, hash-chained activity log.

STORES: every sensitive action. Each row includes prev_hash (previous event's this_hash)
and this_hash = SHA256(prev_hash | event_type | actor | target | case | ip | ts | metadata).
Tampering with any row breaks every subsequent hash; GET /audit/verify detects it.

KEY POINTS:
    - id is BIGSERIAL (sequential) so chain ordering is unambiguous — NOT a UUID.
    - Table is append-only: the migration REVOKEs UPDATE/DELETE from the app DB user.
    - metadata holds NON-sensitive context only (never document content or PII).
    - prev_hash/this_hash are internal — never serialized to API clients.

Chain append MUST be serialized with pg_advisory_xact_lock (works across Gunicorn
workers; a Python threading.Lock does NOT). Full design + canonical AuditEventType enum:
../../feature_plans/audit_trail_plan.md
"""

from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from app.extensions import db


class AuditEvent(db.Model):
    __tablename__ = "audit_events"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)  # BIGSERIAL
    event_type = db.Column(db.Text, nullable=False)
    actor_user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"))  # NULL for system
    target_type = db.Column(db.Text)     # "document" | "case" | "user" | ...
    target_id = db.Column(UUID(as_uuid=True))
    case_id = db.Column(UUID(as_uuid=True))   # denormalized for fast case-scoped queries
    ip_address = db.Column(INET)
    event_metadata = db.Column("metadata", JSONB)   # DB column is "metadata"

    prev_hash = db.Column(db.Text, nullable=False)   # 64-char hex
    this_hash = db.Column(db.Text, nullable=False)   # 64-char hex
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
