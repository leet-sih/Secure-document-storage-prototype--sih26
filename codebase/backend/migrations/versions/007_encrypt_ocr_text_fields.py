"""Clear plaintext OCR text fields — rows must be re-scanned after this migration.

Revision ID: 007_encrypt_ocr_text_fields
Revises: 006_ocr_detail
Create Date: 2026-09-02

WHY: ocr_raw_text and search_text were previously stored as plaintext in PostgreSQL.
They are now encrypted at the application layer (AES-256-GCM via the document's master
key) before being written. Encrypting existing rows in a migration would require calling
the KMS + app crypto from Alembic, which is fragile. Clearing them is safe: the original
document bytes are still fully encrypted on disk and can be re-OCR'd at any time.

Rows affected:
  ocr_raw_text IS NOT NULL  → NULL, ocr_status → NOT_APPLICABLE
  search_text  IS NOT NULL  → NULL, ocr_status → NOT_APPLICABLE (was DONE)
  ocr_detail                → cleared for affected rows (detail was about plaintext run)
"""

import sqlalchemy as sa
from alembic import op

revision = "007_encrypt_ocr_text_fields"
down_revision = "006_ocr_detail"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE documents
            SET ocr_raw_text = NULL,
                search_text  = NULL,
                ocr_detail   = NULL,
                ocr_status   = 'NOT_APPLICABLE'
            WHERE ocr_raw_text IS NOT NULL
               OR search_text  IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    # Cannot restore cleared text — downgrade is intentionally a no-op.
    pass
