"""tests/documents/test_preview.py — reconstruct + preview (file_viewer_spec.md)."""

from __future__ import annotations

import io
import os
import secrets
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-kms-ok")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-not-for-kms-ok")
os.environ.setdefault("KMS_WRAPPING_KEY", "test-kms-wrapping-key-32b-ok")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.core import kms
from app.core.crypto import (
    compute_integrity_hash,
    derive_chunk_key,
    encrypt_chunk,
    generate_master_key,
    sha256_hex,
)
from app.core.errors import APIError
from app.services import document_service
from app.storage import chunk_store


class _PreviewConfig:
    TESTING = True
    SECRET_KEY = "test-secret-key-not-for-kms-ok"
    JWT_SECRET_KEY = "test-jwt-secret-not-for-kms-ok"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    KMS_WRAPPING_KEY = "test-kms-wrapping-key-32b-ok"
    CHUNK_STORE_BACKEND = "local"
    MAX_FILE_SIZE_MB = 1
    CHUNK_SIZE_BYTES = 32
    MAX_CONTENT_LENGTH = 1024 * 1024
    RATELIMIT_ENABLED = False


@pytest.fixture
def app(tmp_path):
    from app import create_app

    cfg = _PreviewConfig()
    cfg.KMS_DIR = str(tmp_path / "keys")
    cfg.CHUNK_STORAGE_DIR = str(tmp_path / "chunks")
    return create_app(cfg)


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app


def _tiny_png() -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (2, 2), (40, 80, 160)).save(buf, format="PNG")
    return buf.getvalue()


def _store_one_chunk(document_id, plaintext: bytes):
    master = generate_master_key()
    kms.store_key(str(document_id), master)
    chunk_key = derive_chunk_key(master, str(document_id), 0)
    iv, ciphertext = encrypt_chunk(chunk_key, plaintext)
    storage_key = secrets.token_hex(16)
    chunk_store.put_chunk(storage_key, ciphertext)
    digest = sha256_hex(ciphertext)
    chunk = SimpleNamespace(
        chunk_index=0,
        storage_key=storage_key,
        iv_hex=iv.hex(),
        chunk_hash=digest,
        size_bytes=len(plaintext),
    )
    doc = SimpleNamespace(
        id=document_id,
        case_id=uuid4(),
        mime_type="text/plain",
        is_deleted=False,
        status="ACTIVE",
        total_chunks=1,
        integrity_hash=compute_integrity_hash([digest]),
        filename="note.txt",
    )
    return doc, chunk


def _patch_load(document, chunk, case=None):
    mock_q = MagicMock()
    mock_q.filter_by.return_value.order_by.return_value.all.return_value = [chunk]
    return (
        patch("app.services.document_service.db.session.get", return_value=document),
        patch("app.services.document_service.DocumentChunk.query", mock_q),
        patch(
            "app.services.document_service.case_service.get_case_for_user",
            return_value=case or SimpleNamespace(status="OPEN"),
        ),
    )


def test_preview_text_plain(app_ctx):
    doc_id = uuid4()
    body = "Witness line 1\n<script>x</script>\n".encode("utf-8")
    document, chunk = _store_one_chunk(doc_id, body)
    p_get, p_q, p_case = _patch_load(document, chunk)
    with p_get, p_q, p_case:
        out = document_service.preview_document(doc_id, uuid4())
    assert out["mode"] == "text"
    assert "<script>x</script>" in out["text"]
    assert out["pages_png_base64"] == []
    assert out["truncated"] is False


def test_preview_png_reencodes(app_ctx):
    doc_id = uuid4()
    png = _tiny_png()
    document, chunk = _store_one_chunk(doc_id, png)
    document.mime_type = "image/png"
    document.filename = "shot.png"
    p_get, p_q, p_case = _patch_load(document, chunk)
    with p_get, p_q, p_case:
        out = document_service.preview_document(doc_id, uuid4())
    assert out["mode"] == "pages"
    assert len(out["pages_png_base64"]) == 1
    assert out["pages_png_base64"][0].startswith("iVBOR")
    assert out["text"] is None


def test_preview_unsupported_mime(app_ctx):
    doc_id = uuid4()
    document, chunk = _store_one_chunk(doc_id, b"not-a-real-mp4-but-encrypted")
    document.mime_type = "video/mp4"
    p_get, p_q, p_case = _patch_load(document, chunk)
    with p_get, p_q, p_case:
        with pytest.raises(APIError) as exc:
            document_service.preview_document(doc_id, uuid4())
    assert exc.value.status == 400


def test_preview_404_when_no_case_access(app_ctx):
    doc_id = uuid4()
    document, chunk = _store_one_chunk(doc_id, b"hello")
    p_get, p_q, p_case = _patch_load(document, chunk)
    p_case = patch(
        "app.services.document_service.case_service.get_case_for_user",
        return_value=None,
    )
    with p_get, p_q, p_case:
        with pytest.raises(APIError) as exc:
            document_service.preview_document(doc_id, uuid4())
    assert exc.value.status == 404


def test_preview_404_deleted(app_ctx):
    doc_id = uuid4()
    document, chunk = _store_one_chunk(doc_id, b"hello")
    document.is_deleted = True
    p_get, p_q, p_case = _patch_load(document, chunk)
    with p_get, p_q, p_case:
        with pytest.raises(APIError) as exc:
            document_service.get_document_for_user(doc_id, uuid4())
    assert exc.value.status == 404


def test_preview_tampered_chunk_422(app_ctx):
    doc_id = uuid4()
    document, chunk = _store_one_chunk(doc_id, b"hello world")
    raw = chunk_store.get_chunk(chunk.storage_key)
    chunk_store.put_chunk(chunk.storage_key, raw[:-1] + bytes([raw[-1] ^ 0xFF]))
    p_get, p_q, p_case = _patch_load(document, chunk)
    with p_get, p_q, p_case:
        with pytest.raises(APIError) as exc:
            document_service.preview_document(doc_id, uuid4())
    assert exc.value.status == 422
    assert exc.value.code == "INTEGRITY_VIOLATION"


def test_preview_kms_missing_503(app_ctx):
    doc_id = uuid4()
    document, chunk = _store_one_chunk(doc_id, b"hello")
    kms.delete_key(str(doc_id))
    p_get, p_q, p_case = _patch_load(document, chunk)
    with p_get, p_q, p_case:
        with pytest.raises(APIError) as exc:
            document_service.preview_document(doc_id, uuid4())
    assert exc.value.status == 503
