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
from sqlalchemy.orm import make_transient as _make_transient

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
    case_id, file_stream, filename, mime_type, doc_type, uploader_id,
    title=None, tags=None, auto_ocr=False,
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

    # ── Best-effort OCR (encrypt-first guarantee) ─────────────────────────────────────────
    # Document is committed ACTIVE and fully encrypted. auto_ocr triggers extraction inline;
    # any failure only changes ocr_status — it can NEVER fail the upload.
    if auto_ocr:
        try:
            _run_ocr_inline(doc)
        except Exception:
            current_app.logger.exception("OCR failed for document %s", doc.id)

    _decrypt_ocr_fields(doc)
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
    docs = (
        Document.query.filter_by(case_id=case_id, is_deleted=False)
        .order_by(Document.created_at.desc())
        .all()
    )
    for doc in docs:
        _decrypt_ocr_fields(doc)
    return docs


# ──────────────────────────────────────────────────────────────────
# Personal vault (case_id = NULL)
# ──────────────────────────────────────────────────────────────────

def upload_personal_document(
    file_stream, filename, mime_type, doc_type, uploader_id, title=None, tags=None, auto_ocr=False,
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

    if auto_ocr:
        try:
            _run_ocr_inline(doc)
        except Exception:
            current_app.logger.exception("OCR failed for document %s", doc.id)

    _decrypt_ocr_fields(doc)
    return doc


def list_personal_documents(user_id) -> list:
    """RETURNS: the calling user's personal documents (case_id IS NULL), newest first."""
    docs = (
        Document.query.filter(
            Document.uploaded_by == user_id,
            Document.case_id.is_(None),
            Document.is_deleted.is_(False),
        )
        .order_by(Document.created_at.desc())
        .all()
    )
    for doc in docs:
        _decrypt_ocr_fields(doc)
    return docs


# ──────────────────────────────────────────────────────────────────
# OCR — on-demand + approval
# ──────────────────────────────────────────────────────────────────

_OCR_MIMES = {"image/jpeg", "image/png", "image/tiff", "image/bmp", "image/webp", "application/pdf"}

# ── OCR text field encryption ──────────────────────────────────────────────────
# ocr_raw_text and search_text are sensitive legal content — they must never sit
# plaintext in PostgreSQL. Both are encrypted under the document's existing master
# key using HKDF-derived field-specific sub-keys (independent of each other and of
# the chunk keys). The master key never changes per document, so decryption is
# always possible as long as the KMS row exists.
_INFO_OCR_RAW    = b"ocr-raw-text"
_INFO_OCR_SEARCH = b"ocr-search-text"


def _encrypt_ocr_raw(text: str, doc_id) -> str:
    return crypto.encrypt_field(text, kms.get_key(doc_id), _INFO_OCR_RAW)


def _encrypt_ocr_search(text: str, doc_id) -> str:
    return crypto.encrypt_field(text, kms.get_key(doc_id), _INFO_OCR_SEARCH)


def _decrypt_ocr_fields(doc: Document) -> None:
    """Decrypt ocr_raw_text / search_text in-place for HTTP response serialization.

    Calls make_transient() before modifying so SQLAlchemy never tracks the plaintext
    and cannot accidentally flush it back to the database. All column values are
    accessed (and therefore loaded) before detachment so no DetachedInstanceError
    can occur during subsequent serialization.

    If decryption fails (corrupted value, legacy plaintext row that slipped through),
    the field is cleared rather than propagated as garbage.
    """
    if not doc.ocr_raw_text and not doc.search_text:
        return
    # Access both fields BEFORE detachment so any expired lazy-loads complete
    # while the object is still session-attached.
    raw_enc    = doc.ocr_raw_text
    search_enc = doc.search_text
    try:
        master_key = kms.get_key(doc.id)
    except Exception:
        _make_transient(doc)
        doc.ocr_raw_text = None
        doc.search_text  = None
        return
    _make_transient(doc)   # detach — in-place modifications below are untracked
    if raw_enc:
        try:
            doc.ocr_raw_text = crypto.decrypt_field(raw_enc, master_key, _INFO_OCR_RAW)
        except Exception:
            doc.ocr_raw_text = None
    if search_enc:
        try:
            doc.search_text = crypto.decrypt_field(search_enc, master_key, _INFO_OCR_SEARCH)
        except Exception:
            doc.search_text = None
_OCR_AUTO_APPROVE_THRESHOLD = 0.65


def _auto_approve_ocr(doc: Document, raw_text: str) -> None:
    """Format raw OCR text and store it as DONE, skipping the review queue."""
    from app.core.llm_formatter import format_ocr_text
    master_key = kms.get_key(doc.id)
    formatted = format_ocr_text(raw_text, doc.doc_type)
    doc.search_text = crypto.encrypt_field(formatted, master_key, _INFO_OCR_SEARCH)
    doc.ocr_raw_text = None
    doc.ocr_status = "DONE"


def _run_ocr_inline(doc: Document) -> None:
    """Run Tesseract on `doc`.
    Confidence >= 65%: auto-approve — format and store as DONE.
    Confidence < 65%: AWAITING_APPROVAL for manual review.
    FAILED is reserved for engine errors and truly empty results.
    Non-scannable types or born-digital PDFs: NOT_APPLICABLE.
    """
    from app.core import ocr as ocr_module

    if doc.mime_type not in _OCR_MIMES:
        doc.ocr_status = "NOT_APPLICABLE"
        db.session.commit()
        return

    data = b"".join(_verify_and_decrypt(doc))

    if doc.mime_type == "application/pdf" and ocr_module.pdf_has_text_layer(data):
        text = ocr_module.extract_pdf_text_layer(data)
        if text.strip():
            doc.ocr_confidence = 1.0
            doc.ocr_page_count = 1
            _auto_approve_ocr(doc, text.strip())
        else:
            doc.ocr_status = "NOT_APPLICABLE"
        db.session.commit()
        return

    result = ocr_module.extract(data, doc.original_filename or doc.filename)

    doc.ocr_confidence = round(result.confidence, 4)
    doc.ocr_language = result.language
    doc.ocr_page_count = result.page_count or None

    if not result.text:
        doc.ocr_status = "FAILED"
        doc.ocr_detail = result.detail or "OCR produced no readable text"
        db.session.commit()
        return

    if result.confidence >= _OCR_AUTO_APPROVE_THRESHOLD:
        _auto_approve_ocr(doc, result.text)
    else:
        doc.ocr_raw_text = _encrypt_ocr_raw(result.text, doc.id)
        doc.ocr_detail = (
            f"Low confidence: {result.confidence:.0%} — "
            "review carefully before approving"
        )
        doc.ocr_status = "AWAITING_APPROVAL"
    db.session.commit()


def generate_ocr_for_document(document_id: str, user_id: str, force: bool = False) -> Document:
    """Trigger OCR on an existing document. force=True re-runs even if already done/pending."""
    doc = db.session.get(Document, document_id)
    if doc is None or doc.is_deleted or not _can_access(doc, user_id):
        raise APIError(404, "NOT_FOUND", "Document not found")
    if not force and doc.ocr_status in ("AWAITING_APPROVAL", "DONE"):
        raise APIError(409, "CONFLICT", "OCR already complete or awaiting approval")
    if doc.mime_type not in _OCR_MIMES:
        raise APIError(409, "CONFLICT", "File type does not support OCR")

    if force:
        doc.ocr_raw_text = None
        doc.ocr_confidence = None
        doc.ocr_page_count = None
        doc.ocr_detail = None
        doc.search_text = None
        doc.ocr_status = "PENDING"
        db.session.commit()

    _run_ocr_inline(doc)
    result = db.session.get(Document, document_id)
    _decrypt_ocr_fields(result)
    return result


def approve_ocr(document_id: str, user_id: str, action: str) -> Document:
    """Approve (format + store) or dismiss OCR text.

    action='approve': calls LLM formatter, stores result in search_text, clears ocr_raw_text.
    action='dismiss': sets ocr_status=FAILED, clears ocr_raw_text.
    """
    doc = db.session.get(Document, document_id)
    if doc is None or doc.is_deleted or not _can_access(doc, user_id):
        raise APIError(404, "NOT_FOUND", "Document not found")
    if doc.ocr_status != "AWAITING_APPROVAL":
        raise APIError(409, "CONFLICT", "Document is not awaiting OCR approval")

    if action == "dismiss":
        doc.ocr_status = "FAILED"
        doc.ocr_raw_text = None
        doc.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return doc

    # approve: decrypt raw text for LLM, then encrypt the formatted result
    from app.core.llm_formatter import format_ocr_text
    master_key = kms.get_key(doc.id)
    try:
        raw_for_llm = (
            crypto.decrypt_field(doc.ocr_raw_text, master_key, _INFO_OCR_RAW)
            if doc.ocr_raw_text else ""
        )
    except Exception:
        raw_for_llm = ""
    formatted = format_ocr_text(raw_for_llm, doc.doc_type)
    doc.search_text = crypto.encrypt_field(formatted, master_key, _INFO_OCR_SEARCH)
    doc.ocr_status = "DONE"
    doc.ocr_raw_text = None
    doc.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    _decrypt_ocr_fields(doc)
    return doc
