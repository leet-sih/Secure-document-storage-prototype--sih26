"""
chunk_store.py — where encrypted chunks physically live.  (PROTOTYPE: local filesystem)

RESPONSIBILITY:
    put/get/delete the encrypted chunk objects. Everything stored here is ALWAYS ciphertext
    (AES-256-GCM, tag included) — never plaintext.

PROTOTYPE IMPLEMENTATION:
    Chunks are plain files under CHUNK_STORAGE_DIR (default ./data/chunks), one folder per
    document:   ./data/chunks/{document_id}/chunk_000000
    Production swaps this module for MinIO/S3 object storage — same function signatures, so
    document_service never changes. (See docs/ARCHITECTURE.md "Future / production".)

FUNCTIONS:
    chunk_path(document_id, index) -> str   # helper: full path for one chunk
    put_chunk(document_id, index, data: bytes) -> str   # writes file, RETURNS its storage key
    get_chunk(storage_key) -> bytes
    delete_document(document_id) -> None     # remove the whole document folder

Reference: chunked_document_storage_plan.md + docs/EDGE_CASES.md sections 1 & 5.
"""


def chunk_path(document_id: str, index: int) -> str:
    """RETURNS: CHUNK_STORAGE_DIR/{document_id}/chunk_{index:06d}. TODO (read dir from config)."""
    raise NotImplementedError


def put_chunk(document_id: str, index: int, data: bytes) -> str:
    """Write one ciphertext chunk to disk (create the doc folder if needed).
    RETURNS: the storage key to save in DocumentChunk.storage_key. TODO."""
    raise NotImplementedError


def get_chunk(storage_key: str) -> bytes:
    """Read one ciphertext chunk back. Raise FileNotFoundError if missing. TODO."""
    raise NotImplementedError


def delete_document(document_id: str) -> None:
    """Delete the whole {document_id}/ chunk folder (cleanup / hard delete). Idempotent. TODO."""
    raise NotImplementedError
