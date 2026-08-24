"""
CaseMember model — the membership + per-case role that drives all access control.

STORES: which user belongs to which case, and their role WITHIN that case (which can
differ from their system-wide User.role). Soft removal via is_active=False so historical
audit events still resolve the user.

INVARIANTS:
    - UNIQUE(case_id, user_id) — a user is a member at most once.
    - A case must always retain >= 1 active CASE_OFFICER (enforced in service layer).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID
from app.extensions import db

CASE_MEMBER_ROLES = ("CASE_OFFICER", "INVESTIGATOR", "PROSECUTOR", "VIEWER")


class CaseMember(db.Model):
    __tablename__ = "case_members"
    __table_args__ = (db.UniqueConstraint("case_id", "user_id", name="uq_case_member"),)

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = db.Column(UUID(as_uuid=True), db.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = db.Column(db.Text, nullable=False)  # one of CASE_MEMBER_ROLES

    added_by = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=False)
    added_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    removed_at = db.Column(db.DateTime(timezone=True))
    is_active = db.Column(db.Boolean, nullable=False, default=True)
