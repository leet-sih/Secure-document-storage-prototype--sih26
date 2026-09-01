"""cases and case_members tables

Revision ID: 002_case_management
Revises: 001_auth_totp
Create Date: 2026-08-30
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002_case_management"
down_revision = "001_auth_totp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_number", sa.Text(), nullable=False, unique=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False, server_default="OPEN"),
        sa.Column("priority", sa.Text(), nullable=False, server_default="NORMAL"),
        sa.Column("category", sa.Text()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id"), nullable=False),
        sa.Column("lead_officer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('OPEN','UNDER_INVESTIGATION','CLOSED','ARCHIVED')",
            name="chk_case_status",
        ),
        sa.CheckConstraint(
            "priority IN ('LOW','NORMAL','HIGH','CRITICAL')",
            name="chk_case_priority",
        ),
    )
    op.create_index("ix_cases_department_id", "cases", ["department_id"])
    op.create_index("ix_cases_status", "cases", ["status"])

    op.create_table(
        "case_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("added_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True)),
        sa.Column("removed_at", sa.DateTime(timezone=True)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("case_id", "user_id", name="uq_case_member"),
        sa.CheckConstraint(
            "role IN ('CASE_OFFICER','INVESTIGATOR','PROSECUTOR','VIEWER')",
            name="chk_case_member_role",
        ),
    )
    op.create_index("ix_case_members_case_id", "case_members", ["case_id"])
    op.create_index("ix_case_members_user_id", "case_members", ["user_id"])

    # Speed up timeline queries (case_id is already a column; this adds the index)
    op.create_index("ix_audit_events_case_id", "audit_events", ["case_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_case_id", table_name="audit_events")
    op.drop_index("ix_case_members_user_id", table_name="case_members")
    op.drop_index("ix_case_members_case_id", table_name="case_members")
    op.drop_table("case_members")
    op.drop_index("ix_cases_status", table_name="cases")
    op.drop_index("ix_cases_department_id", table_name="cases")
    op.drop_table("cases")
