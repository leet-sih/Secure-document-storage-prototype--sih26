"""departments, users, audit_events for TOTP auth

Revision ID: 001_auth_totp
Revises:
Create Date: 2026-08-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_auth_totp"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("dept_type", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("employee_id", sa.Text(), unique=True),
        sa.Column("phone", sa.Text()),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id"), nullable=False),
        sa.Column("totp_secret", sa.Text()),
        sa.Column("totp_secret_pending", sa.Text()),
        sa.Column("signing_public_key", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_first_login", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("failed_logins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True)),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("password_changed_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "role IN ('SUPER_ADMIN','CASE_OFFICER','INVESTIGATOR','PROSECUTOR','AUDITOR','VIEWER')",
            name="ck_users_role",
        ),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("target_type", sa.Text()),
        sa.Column("target_id", postgresql.UUID(as_uuid=True)),
        sa.Column("case_id", postgresql.UUID(as_uuid=True)),
        sa.Column("ip_address", postgresql.INET()),
        sa.Column("metadata", postgresql.JSONB()),
        sa.Column("prev_hash", sa.Text(), nullable=False),
        sa.Column("this_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("users")
    op.drop_table("departments")
