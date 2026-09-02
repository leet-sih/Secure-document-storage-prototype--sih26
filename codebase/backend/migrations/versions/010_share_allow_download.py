"""Add allow_download column to document_share_links.

Revision ID: 010_share_allow_download
Revises: 009_sharing
Create Date: 2026-09-02

allow_download=True (default) preserves existing behaviour — recipients can download.
allow_download=False restricts recipients to server-side preview only; the raw file
bytes are never streamed to the browser.
"""

import sqlalchemy as sa
from alembic import op


revision = "010_share_allow_download"
down_revision = "009_sharing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "document_share_links",
        sa.Column(
            "allow_download",
            sa.Boolean(),
            nullable=False,
            server_default="true",
        ),
    )


def downgrade() -> None:
    op.drop_column("document_share_links", "allow_download")
