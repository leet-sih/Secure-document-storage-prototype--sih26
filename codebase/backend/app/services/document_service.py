"""
document_service.py — THE core feature: chunked encrypted upload & reconstruction.

This orchestrates core.crypto + core.kms + storage.chunk_store + the documents/
document_chunks/document_keys tables. Keep ALL raw crypto in core.crypto — this file only
orchestrates.

PROTOTYPE NOTE: chunks go to the local filesystem (storage.chunk_store) and the master key is
stored WRAPPED in Postgres (core.kms). Same encryption as production — only the storage
backends are simpler.

ENCRYPT-FIRST, OCR-BEST-EFFORT (the guarantee):
    Encryption operates on the RAW BYTES of the file, so it is identical for every allowed
    type (text, PDF, image, docx/xlsx, video, audio). The whole file is ALWAYS encrypted at
    rest regardless of type. OCR/text-extraction is a separate, best-effort layer that runs
    AFTER the ACTIVE document is committed and can NEVER fail the upload or affect encryption
    (see the hook at the end of upload_document + feature_plans/ocr_plan.md).

UPLOAD  upload_document(...) -> Document
    1. Validate case access + open state; MIME by magic bytes; reject empty files.
    2. Create Document(status=UPLOADING); generate master key -> kms.store_key (wrapped, same txn).
    3. Loop CHUNK_SIZE pieces: derive key -> encrypt -> SHA256 -> chunk_store.put_chunk ->
       insert DocumentChunk row.
    4. integrity_hash = SHA256(ordered chunk hashes); Document -> ACTIVE; commit (atomic).
    5. On ANY failure: rollback DB (undoes doc + chunks + wrapped key) + delete written chunks.

DOWNLOAD  download_document(document_id, requesting_user_id) -> (Document, byte_iterator)
    Loads doc; case access (else 404); PRE-VERIFY every chunk (SHA256 + GCM + overall
    integrity_hash) BEFORE yielding a single byte; then stream reconstructed plaintext.

reconstruct_bytes(document_id) -> bytes    (server-side plaintext hook for OCR/preview; verified)
soft_delete(document_id, actor) -> None    (is_deleted=True; chunks + key stay for legal audit)
list_documents(case_id, requesting_user_id) -> list

Full pipeline + edge cases: feature_plans/specs/document_encryption_keystore_spec.md
"""

import os
import re
import secrets
from datetime import datetime, timezone

from cryptography.exceptions import InvalidTag
from flask import current_app

from app.core import crypto, kms
from app.core.audit_events import AuditEventType
from app.core.errors import APIError
from app.extensions import db
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services import case_service
from app.services.audit_service import audit_service
from app.storage import chunk_store

# File types accepted by the vault. Verified by MAGIC BYTES, never the client header/extension.
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",   # .docx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",         # .xlsx
    "image/jpeg",
    "image/png",
    "image/tiff",
    "video/mp4",          # forensic video evidence
    "audio/mpeg",         # recorded statements
    "audio/wav",
    "text/plain",         # plain-text notes / statements
}

_MAGIC_SNIFF_BYTES = 2048


class IntegrityError(Exception):
    """Raised when a chunk hash / GCM tag / overall integrity hash fails. -> HTTP 422."""


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────

def _sanitize_filename(name: str) -> str:
    """Strip path components; keep only [A-Za-z0-9._-]; cap at 255 chars."""
    base = os.path.basename(name or "")
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", base).strip("._")
    return (cleaned or "file")[:255]


_MAGIC_TABLE: list[tuple[bytes, int, str]] = [
    (b"%PDF",               0,  "application/pdf"),
    (b"\xff\xd8\xff",       0,  "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", 0,  "image/png"),
    (b"II*\x00",            0,  "image/tiff"),
    (b"MM\x00*",            0,  "image/tiff"),
    (b"RIFF",               0,  "audio/wav"),
    (b"ID3",                0,  "audio/mpeg"),
    (b"\xff\xfb",           0,  "audio/mpeg"),
    (b"\xff\xf3",           0,  "audio/mpeg"),
    (b"\xff\xf2",           0,  "audio/mpeg"),
    (b"PK\x03\x04",         0,  "application/zip"),   # DOCX/XLSX/ZIP — refined below
]

_EXT_OVERRIDES: dict[str, str] = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".mp4":  "video/mp4",
}


def _detect_mime(head: bytes, filename: str = "") -> str:
    """Detect MIME type from the first bytes.  Tries python-magic (libmagic) first; falls back
    to a built-in signature table if libmagic is unavailable (common on Windows dev boxes)."""
    try:
        import magic as _magic  # python-magic (requires libmagic DLL on Windows)
        detected = _magic.from_buffer(head, mime=True)
        # Libmagic detects DOCX/XLSX as application/zip — refine with filename extension.
        if detected == "application/zip":
            ext = os.path.splitext(filename.lower())[1]
            if ext in _EXT_OVERRIDES:
                return _EXT_OVERRIDES[ext]
        return detected
    except Exception:
        pass  # libmagic unavailable — fall through to signature table

    # Pure-Python fallback: signature table
    ext = os.path.splitext(filename.lower())[1]
    if ext in _EXT_OVERRIDES:
        # Office formats are ZIP-based; check the ZIP magic first.
        if head[:4] == b"PK\x03\x04":
            return _EXT_OVERRIDES[ext]
    if ext == ".mp4" and len(head) >= 8 and head[4:8] in (b"ftyp", b"moov", b"mdat"):
        return "video/mp4"
    for sig, offset, mime in _MAGIC_TABLE:
        if head[offset: offset + len(sig)] == sig:
            return mime
    return "application/octet-stream"  # unknown — upload_document will reject this


def _verify_and_decrypt(doc: Document) -> list[bytes]:
    """Fetch, integrity-check and decrypt every chunk of `doc`, IN ORDER.
    Verifies SHA256(ciphertext)==chunk_hash, the GCM auth tag, and the overall integrity_hash.
    Raises IntegrityError on any mismatch (before returning any plaintext).
    RETURNS: ordered list of plaintext chunk bytes. Buffers the whole document in RAM
    (prototype choice — see spec §7)."""
    chunks = (
        DocumentChunk.query.filter_by(document_id=doc.id)
        .order_by(DocumentChunk.chunk_index)
        .all()
    )
    if len(chunks) != doc.total_chunks:
        raise IntegrityError("chunk count does not match document.total_chunks")

    try:
        master_key = kms.get_key(doc.id)
    except FileNotFoundError:
        # Never serve an undecryptable file. Distinct from tampering -> 503, not 422.
        raise APIError(503, "INTERNAL_ERROR", "Key material unavailable")

    parts: list[bytes] = []
    ordered_hashes: list[str] = []
    for chunk in chunks:
        try:
            ciphertext = chunk_store.get_chunk(chunk.storage_key)
        except FileNotFoundError:
            raise IntegrityError(f"chunk {chunk.chunk_index} missing from chunk store")

        if crypto.sha256_hex(ciphertext) != chunk.chunk_hash:
            raise IntegrityError(f"chunk {chunk.chunk_index} ciphertext hash mismatch")
        ordered_hashes.append(chunk.chunk_hash)

        chunk_key = crypto.derive_chunk_key(master_key, str(doc.id), chunk.chunk_index)
        try:
            parts.append(
                crypto.decrypt_chunk(chunk_key, bytes.fromhex(chunk.iv_hex), ciphertext)
            )
        except InvalidTag:
            raise IntegrityError(f"chunk {chunk.chunk_index} GCM auth tag invalid")

    if crypto.compute_integrity_hash(ordered_hashes) != doc.integrity_hash:
        raise IntegrityError("document-level integrity hash mismatch")

    return parts


def _actor_id(actor) -> str:
    """Accept either a User object or a raw id."""
    return str(actor.id) if hasattr(actor, "id") else str(actor)


# ──────────────────────────────────────────────────────────────────
# Upload
# ──────────────────────────────────────────────────────────────────

def upload_document(
    case_id, file_stream, filename, mime_type, doc_type, uploader_id, title=None, tags=None
):
    """Chunk, encrypt, and store one uploaded file. RETURNS: the ACTIVE Document (metadata only).
    `file_stream` must be seekable (werkzeug FileStorage.stream is)."""
    # 1. Case must be visible to the uploader and open for writes.
    case = case_service.get_case_for_user(case_id, uploader_id)  # aborts/raises 404 if not member
    if case.status in ("CLOSED", "ARCHIVED"):
        raise APIError(409, "CONFLICT", "Case is not open for uploads")

    # 2. MIME by magic bytes (reject empty + disallowed types before writing anything).
    head = file_stream.read(_MAGIC_SNIFF_BYTES)
    if not head:
        raise APIError(400, "VALIDATION_ERROR", "Empty file")
    detected = _detect_mime(head, filename or "")
    if detected not in ALLOWED_MIME_TYPES:
        raise APIError(400, "UNSUPPORTED_MEDIA_TYPE", f"File type not permitted: {detected}")
    file_stream.seek(0)

    safe_name = _sanitize_filename(filename)
    chunk_size = current_app.config["CHUNK_SIZE_BYTES"]
    max_size = current_app.config["MAX_CONTENT_LENGTH"]

    # 3. Create the metadata row (UPLOADING) and get its id.
    doc = Document(
        case_id=case_id,
        filename=safe_name,
        original_filename=filename or safe_name,
        title=title,
        mime_type=detected,
        doc_type=doc_type,
        file_size_bytes=0,
        total_chunks=0,
        integrity_hash="",
        status="UPLOADING",
        tags=tags or [],
        uploaded_by=uploader_id,
        ocr_status="NOT_APPLICABLE",
    )
    db.session.add(doc)
    db.session.flush()  # assigns doc.id without committing

    written_keys: list[str] = []
    chunk_hashes: list[str] = []
    total_bytes = 0
    index = 0
    try:
        master_key = crypto.generate_master_key()
        kms.store_key(doc.id, master_key)  # wrapped row, same transaction

        while True:
            plaintext = file_stream.read(chunk_size)
            if not plaintext:
                break
            total_bytes += len(plaintext)
            if total_bytes > max_size:
                raise APIError(413, "PAYLOAD_TOO_LARGE", "File exceeds the size limit")

            chunk_key = crypto.derive_chunk_key(master_key, str(doc.id), index)
            iv, ciphertext = crypto.encrypt_chunk(chunk_key, plaintext)
            chunk_hash = crypto.sha256_hex(ciphertext)
            storage_key = secrets.token_hex(16)  # opaque, structureless

            chunk_store.put_chunk(storage_key, ciphertext)  # storage is NOT transactional
            written_keys.append(storage_key)
            chunk_hashes.append(chunk_hash)

            db.session.add(
                DocumentChunk(
                    document_id=doc.id,
                    chunk_index=index,
                    storage_key=storage_key,
                    iv_hex=iv.hex(),
                    chunk_hash=chunk_hash,
                    size_bytes=len(plaintext),
                )
            )
            index += 1

        if index == 0:  # whitespace/edge: file had a magic header but no readable bytes
            raise APIError(400, "VALIDATION_ERROR", "Empty file")

        doc.total_chunks = index
        doc.file_size_bytes = total_bytes
        doc.integrity_hash = crypto.compute_integrity_hash(chunk_hashes)
        doc.status = "ACTIVE"
        doc.updated_at = datetime.now(timezone.utc)
        db.session.commit()  # ATOMIC: documents + document_chunks + document_keys
    except Exception:
        db.session.rollback()  # undoes doc + chunk rows + wrapped key
        if written_keys:
            chunk_store.delete_chunks(written_keys)  # clean up the non-transactional writes
        raise

    # NOTE: the DOCUMENT_UPLOADED audit event is recorded by the BLUEPRINT layer after this
    # returns (house rule — see services/__init__.py). Only security events (INTEGRITY_VIOLATION)
    # are recorded inside this service, where they are detected.

    # ── Best-effort OCR (encrypt-first guarantee) ──────────────────────────────────────────
    # The document is already committed ACTIVE and fully encrypted above. OCR runs on the
    # in-memory plaintext to populate search_text; if it is unsure/unavailable/fails, the
    # document stays ACTIVE + encrypted and only ocr_status changes. OCR must NEVER fail the
    # upload. The engine lives in core.ocr (feature_plans/ocr_plan.md) — wire it in here:
    #     try:
    #         from app.core import ocr
    #         ocr.run_ocr_inline(doc)
    #     except Exception:
    #         current_app.logger.exception("OCR failed for document %s", doc.id)

    return doc


# ──────────────────────────────────────────────────────────────────
# Download / reconstruction
# ──────────────────────────────────────────────────────────────────

def _can_access(doc: Document, user_id: str) -> bool:
    """True if the user may read this document.
    Personal docs (case_id=None): owner only. Case docs: case membership."""
    if doc.case_id is None:
        return str(doc.uploaded_by) == str(user_id)
    return case_service.user_has_access(user_id, doc.case_id)


def download_document(document_id, requesting_user_id):
    """RETURNS: (Document, generator of plaintext byte chunks). Pre-verifies integrity before
    yielding anything. Raises IntegrityError (-> 422) on tamper, APIError(404) if not visible."""
    doc = db.session.get(Document, document_id)
    if doc is None or doc.is_deleted or not _can_access(doc, requesting_user_id):
        raise APIError(404, "NOT_FOUND", "Document not found")

    try:
        parts = _verify_and_decrypt(doc)
    except IntegrityError:
        # Security event — recorded here (in the service) where tampering is detected, per the
        # exception in the services/__init__.py audit rule. The blueprint records the normal
        # DOCUMENT_DOWNLOADED event only on success.
        audit_service.record(
            AuditEventType.INTEGRITY_VIOLATION.value,
            actor_user_id=requesting_user_id,
            target_type="document",
            target_id=doc.id,
            case_id=doc.case_id,
        )
        raise

    def generate():
        for part in parts:
            yield part

    return doc, generate()


def reconstruct_bytes(document_id) -> bytes:
    """Server-side plaintext hook (for OCR/preview/search). Same integrity verification as
    download, but NO case-access check — callers are internal, trusted server code.
    RETURNS: the full decrypted document bytes."""
    doc = db.session.get(Document, document_id)
    if doc is None or doc.is_deleted:
        raise APIError(404, "NOT_FOUND", "Document not found")
    return b"".join(_verify_and_decrypt(doc))


# ──────────────────────────────────────────────────────────────────
# Delete / list
# ──────────────────────────────────────────────────────────────────

def soft_delete(document_id, actor) -> Document:
    """Mark the document deleted (is_deleted=True). Chunks + wrapped key REMAIN for legal
    retention — no physical deletion here. RETURNS the deleted Document so the blueprint can
    record DOCUMENT_DELETED (house rule — audit in the blueprint layer)."""
    actor_id = _actor_id(actor)
    doc = db.session.get(Document, document_id)
    if doc is None or doc.is_deleted or not _can_access(doc, actor_id):
        raise APIError(404, "NOT_FOUND", "Document not found")

    doc.is_deleted = True
    doc.deleted_by = actor_id
    doc.deleted_at = datetime.now(timezone.utc)
    doc.status = "DELETED"
    doc.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return doc


def list_documents(case_id, requesting_user_id) -> list:
    """RETURNS: non-deleted Documents in the case, newest first. Aborts 404 if the case is not
    visible to the requester."""
    case_service.get_case_for_user(case_id, requesting_user_id)  # 404 if not a member
    return (
        Document.query.filter_by(case_id=case_id, is_deleted=False)
        .order_by(Document.created_at.desc())
        .all()
    )


# ──────────────────────────────────────────────────────────────────
# Personal vault (case_id = NULL)
# ──────────────────────────────────────────────────────────────────

def upload_personal_document(
    file_stream, filename, mime_type, doc_type, uploader_id, title=None, tags=None
):
    """Same chunked-AES pipeline as upload_document but with case_id=None (personal vault).
    RETURNS: the ACTIVE Document."""
    head = file_stream.read(_MAGIC_SNIFF_BYTES)
    if not head:
        raise APIError(400, "VALIDATION_ERROR", "Empty file")
    detected = _detect_mime(head, filename or "")
    if detected not in ALLOWED_MIME_TYPES:
        raise APIError(400, "UNSUPPORTED_MEDIA_TYPE", f"File type not permitted: {detected}")
    file_stream.seek(0)

    safe_name = _sanitize_filename(filename)
    chunk_size = current_app.config["CHUNK_SIZE_BYTES"]
    max_size = current_app.config["MAX_CONTENT_LENGTH"]

    doc = Document(
        case_id=None,
        filename=safe_name,
        original_filename=filename or safe_name,
        title=title,
        mime_type=detected,
        doc_type=doc_type,
        file_size_bytes=0,
        total_chunks=0,
        integrity_hash="",
        status="UPLOADING",
        tags=tags or [],
        uploaded_by=uploader_id,
        ocr_status="NOT_APPLICABLE",
    )
    db.session.add(doc)
    db.session.flush()

    written_keys: list[str] = []
    chunk_hashes: list[str] = []
    total_bytes = 0
    index = 0
    try:
        master_key = crypto.generate_master_key()
        kms.store_key(doc.id, master_key)

        while True:
            plaintext = file_stream.read(chunk_size)
            if not plaintext:
                break
            total_bytes += len(plaintext)
            if total_bytes > max_size:
                raise APIError(413, "PAYLOAD_TOO_LARGE", "File exceeds the size limit")

            chunk_key = crypto.derive_chunk_key(master_key, str(doc.id), index)
            iv, ciphertext = crypto.encrypt_chunk(chunk_key, plaintext)
            chunk_hash = crypto.sha256_hex(ciphertext)
            storage_key = secrets.token_hex(16)

            chunk_store.put_chunk(storage_key, ciphertext)
            written_keys.append(storage_key)
            chunk_hashes.append(chunk_hash)

            db.session.add(
                DocumentChunk(
                    document_id=doc.id,
                    chunk_index=index,
                    storage_key=storage_key,
                    iv_hex=iv.hex(),
                    chunk_hash=chunk_hash,
                    size_bytes=len(plaintext),
                )
            )
            index += 1

        if index == 0:
            raise APIError(400, "VALIDATION_ERROR", "Empty file")

        doc.total_chunks = index
        doc.file_size_bytes = total_bytes
        doc.integrity_hash = crypto.compute_integrity_hash(chunk_hashes)
        doc.status = "ACTIVE"
        doc.updated_at = datetime.now(timezone.utc)
        db.session.commit()
    except Exception:
        db.session.rollback()
        if written_keys:
            chunk_store.delete_chunks(written_keys)
        raise

    return doc


def list_personal_documents(user_id) -> list:
    """RETURNS: the calling user's personal documents (case_id IS NULL), newest first."""
    return (
        Document.query.filter(
            Document.uploaded_by == user_id,
            Document.case_id.is_(None),
            Document.is_deleted.is_(False),
        )
        .order_by(Document.created_at.desc())
        .all()
    )
