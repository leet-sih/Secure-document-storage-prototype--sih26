"""
documents.py — upload / list / download / delete. Prefix: /api/v1

ROUTES:
    POST   /cases/{case_id}/documents   [SUPER_ADMIN, CASE_OFFICER]  multipart upload (rate-limited)
        Streams the `file` part into document_service.upload_document. Blocks if the case is
        CLOSED/ARCHIVED. Records DOCUMENT_UPLOADED.
    GET    /cases/{case_id}/documents   [members]  list metadata (no content). 404 if not a member.
    GET    /documents/{id}/download     [members]  pre-verify all chunks -> stream plaintext;
        Content-Disposition: attachment. IntegrityError -> 422 INTEGRITY_VIOLATION.
        Records DOCUMENT_DOWNLOADED.
    DELETE /documents/{id}              [SUPER_ADMIN, CASE_OFFICER]  soft delete; DOCUMENT_DELETED

Case-scoped access (membership) is enforced in document_service/case_service and returns 404
(not 403) to non-members — the route-level RBAC only gates coarse SYSTEM roles.

The binary `file` part is read from werkzeug's FileStorage.stream (a seekable spooled temp file),
so the magic-byte sniff works and we never materialise 500 MB in a single Python bytes object.
See feature_plans/specs/document_encryption_keystore_spec.md + docs/EDGE_CASES.md §1 & §5.
"""

from flask import Blueprint, Response, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.core.audit_events import AuditEventType
from app.core.errors import APIError
from app.core.rate_limit import UPLOAD_LIMITS
from app.core.rbac import Role, require_roles
from app.extensions import limiter
from app.schemas.document_schemas import DocumentMetadataSchema, DocumentUploadSchema
from app.services import document_service
from app.services.audit_service import audit_service
from app.services.document_service import IntegrityError

documents_bp = Blueprint("documents", __name__)

_upload_schema = DocumentUploadSchema()
_metadata_schema = DocumentMetadataSchema()
_metadata_list_schema = DocumentMetadataSchema(many=True)


@documents_bp.route("/cases/<uuid:case_id>/documents", methods=["POST"])
@jwt_required()
@limiter.limit(UPLOAD_LIMITS)
@require_roles(Role.SUPER_ADMIN, Role.CASE_OFFICER)
def upload_document(case_id, current_user):
    file = request.files.get("file")
    if file is None or not file.filename:
        raise APIError(400, "VALIDATION_ERROR", "Missing 'file' part")

    # Validate the non-file form fields through marshmallow (unknown=RAISE).
    raw = {"doc_type": request.form.get("doc_type"), "title": request.form.get("title")}
    tags = request.form.getlist("tags")
    if tags:
        raw["tags"] = tags
    payload = _upload_schema.load({k: v for k, v in raw.items() if v is not None})

    doc = document_service.upload_document(
        case_id=str(case_id),
        file_stream=file.stream,
        filename=file.filename,
        mime_type=file.mimetype,
        doc_type=payload["doc_type"],
        uploader_id=current_user.id,
        title=payload.get("title"),
        tags=payload.get("tags"),
    )
    audit_service.record(
        AuditEventType.DOCUMENT_UPLOADED.value,
        actor_user_id=current_user.id,
        target_type="document",
        target_id=doc.id,
        case_id=str(case_id),
        metadata={
            "filename": doc.filename,
            "size_bytes": doc.file_size_bytes,
            "chunks": doc.total_chunks,
        },
    )
    return jsonify(_metadata_schema.dump(doc)), 201


@documents_bp.route("/cases/<uuid:case_id>/documents", methods=["GET"])
@jwt_required()
def list_documents(case_id):
    docs = document_service.list_documents(str(case_id), get_jwt_identity())
    return jsonify(_metadata_list_schema.dump(docs)), 200


@documents_bp.route("/documents/<uuid:document_id>/download", methods=["GET"])
@jwt_required()
def download_document(document_id):
    user_id = get_jwt_identity()
    try:
        doc, stream = document_service.download_document(str(document_id), user_id)
    except IntegrityError:
        raise APIError(422, "INTEGRITY_VIOLATION", "Document failed integrity verification")

    audit_service.record(
        AuditEventType.DOCUMENT_DOWNLOADED.value,
        actor_user_id=user_id,
        target_type="document",
        target_id=doc.id,
        case_id=doc.case_id,
        metadata={"filename": doc.filename},
    )
    return Response(
        stream,
        mimetype=doc.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{doc.filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@documents_bp.route("/documents/<uuid:document_id>", methods=["DELETE"])
@jwt_required()
@require_roles(Role.SUPER_ADMIN, Role.CASE_OFFICER)
def delete_document(document_id, current_user):
    doc = document_service.soft_delete(str(document_id), current_user)
    audit_service.record(
        AuditEventType.DOCUMENT_DELETED.value,
        actor_user_id=current_user.id,
        target_type="document",
        target_id=doc.id,
        case_id=doc.case_id,
    )
    return "", 204
