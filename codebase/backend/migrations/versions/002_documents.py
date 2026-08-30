"""documents + document_chunks (chunked encrypted ingest).

Depends on `users` (001). `case_id` FK requires the `cases` table from case-management.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "002_documents"
down_revision = "001_auth_totp"
branch_labels = None
depends_on = None

DOC_TYPES = (
    "FIR",
    "POLICE_REPORT",
    "INVESTIGATION_RECORD",
    "WITNESS_STATEMENT",
    "CHARGE_SHEET",
    "COURT_FILING",
    "EVIDENCE_RECORD",
    "FORENSIC_REPORT",
    "LEGAL_NOTICE",
    "JUDGMENT",
    "OTHER",
)

DOC_STATUSES = ("UPLOADING", "ACTIVE", "FAILED", "DELETED")


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.Text(), nullable=False),
        sa.Column("title", sa.Text()),
        sa.Column("mime_type", sa.Text(), nullable=False),
        sa.Column("doc_type", sa.Text(), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("total_chunks", sa.Integer(), nullable=False),
        sa.Column("integrity_hash", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="UPLOADING"),
        sa.Column("tags", postgresql.ARRAY(sa.Text()), server_default="{}"),
        sa.Column("search_text", sa.Text()),
        sa.Column("search_vector", postgresql.TSVECTOR()),
        sa.Column("ocr_status", sa.Text(), server_default="NOT_APPLICABLE"),
        sa.Column("ocr_confidence", sa.Float()),
        sa.Column("ocr_language", sa.Text(), server_default="eng+hin"),
        sa.Column("ocr_page_count", sa.Integer()),
        sa.Column("embedding_status", sa.Text(), server_default="NOT_APPLICABLE"),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("doc_type IN (" + ", ".join(repr(t) for t in DOC_TYPES) + ")", name="chk_doc_type"),
        sa.CheckConstraint("status IN (" + ", ".join(repr(s) for s in DOC_STATUSES) + ")", name="chk_status"),
    )
    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("iv_hex", sa.Text(), nullable=False),
        sa.Column("chunk_hash", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk"),
    )
    op.create_index(
        "idx_chunks_document_index",
        "document_chunks",
        ["document_id", "chunk_index"],
    )


def downgrade() -> None:
    op.drop_index("idx_chunks_document_index", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_table("documents")
