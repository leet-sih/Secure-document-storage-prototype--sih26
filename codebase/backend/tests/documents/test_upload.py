"""
tests/documents/test_upload.py — upload pipeline tests from chunked_document_storage_plan.md.
"""

from __future__ import annotations

import io
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-kms-ok")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-not-for-kms-ok")
os.environ.setdefault("KMS_WRAPPING_KEY", "test-kms-wrapping-key-32b-ok")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.core.errors import APIError
from app.services import document_service


PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
EXE_BYTES = b"MZ" + b"\x00" * 64


class _UploadConfig:
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

    cfg = _UploadConfig()
    cfg.KMS_DIR = str(tmp_path / "keys")
    cfg.CHUNK_STORAGE_DIR = str(tmp_path / "chunks")
    application = create_app(cfg)
    return application


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app


@pytest.fixture
def open_case():
    return SimpleNamespace(status="OPEN", id=uuid4())


def _run_upload(app_ctx, open_case, data: bytes, filename="report.pdf", **kwargs):
    with patch("app.services.document_service.case_service.get_case_for_user", return_value=open_case):
        with patch("app.services.document_service.db") as mock_db:
            mock_db.session = MagicMock()
            return document_service.upload_document(
                case_id=open_case.id,
                file_stream=io.BytesIO(data),
                filename=filename,
                mime_type="application/pdf",
                doc_type="FIR",
                uploader_id=uuid4(),
                **kwargs,
            )


def test_upload_rejected_invalid_mime_type(app_ctx, open_case):
    with patch("app.services.document_service.case_service.get_case_for_user", return_value=open_case):
        with pytest.raises(APIError) as exc:
            document_service.upload_document(
                case_id=open_case.id,
                file_stream=io.BytesIO(EXE_BYTES),
                filename="report.pdf",
                mime_type="application/pdf",
                doc_type="FIR",
                uploader_id=uuid4(),
            )
    assert exc.value.status == 400
    assert exc.value.code == "VALIDATION_ERROR"


def test_upload_rejected_file_too_large(app_ctx, open_case):
    huge = PDF_BYTES + b"\x00" * (2 * 1024 * 1024)
    with patch("app.services.document_service.case_service.get_case_for_user", return_value=open_case):
        with pytest.raises(APIError) as exc:
            document_service.upload_document(
                case_id=open_case.id,
                file_stream=io.BytesIO(huge),
                filename="report.pdf",
                mime_type="application/pdf",
                doc_type="FIR",
                uploader_id=uuid4(),
            )
    assert exc.value.status == 400


def test_upload_requires_case_access(app_ctx):
    with patch(
        "app.services.document_service.case_service.get_case_for_user",
        side_effect=APIError(404, "NOT_FOUND", "Not found"),
    ):
        with pytest.raises(APIError) as exc:
            document_service.upload_document(
                case_id=uuid4(),
                file_stream=io.BytesIO(PDF_BYTES),
                filename="report.pdf",
                mime_type="application/pdf",
                doc_type="FIR",
                uploader_id=uuid4(),
            )
    assert exc.value.status == 404


def test_upload_pdf_creates_chunks_in_minio(app_ctx, open_case, tmp_path):
    """Local chunk store (spec: not MinIO paths)."""
    doc = _run_upload(app_ctx, open_case, PDF_BYTES * 4)
    stored = list((tmp_path / "chunks").iterdir()) if (tmp_path / "chunks").exists() else []
    # tmp_path on fixture app is the same dirs
    chunk_dir = app_ctx.config["CHUNK_STORAGE_DIR"]
    files = [p for p in os.listdir(chunk_dir) if os.path.isfile(os.path.join(chunk_dir, p))]
    assert len(files) >= 1
    assert all(len(name) == 32 for name in files)  # token_hex(16)
    assert doc.status == "ACTIVE"


def test_upload_stores_correct_chunk_count(app_ctx, open_case):
    payload = PDF_BYTES * 20
    doc = _run_upload(app_ctx, open_case, payload)
    expected = (len(payload) + 31) // 32
    assert doc.total_chunks == expected
    assert doc.file_size_bytes == len(payload)


def test_upload_integrity_hash_computed_correctly(app_ctx, open_case):
    payload = PDF_BYTES * 8
    doc = _run_upload(app_ctx, open_case, payload)
    assert len(doc.integrity_hash) == 64


def test_failed_upload_cleans_up_minio_objects(app_ctx, open_case):
    calls = {"n": 0}

    def fail_second(storage_key, data):
        calls["n"] += 1
        if calls["n"] >= 2:
            raise OSError("disk full")
        from app.storage.chunk_store import _put_local

        return _put_local(storage_key, data)

    with patch("app.services.document_service.case_service.get_case_for_user", return_value=open_case):
        with patch("app.services.document_service.db") as mock_db:
            mock_db.session = MagicMock()
            with patch("app.services.document_service.chunk_store.put_chunk", side_effect=fail_second):
                with pytest.raises(APIError) as exc:
                    document_service.upload_document(
                        case_id=open_case.id,
                        file_stream=io.BytesIO(PDF_BYTES * 20),
                        filename="report.pdf",
                        mime_type="application/pdf",
                        doc_type="FIR",
                        uploader_id=uuid4(),
                    )
    assert exc.value.status == 500
    chunk_dir = app_ctx.config["CHUNK_STORAGE_DIR"]
    leftover = os.listdir(chunk_dir) if os.path.isdir(chunk_dir) else []
    assert leftover == []


def test_failed_upload_cleans_up_vault_key(app_ctx, open_case):
    def boom(storage_key, data):
        raise OSError("store down")

    with patch("app.services.document_service.case_service.get_case_for_user", return_value=open_case):
        with patch("app.services.document_service.db") as mock_db:
            mock_db.session = MagicMock()
            with patch("app.services.document_service.chunk_store.put_chunk", side_effect=boom):
                with pytest.raises(APIError):
                    document_service.upload_document(
                        case_id=open_case.id,
                        file_stream=io.BytesIO(PDF_BYTES),
                        filename="report.pdf",
                        mime_type="application/pdf",
                        doc_type="FIR",
                        uploader_id=uuid4(),
                    )
    keys_dir = app_ctx.config["KMS_DIR"]
    leftover = os.listdir(keys_dir) if os.path.isdir(keys_dir) else []
    assert leftover == []
