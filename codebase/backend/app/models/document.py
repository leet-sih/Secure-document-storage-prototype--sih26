"""
Document model — METADATA ONLY. The actual bytes live as encrypted chunks in MinIO.

STORES: filename, mime type, size, chunk count, overall integrity hash, type, status,
soft-delete flags, and (for search/OCR) extracted text + FTS vector. NEVER stores the
document content or its master key.

integrity_hash = SHA256( concat of every chunk's chunk_hash, in order ). Re-checked on
download; any mismatch => 422 INTEGRITY_VIOLATION.

status: UPLOADING -> ACTIVE | FAILED ; DELETED via is_deleted (soft delete keeps chunks
for legal audit).

Full pipeline: ../../feature_plans/chunked_document_storage_plan.md
Search/OCR columns: ../../feature_plans/{search,ocr}_plan.md
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID, ARRAY, TSVECTOR
from app.extensions import db

DOC_TYPES = (
    "FIR", "POLICE_REPORT", "INVESTIGATION_RECORD", "WITNESS_STATEMENT",
    "CHARGE_SHEET", "COURT_FILING", "EVIDENCE_RECORD", "FORENSIC_REPORT",
    "LEGAL_NOTICE", "JUDGMENT", "OTHER",
)
DOC_STATUSES = ("UPLOADING", "ACTIVE", "FAILED", "DELETED")


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = db.Column(UUID(as_uuid=True), db.ForeignKey("cases.id"), nullable=False)

    filename = db.Column(db.Text, nullable=False)          # sanitized
    original_filename = db.Column(db.Text, nullable=False)  # as uploaded
    title = db.Column(db.Text)
    mime_type = db.Column(db.Text, nullable=False)          # verified by magic bytes
    doc_type = db.Column(db.Text, nullable=False)           # one of DOC_TYPES
    file_size_bytes = db.Column(db.BigInteger, nullable=False)
    total_chunks = db.Column(db.Integer, nullable=False)
    integrity_hash = db.Column(db.Text, nullable=False)     # SHA256 of ordered chunk hashes

    status = db.Column(db.Text, nullable=False, default="UPLOADING")
    tags = db.Column(ARRAY(db.Text), default=list)          # lowercase, [a-z0-9-]

    # ── Search / OCR (populated later; NULL for now) ──
    search_text = db.Column(db.Text)                        # extracted plaintext for FTS
    search_vector = db.Column(TSVECTOR)                     # GIN-indexed; set by DB trigger
    ocr_status = db.Column(db.Text, default="NOT_APPLICABLE")
    ocr_confidence = db.Column(db.Float)
    embedding_status = db.Column(db.Text, default="NOT_APPLICABLE")

    uploaded_by = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=False)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    deleted_by = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"))
    deleted_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
