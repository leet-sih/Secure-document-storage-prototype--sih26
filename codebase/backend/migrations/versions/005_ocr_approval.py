"""Add ocr_raw_text column to documents for the approval-gated OCR flow.

Revision ID: 005_ocr_approval
Revises: 004_personal_vault
Create Date: 2026-09-01

ocr_raw_text holds unformatted Tesseract output while the document is in
AWAITING_APPROVAL state. It is cleared (set to NULL) once the user approves
and the LLM-formatted text is moved to search_text.
"""

import sqlalchemy as sa
from alembic import op

revision = "005_ocr_approval"
down_revision = "004_personal_vault"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("ocr_raw_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "ocr_raw_text")
