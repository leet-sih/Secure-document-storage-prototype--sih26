"""Add ocr_detail column to documents for human-readable failure reason.

Revision ID: 006_ocr_detail
Revises: 005_ocr_approval
Create Date: 2026-09-01

Stores why OCR failed — e.g. "Confidence 23% is below the 60% threshold"
or "tesseract binary not installed on this server". NULL on success/pending.
"""

import sqlalchemy as sa
from alembic import op

revision = "006_ocr_detail"
down_revision = "005_ocr_approval"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("ocr_detail", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "ocr_detail")
