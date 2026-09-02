"""
documents.py — upload / list / download / preview / delete. Prefix: /api/v1

This branch: POST /cases/{case_id}/documents, GET /documents/{id}, GET /documents/{id}/preview.
"""

from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import ValidationError
from flask_limiter.util import get_remote_address

from app.core.audit_events import AuditEventType
from app.core.errors import APIError, error_response
from app.core.rate_limit import DEFAULT_LIMITS, UPLOAD_LIMITS
from app.core.rbac import Role, require_roles
from app.extensions import limiter
from app.schemas.document_schemas import (
    DocumentMetadataSchema,
    DocumentPreviewSchema,
    DocumentUploadSchema,
)
from app.services import document_service
from app.services.audit_service import audit_service

documents_bp = Blueprint("documents", __name__)

_VIEW_ROLES = (
    Role.SUPER_ADMIN,
    Role.CASE_OFFICER,
    Role.INVESTIGATOR,
    Role.PROSECUTOR,
)


@documents_bp.route("/cases/<case_id>/documents", methods=["POST"])
@jwt_required()
@require_roles(Role.SUPER_ADMIN, Role.CASE_OFFICER)
@limiter.limit(
    UPLOAD_LIMITS,
    key_func=lambda: str(get_jwt_identity() or get_remote_address()),
)
def upload_case_document(case_id, current_user):
    file = request.files.get("file")
    if file is None or not file.filename:
        return error_response(400, "VALIDATION_ERROR", "file is required")

    payload: dict = {
        "doc_type": request.form.get("doc_type"),
        "tags": request.form.getlist("tags"),
    }
    if request.form.get("title"):
        payload["title"] = request.form.get("title")
    try:
        form = DocumentUploadSchema().load(payload)
    except ValidationError as exc:
        return error_response(400, "VALIDATION_ERROR", str(exc.messages))

    try:
        document = document_service.upload_document(
            case_id=case_id,
            file_stream=file.stream,
            filename=file.filename,
            mime_type=file.mimetype,
            doc_type=form["doc_type"],
            uploader_id=current_user.id,
            title=form.get("title"),
            tags=form.get("tags") or [],
        )
    except APIError as exc:
        return error_response(exc.status, exc.code, exc.message)

    audit_service.record(
        AuditEventType.DOCUMENT_UPLOADED.value,
        actor_user_id=current_user.id,
        target_type="document",
        target_id=document.id,
        case_id=case_id,
        metadata={
            "filename": document.filename,
            "size_bytes": document.file_size_bytes,
            "chunks": document.total_chunks,
        },
    )
    return DocumentMetadataSchema().dump(document), 201


@documents_bp.route("/documents/<document_id>", methods=["GET"])
@jwt_required()
@require_roles(*_VIEW_ROLES)
@limiter.limit(
    DEFAULT_LIMITS,
    key_func=lambda: str(get_jwt_identity() or get_remote_address()),
)
def get_document(document_id, current_user):
    try:
        document = document_service.get_document_for_user(document_id, current_user.id)
    except APIError as exc:
        return error_response(exc.status, exc.code, exc.message)
    return DocumentMetadataSchema().dump(document), 200


@documents_bp.route("/documents/<document_id>/preview", methods=["GET"])
@jwt_required()
@require_roles(*_VIEW_ROLES)
@limiter.limit(
    DEFAULT_LIMITS,
    key_func=lambda: str(get_jwt_identity() or get_remote_address()),
)
def preview_document(document_id, current_user):
    try:
        payload = document_service.preview_document(document_id, current_user.id)
    except APIError as exc:
        if exc.code == "INTEGRITY_VIOLATION":
            audit_service.record(
                AuditEventType.INTEGRITY_VIOLATION.value,
                actor_user_id=current_user.id,
                target_type="document",
                target_id=document_id,
                metadata={"reason": "preview"},
            )
        return error_response(exc.status, exc.code, exc.message)

    audit_service.record(
        AuditEventType.DOCUMENT_PREVIEWED.value,
        actor_user_id=current_user.id,
        target_type="document",
        target_id=payload["document_id"],
        metadata={
            "filename": payload.get("filename"),
            "mime_type": payload.get("mime_type"),
            "page_count": payload["page_count"],
        },
    )
    return DocumentPreviewSchema().dump(payload), 200
