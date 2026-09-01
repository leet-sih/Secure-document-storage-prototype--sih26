"""Make documents.case_id nullable to support personal vault (user-scoped documents).

Revision ID: 004_personal_vault
Revises: 003_documents
Create Date: 2026-09-01

Personal documents have case_id = NULL; case-scoped documents are unchanged.
Downgrade will fail if any personal documents exist (NULL case_ids cannot be
restored to NOT NULL while NULLs are present).
"""

from alembic import op

revision = "004_personal_vault"
down_revision = "003_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("documents", "case_id", nullable=True)


def downgrade() -> None:
    # Will fail if personal documents (case_id IS NULL) exist.
    op.alter_column("documents", "case_id", nullable=False)
