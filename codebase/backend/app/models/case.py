"""
Case model — the top-level container. Every document belongs to exactly one case.

STORES: case identity, status lifecycle, priority/category, ownership.
ACCESS CONTROL: a user sees a case only if they are an active row in case_members
(SUPER_ADMIN sees all). Non-members get 404, never 403.

STATUS lifecycle: OPEN -> UNDER_INVESTIGATION -> CLOSED -> ARCHIVED
    CLOSED   : documents read-only (no upload/delete)
    ARCHIVED : read-only + only SUPER_ADMIN/AUDITOR can access

Full rules: ../../feature_plans/case_management_plan.md
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID
from app.extensions import db

CASE_STATUSES = ("OPEN", "UNDER_INVESTIGATION", "CLOSED", "ARCHIVED")
CASE_PRIORITIES = ("LOW", "NORMAL", "HIGH", "CRITICAL")


class Case(db.Model):
    __tablename__ = "cases"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_number = db.Column(db.Text, nullable=False, unique=True)   # e.g. FIR-2026-DL-001
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.Text, nullable=False, default="OPEN")
    priority = db.Column(db.Text, nullable=False, default="NORMAL")
    category = db.Column(db.Text)

    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=False)
    department_id = db.Column(UUID(as_uuid=True), db.ForeignKey("departments.id"), nullable=False)

    closed_at = db.Column(db.DateTime(timezone=True))
    archived_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
