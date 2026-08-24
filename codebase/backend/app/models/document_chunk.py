"""
DocumentChunk model — crypto metadata for one encrypted chunk. The ciphertext itself
lives in MinIO, NOT here.

STORES per chunk: ordering index, the storage key (local file path in the prototype; an
object key later), the 12-byte IV (hex), and the SHA256 of the stored ciphertext. There is
NO auth_tag column — Python's AESGCM appends the 16-byte GCM tag to the ciphertext, so it is
inside the stored object and is covered by chunk_hash.

Retrieval: fetch by document_id ordered by chunk_index, verify SHA256(ciphertext)==chunk_hash,
then AES-256-GCM decrypt with the per-chunk key = HKDF(master_key, salt=doc_id, info=chunk-i).

Full design: ../../feature_plans/chunked_document_storage_plan.md
"""

import uuid

from sqlalchemy.dialects.postgresql import UUID
from app.extensions import db


class DocumentChunk(db.Model):
    __tablename__ = "document_chunks"
    __table_args__ = (db.UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk"),)

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = db.Column(UUID(as_uuid=True), db.ForeignKey("documents.id"), nullable=False)
    chunk_index = db.Column(db.Integer, nullable=False)
    storage_key = db.Column(db.Text, nullable=False)  # {doc_id}/chunk_{index:06d} (local file now, object key later)
    iv_hex = db.Column(db.Text, nullable=False)       # 12-byte nonce, hex (24 chars)
    chunk_hash = db.Column(db.Text, nullable=False)   # SHA256(ciphertext incl. GCM tag)
    size_bytes = db.Column(db.Integer, nullable=False)  # plaintext size
