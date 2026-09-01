"""Add signing_private_key_enc to users; create document_signatures

Revision ID: 002_signatures
Revises: 001_auth_totp
Create Date: 2026-09-01

DEPENDS ON: 001_auth_totp (users table), and a `documents` table created by the
            documents feature migration (or db.create_all() in dev).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002_signatures"
down_revision = "001_auth_totp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Private key column on users — AES-256-GCM wrapped, hex(iv || ct+tag)
    op.add_column("users", sa.Column("signing_private_key_enc", sa.Text(), nullable=True))

    op.create_table(
        "document_signatures",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "signer_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("integrity_hash_at_signing", sa.Text(), nullable=False),
        sa.Column("signed_payload_hash", sa.Text(), nullable=False),
        sa.Column("signature_hex", sa.Text(), nullable=False),
        sa.Column("is_valid", sa.Boolean(), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "document_id", "signer_user_id", name="uq_one_sig_per_user_per_doc"
        ),
    )

    op.create_index(
        "ix_document_signatures_document_id",
        "document_signatures",
        ["document_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_document_signatures_document_id", table_name="document_signatures")
    op.drop_table("document_signatures")
    op.drop_column("users", "signing_private_key_enc")
