"""
document_service.py — THE core feature: chunked encrypted upload & reconstruction.

This orchestrates core.crypto + core.kms + storage.chunk_store + the documents/
document_chunks tables. Keep ALL raw crypto in core.crypto — this file only orchestrates.

PROTOTYPE NOTE: chunks go to the local filesystem (storage.chunk_store) and master keys to a
local file KMS (core.kms). Same encryption as production — only the storage backend is simpler.

UPLOAD  upload_document(case_id, file_stream, filename, mime_type, doc_type, uploader_id) -> Document
    1. Validate MIME by magic bytes; enforce size limit; reject empty files.
    2. Create Document(status=UPLOADING); generate master key -> kms.store_key.
    3. Loop CHUNK_SIZE pieces: derive key -> encrypt -> SHA256 -> chunk_store.put_chunk ->
       insert DocumentChunk row.
    4. integrity_hash = SHA256(ordered chunk hashes); Document -> ACTIVE.
    5. On ANY failure: chunk_store.delete_document + kms.delete_key, mark FAILED, rollback.
    RETURNS: the ACTIVE Document (metadata only).

DOWNLOAD  download_document(document_id, requesting_user_id) -> (Document, byte_iterator)
    1. Load doc; check case access (else caller 404).
    2. Fetch master key from kms.get_key.
    3. PRE-VERIFY every chunk (SHA256 + GCM + overall integrity_hash) BEFORE yielding a
       single byte. Any mismatch -> raise IntegrityError (blueprint -> 422 + audit).
    4. Only then stream reconstructed plaintext.

reconstruct_bytes(document_id) -> bytes    (helper for preview; same verification)
soft_delete(document_id, actor) -> None    (is_deleted=True; chunks stay for legal audit)
list_documents(case_id, requesting_user_id) -> list

Full pipeline + edge cases: ../../feature_plans/chunked_document_storage_plan.md
"""


class IntegrityError(Exception):
    """Raised when a chunk hash / GCM tag / overall integrity hash fails. -> HTTP 422."""


def upload_document(case_id, file_stream, filename, mime_type, doc_type, uploader_id):
    raise NotImplementedError


def download_document(document_id, requesting_user_id):
    raise NotImplementedError


def reconstruct_bytes(document_id) -> bytes:
    raise NotImplementedError


def soft_delete(document_id, actor) -> None:
    raise NotImplementedError


def list_documents(case_id, requesting_user_id) -> list:
    raise NotImplementedError
