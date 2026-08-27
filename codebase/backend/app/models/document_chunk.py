"""
DocumentChunk model — crypto metadata for one encrypted chunk.
The ciphertext itself lives in the chunk store (local disk in prototype; MinIO in production),
NOT in this table.

OPAQUE STORAGE KEYS:
    storage_key is a random opaque identifier (secrets.token_hex(16)), generated in
    document_service.py before calling chunk_store.put_chunk(). It has no structure
    that reveals document boundaries, chunk index, or ordering. All ordering information
    lives only in this table (chunk_index column). A listing of the chunk store directory
    therefore reveals nothing useful to an attacker.

    Old scheme (do not use): "{doc_id}/chunk_{index:06d}"  — leaked structure
    New scheme: "a8f13c4d9e2b7f1a" (flat namespace, opaque)  — no leakage

STORES per chunk:
    chunk_index  — ordering (DB only; not in the filename)
    storage_key  — opaque key used to fetch/delete from chunk_store
    iv_hex       — 12-byte AES-GCM nonce, hex-encoded (24 chars)
    chunk_hash   — SHA256 of the stored ciphertext (including GCM tag)
    size_bytes   — plaintext size of this chunk

NO auth_tag column: Python's AESGCM appends the 16-byte GCM tag to the ciphertext,
so it is inside the stored object and is covered by chunk_hash.

Retrieval: fetch by document_id ordered by chunk_index, verify SHA256(ciphertext)==chunk_hash,
then AES-256-GCM decrypt with per-chunk key = HKDF(master_key, salt=doc_id, info=chunk-i).

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
    storage_key = db.Column(db.Text, nullable=False)   # opaque random key (16-byte hex)
    iv_hex = db.Column(db.Text, nullable=False)        # 12-byte nonce, hex (24 chars)
    chunk_hash = db.Column(db.Text, nullable=False)    # SHA256(ciphertext incl. GCM tag)
    size_bytes = db.Column(db.Integer, nullable=False)  # plaintext size
