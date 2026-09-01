"""Create document_signatures table and add signing_private_key_enc to users

Revision ID: 003_signature_comment
Revises: 007_encrypt_ocr_text_fields
Create Date: 2026-09-02

Context: The feat/ocr-integration branch (merged first) went from 001_auth_totp
through its own 003-007 chain, adding signing_public_key to users but never
applying the original 002_signatures migration. This migration bridges that gap:
it adds signing_private_key_enc (missing from 002_signatures) and creates the
document_signatures table, plus the comment column from day one.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003_signature_comment"
down_revision = "007_encrypt_ocr_text_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Private key column on users (encrypted Ed25519 private key, AES-256-GCM wrapped)
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
        sa.Column("comment", sa.Text(), nullable=True),
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
