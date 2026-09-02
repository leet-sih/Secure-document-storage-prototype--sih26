"""Create document_share_links table (secure sharing feature).

Revision ID: 009_sharing
Revises: 008_audit_chain_revoke
Create Date: 2026-09-02

Supports three sharing scopes:
  DOCUMENT        — single document (document_id required)
  CASE_DOCUMENTS  — all docs in a case (case_id required, document_id NULL)
  CASE_FULL       — case metadata + members + all docs (case_id required, document_id NULL)

Stores only SHA256(raw_token) — the raw token is shown to the creator once and never
persisted (same principle as password hashing).

Atomic use_count increment via UPDATE ... WHERE use_count < max_uses RETURNING id
ensures race-safety without application-level locking.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "009_sharing"
down_revision = "008_audit_chain_revoke"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_share_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("share_scope", sa.Text(), nullable=False, server_default="DOCUMENT"),
        # DOCUMENT scope: document_id required. CASE_* scopes: NULL.
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=True,
        ),
        # CASE_* scopes: case_id required. DOCUMENT scope: set for context.
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cases.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("token_hash", sa.Text(), nullable=False, unique=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("allowed_email", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_uses", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "revoked_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index("idx_share_case", "document_share_links", ["case_id"])
    op.create_index("idx_share_document", "document_share_links", ["document_id"])
    op.create_index("idx_share_created_by", "document_share_links", ["created_by"])


def downgrade() -> None:
    op.drop_index("idx_share_created_by", table_name="document_share_links")
    op.drop_index("idx_share_document", table_name="document_share_links")
    op.drop_index("idx_share_case", table_name="document_share_links")
    op.drop_table("document_share_links")
