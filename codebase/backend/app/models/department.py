"""
Department model — an organizational unit a user belongs to.

STORES: police stations, courts, forensic labs, legal departments.
Seeded at setup (see seed.py). Referenced by User and Case.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID
from app.extensions import db


class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.Text, nullable=False, unique=True)
    # dept_type: "POLICE" | "COURT" | "FORENSIC" | "LEGAL"
    dept_type = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
