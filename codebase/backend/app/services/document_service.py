"""
document_service.py — THE core feature: chunked encrypted upload & reconstruction.

This orchestrates core.crypto + core.kms + storage.chunk_store + the documents/
document_chunks tables. Keep ALL raw crypto in core.crypto — this file only orchestrates.

PROTOTYPE NOTE: chunks go to the local filesystem (storage.chunk_store) and master keys to a
local file KMS (core.kms). Same encryption as production — only the storage backend is simpler.

UPLOAD   upload_document(...)
PREVIEW  get_document_for_user + preview_document (reconstruct in RAM, PNG/text JSON)
DOWNLOAD / list / soft_delete — not this branch.

Full pipeline + edge cases: ../../feature_plans/chunked_document_storage_plan.md
"""

from __future__ import annotations

import base64
import io
import os
import re
import secrets
from typing import BinaryIO
from uuid import UUID, uuid4

from cryptography.exceptions import InvalidTag
from flask import current_app

from app.core import kms
from app.core.crypto import (
    compute_integrity_hash,
    decrypt_chunk,
    derive_chunk_key,
    encrypt_chunk,
    generate_master_key,
    sha256_hex,
)
from app.core.errors import APIError
from app.extensions import db
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services import case_service
from app.storage import chunk_store

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "video/mp4",
    "audio/wav",
}

PREVIEWABLE_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "text/plain",
}

MAX_PREVIEW_PAGES = 20
MAX_PREVIEW_TEXT_CHARS = 512 * 1024


class IntegrityError(Exception):
    """Raised when a chunk hash / GCM tag / overall integrity hash fails. -> HTTP 422."""


def sanitize_filename(filename: str) -> str:
    """Strip path components; keep [a-zA-Z0-9._-]; max 255 chars."""
    base = os.path.basename(filename.replace("\\", "/"))
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "_", base)[:255]
    return cleaned or "unnamed"


def _max_file_bytes() -> int:
    return int(current_app.config["MAX_FILE_SIZE_MB"]) * 1024 * 1024


def _chunk_size() -> int:
    return int(current_app.config["CHUNK_SIZE_BYTES"])


def _detect_mime_signatures(header: bytes) -> str:
    """Magic-byte sniff when libmagic is unavailable (Windows without libmagic)."""
    if header.startswith(b"%PDF"):
        return "application/pdf"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"II*\x00") or header.startswith(b"MM\x00*"):
        return "image/tiff"
    if len(header) >= 12 and header[4:8] == b"ftyp":
        return "video/mp4"
    if header.startswith(b"RIFF") and header[8:12] == b"WAVE":
        return "audio/wav"
    if header.startswith(b"PK"):
        if b"word/" in header or b"word\\" in header:
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if b"xl/" in header or b"xl\\" in header:
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return "application/zip"
    if header.startswith(b"MZ"):
        return "application/x-dosexec"
    return "application/octet-stream"


def detect_mime_from_header(header: bytes) -> str:
    """MIME from magic bytes — python-magic when present, else signature table."""
    try:
        import magic

        return magic.from_buffer(header, mime=True)
    except Exception:
        return _detect_mime_signatures(header)


def _sniff_mime(file_stream: BinaryIO) -> str:
    header = file_stream.read(2048)
    if hasattr(file_stream, "seek"):
        file_stream.seek(0)
    if not header:
        raise APIError(400, "VALIDATION_ERROR", "Empty file is not permitted")
    detected = detect_mime_from_header(header)
    if detected not in ALLOWED_MIME_TYPES:
        raise APIError(400, "VALIDATION_ERROR", "File type not permitted")
    return detected


def _seekable_size(file_stream: BinaryIO) -> int | None:
    if not hasattr(file_stream, "seek") or not hasattr(file_stream, "tell"):
        return None
    try:
        pos = file_stream.tell()
        file_stream.seek(0, os.SEEK_END)
        size = file_stream.tell()
        file_stream.seek(pos)
        return size
    except Exception:
        return None


def _cleanup_failed_upload(storage_keys: list[str], document_id: UUID | None) -> None:
    if storage_keys:
        chunk_store.delete_chunks(storage_keys)
    if document_id is not None:
        kms.delete_key(str(document_id))


def upload_document(
    case_id,
    file_stream,
    filename,
    mime_type,
    doc_type,
    uploader_id,
    title=None,
    tags=None,
):
    case = case_service.get_case_for_user(str(case_id), str(uploader_id))
    if case is None:
        raise APIError(404, "NOT_FOUND", "Not found")
    if getattr(case, "status", None) in ("CLOSED", "ARCHIVED"):
        raise APIError(409, "CONFLICT", "Case is closed — no new documents allowed")

    detected_mime = _sniff_mime(file_stream)
    if mime_type and mime_type not in ALLOWED_MIME_TYPES:
        # Client header is ignored for allowlisting; sniffed type already checked.
        pass
    mime_type = detected_mime

    known_size = _seekable_size(file_stream)
    if known_size is not None:
        if known_size < 1:
            raise APIError(400, "VALIDATION_ERROR", "Empty file is not permitted")
        if known_size > _max_file_bytes():
            raise APIError(400, "VALIDATION_ERROR", "File exceeds maximum size")

    original = filename or "unnamed"
    safe_name = sanitize_filename(original)
    master_key: bytes | None = None
    storage_keys: list[str] = []
    document: Document | None = None

    try:
        document = Document(
            case_id=case_id if isinstance(case_id, UUID) else UUID(str(case_id)),
            filename=safe_name,
            original_filename=original[:1024],
            title=title,
            mime_type=mime_type,
            doc_type=doc_type,
            file_size_bytes=0,
            total_chunks=0,
            integrity_hash="",
            status="UPLOADING",
            tags=list(tags or []),
            uploaded_by=uploader_id if isinstance(uploader_id, UUID) else UUID(str(uploader_id)),
        )
        db.session.add(document)
        db.session.flush()
        if document.id is None:
            document.id = uuid4()

        master_key = generate_master_key()
        try:
            kms.store_key(str(document.id), master_key)
        except APIError:
            raise
        except Exception as exc:
            db.session.rollback()
            raise APIError(503, "KMS_UNAVAILABLE", "Key store unavailable") from exc

        chunk_index = 0
        chunk_hashes: list[str] = []
        total_bytes = 0
        size_limit = _max_file_bytes()
        piece = _chunk_size()

        while True:
            chunk_data = file_stream.read(piece)
            if not chunk_data:
                break
            total_bytes += len(chunk_data)
            if total_bytes > size_limit:
                raise APIError(400, "VALIDATION_ERROR", "File exceeds maximum size")

            storage_key = secrets.token_hex(16)
            chunk_key = derive_chunk_key(master_key, str(document.id), chunk_index)
            iv, ciphertext = encrypt_chunk(chunk_key, chunk_data)
            chunk_hash = sha256_hex(ciphertext)
            chunk_store.put_chunk(storage_key, ciphertext)
            storage_keys.append(storage_key)

            db.session.add(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=chunk_index,
                    storage_key=storage_key,
                    iv_hex=iv.hex(),
                    chunk_hash=chunk_hash,
                    size_bytes=len(chunk_data),
                )
            )
            chunk_hashes.append(chunk_hash)
            chunk_index += 1

        if total_bytes < 1:
            raise APIError(400, "VALIDATION_ERROR", "Empty file is not permitted")

        document.total_chunks = chunk_index
        document.file_size_bytes = total_bytes
        document.integrity_hash = compute_integrity_hash(chunk_hashes)
        document.status = "ACTIVE"
        db.session.commit()
        return document
    except APIError:
        _cleanup_failed_upload(storage_keys, document.id if document is not None else None)
        db.session.rollback()
        raise
    except Exception as exc:
        _cleanup_failed_upload(storage_keys, document.id if document is not None else None)
        db.session.rollback()
        raise APIError(500, "INTERNAL_ERROR", "Upload failed") from exc
    finally:
        if master_key is not None:
            # Do not leave the master key in locals longer than needed.
            master_key = None


def _as_uuid(value) -> UUID:
    try:
        return value if isinstance(value, UUID) else UUID(str(value))
    except (ValueError, TypeError) as exc:
        raise APIError(404, "NOT_FOUND", "Not found") from exc


def _integrity_fail(message: str) -> None:
    raise APIError(422, "INTEGRITY_VIOLATION", message)


def get_document_for_user(document_id, requesting_user_id) -> Document:
    """ACTIVE, not deleted, caller can access the parent case. Else 404."""
    did = _as_uuid(document_id)
    document = db.session.get(Document, did)
    if document is None or document.is_deleted or document.status != "ACTIVE":
        raise APIError(404, "NOT_FOUND", "Not found")
    case = case_service.get_case_for_user(str(document.case_id), str(requesting_user_id))
    if case is None:
        raise APIError(404, "NOT_FOUND", "Not found")
    return document


def _reconstruct_verified(document: Document) -> bytes:
    """Decrypt all chunks in RAM after full hash/GCM/integrity checks. Never writes plaintext."""
    chunks = (
        DocumentChunk.query.filter_by(document_id=document.id)
        .order_by(DocumentChunk.chunk_index.asc())
        .all()
    )
    if len(chunks) != document.total_chunks:
        _integrity_fail("Document is incomplete — chunks missing")

    try:
        master_key = kms.get_key(str(document.id))
    except FileNotFoundError as exc:
        raise APIError(503, "KMS_UNAVAILABLE", "Key store unavailable") from exc
    except Exception as exc:
        raise APIError(503, "KMS_UNAVAILABLE", "Key store unavailable") from exc

    running_hashes: list[str] = []
    pieces: list[bytes] = []
    try:
        for expected_index, chunk in enumerate(chunks):
            if chunk.chunk_index != expected_index:
                _integrity_fail("Chunk order is inconsistent")
            try:
                ciphertext = chunk_store.get_chunk(chunk.storage_key)
            except FileNotFoundError:
                _integrity_fail("Document is incomplete — chunks missing")
            if sha256_hex(ciphertext) != chunk.chunk_hash:
                _integrity_fail("Chunk hash mismatch — storage tampering detected")
            running_hashes.append(chunk.chunk_hash)
            chunk_key = derive_chunk_key(master_key, str(document.id), chunk.chunk_index)
            try:
                iv = bytes.fromhex(chunk.iv_hex)
                pieces.append(decrypt_chunk(chunk_key, iv, ciphertext))
            except (InvalidTag, ValueError):
                _integrity_fail("Chunk hash mismatch — storage tampering detected")

        computed = compute_integrity_hash(running_hashes)
        if computed != document.integrity_hash:
            _integrity_fail("Document-level integrity check failed")
        return b"".join(pieces)
    finally:
        master_key = None


def reconstruct_bytes(document_id) -> bytes:
    """Internal reconstruct. Caller must already have authorized access."""
    did = _as_uuid(document_id)
    document = db.session.get(Document, did)
    if document is None:
        raise APIError(404, "NOT_FOUND", "Not found")
    return _reconstruct_verified(document)


def _png_base64(png_bytes: bytes) -> str:
    return base64.b64encode(png_bytes).decode("ascii")


def _render_image_pages(plaintext: bytes) -> tuple[list[str], bool]:
    from PIL import Image

    pages: list[str] = []
    truncated = False
    with Image.open(io.BytesIO(plaintext)) as img:
        frame = 0
        while True:
            if frame >= MAX_PREVIEW_PAGES:
                truncated = True
                break
            converted = img.convert("RGB")
            buf = io.BytesIO()
            converted.save(buf, format="PNG")
            pages.append(_png_base64(buf.getvalue()))
            frame += 1
            try:
                img.seek(frame)
            except EOFError:
                break
    return pages, truncated


def _render_pdf_pages(plaintext: bytes) -> tuple[list[str], bool]:
    import fitz

    pages: list[str] = []
    truncated = False
    doc = fitz.open(stream=plaintext, filetype="pdf")
    try:
        total = doc.page_count
        truncated = total > MAX_PREVIEW_PAGES
        for i in range(min(total, MAX_PREVIEW_PAGES)):
            pix = doc.load_page(i).get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
            pages.append(_png_base64(pix.tobytes("png")))
    finally:
        doc.close()
    return pages, truncated


def _render_text(plaintext: bytes) -> tuple[str, bool]:
    raw = plaintext.decode("utf-8", errors="replace").replace("\x00", "")
    truncated = len(raw) > MAX_PREVIEW_TEXT_CHARS
    if truncated:
        raw = raw[:MAX_PREVIEW_TEXT_CHARS]
    return raw, truncated


def preview_document(document_id, requesting_user_id) -> dict:
    document = get_document_for_user(document_id, requesting_user_id)
    if document.mime_type not in PREVIEWABLE_MIME_TYPES:
        raise APIError(400, "VALIDATION_ERROR", "Preview is not available for this file type")

    plaintext = _reconstruct_verified(document)
    try:
        if document.mime_type == "text/plain":
            text, truncated = _render_text(plaintext)
            return {
                "document_id": document.id,
                "mode": "text",
                "pages_png_base64": [],
                "text": text,
                "page_count": 1,
                "truncated": truncated,
                "filename": document.filename,
                "mime_type": document.mime_type,
            }
        if document.mime_type == "application/pdf":
            pages, truncated = _render_pdf_pages(plaintext)
        else:
            pages, truncated = _render_image_pages(plaintext)
        return {
            "document_id": document.id,
            "mode": "pages",
            "pages_png_base64": pages,
            "text": None,
            "page_count": len(pages),
            "truncated": truncated,
            "filename": document.filename,
            "mime_type": document.mime_type,
        }
    except APIError:
        raise
    except Exception as exc:
        raise APIError(400, "VALIDATION_ERROR", "Preview is not available for this file type") from exc
    finally:
        plaintext = b""


def download_document(document_id, requesting_user_id):
    raise NotImplementedError


def soft_delete(document_id, actor) -> None:
    raise NotImplementedError


def list_documents(case_id, requesting_user_id) -> list:
    raise NotImplementedError
