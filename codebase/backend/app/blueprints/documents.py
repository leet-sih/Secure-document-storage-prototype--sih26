"""
documents.py — upload / list / download / delete + OCR. Prefix: /api/v1

ROUTES:
    POST   /cases/{case_id}/documents        [SUPER_ADMIN, CASE_OFFICER]  multipart upload
    GET    /cases/{case_id}/documents        [members]  list metadata (no content)
    GET    /documents/{id}/download          [any auth]  pre-verify + stream plaintext
    DELETE /documents/{id}                   [SUPER_ADMIN, CASE_OFFICER]  soft delete
    POST   /documents/{id}/ocr              [any auth]  trigger OCR on demand
    POST   /documents/{id}/ocr/approve      [any auth]  approve or dismiss OCR text
    POST   /me/documents                     [any auth]  personal vault upload
    GET    /me/documents                     [any auth]  list own personal documents

Case-scoped access (404 not 403 for non-members) is enforced in document_service/case_service.
Personal docs are owner-only; the service checks uploaded_by == requesting_user_id.

See feature_plans/specs/ocr_integration_spec.md + docs/EDGE_CASES.md §1 & §5.
"""

from flask import Blueprint, Response, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.core.audit_events import AuditEventType
from app.core.errors import APIError
from app.core.rate_limit import UPLOAD_LIMITS
from app.core.rbac import Role, require_recent_mfa, require_roles
from app.extensions import limiter
from app.schemas.document_schemas import DocumentDeleteSchema, DocumentMetadataSchema, DocumentUploadSchema, OcrActionSchema
from app.services import document_service, signature_service
from app.services.audit_service import audit_service
from app.services.document_service import IntegrityError

documents_bp = Blueprint("documents", __name__)

_upload_schema = DocumentUploadSchema()
_ocr_action_schema = OcrActionSchema()
_metadata_schema = DocumentMetadataSchema()
_metadata_list_schema = DocumentMetadataSchema(many=True)


def _parse_upload_payload():
    """Extract and validate the non-file multipart fields for both upload endpoints."""
    doc_type = (request.form.get("doc_type") or "").strip() or None
    title = (request.form.get("title") or "").strip() or None
    raw: dict = {}
    if doc_type:
        raw["doc_type"] = doc_type
    if title:
        raw["title"] = title
    tags = [t.strip() for t in request.form.getlist("tags") if t.strip()]
    if tags:
        raw["tags"] = tags
    # auto_ocr: accept "1", "true" (case-insensitive) as truthy
    auto_ocr_raw = request.form.get("auto_ocr", "").strip().lower()
    if auto_ocr_raw in ("1", "true"):
        raw["auto_ocr"] = True
    return _upload_schema.load(raw)


@documents_bp.route("/cases/<uuid:case_id>/documents", methods=["POST"])
@jwt_required()
@limiter.limit(UPLOAD_LIMITS)
@require_roles(Role.SUPER_ADMIN, Role.CASE_OFFICER)
def upload_document(case_id, current_user):
    file = request.files.get("file")
    if file is None or not file.filename:
        raise APIError(400, "VALIDATION_ERROR", "Missing 'file' part")

    payload = _parse_upload_payload()

    doc = document_service.upload_document(
        case_id=str(case_id),
        file_stream=file.stream,
        filename=file.filename,
        mime_type=file.mimetype,
        doc_type=payload["doc_type"],
        uploader_id=current_user.id,
        title=payload.get("title"),
        tags=payload.get("tags"),
        auto_ocr=payload.get("auto_ocr", False),
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
            "auto_ocr": payload.get("auto_ocr", False),
        },
    )
    # Auto-sign on upload: best-effort, never blocks the 201 response
    try:
        if current_user.role in ("SUPER_ADMIN", "CASE_OFFICER", "INVESTIGATOR"):
            signature_service.sign_document(str(doc.id), current_user)
            audit_service.record(
                AuditEventType.DOCUMENT_SIGNED.value,
                actor_user_id=current_user.id,
                target_type="document",
                target_id=doc.id,
                case_id=str(case_id),
                metadata={"auto": True},
            )
    except Exception:
        pass
    return jsonify(_metadata_schema.dump(doc)), 201


@documents_bp.route("/cases/<uuid:case_id>/documents", methods=["GET"])
@require_roles(
    Role.SUPER_ADMIN,
    Role.CASE_OFFICER,
    Role.INVESTIGATOR,
    Role.PROSECUTOR,
)
def list_documents(case_id, current_user):
    docs = document_service.list_documents(str(case_id), str(current_user.id))
    return jsonify(_metadata_list_schema.dump(docs)), 200


@documents_bp.route("/documents/<uuid:document_id>/download", methods=["GET"])
@require_roles(
    Role.SUPER_ADMIN,
    Role.CASE_OFFICER,
    Role.INVESTIGATOR,
    Role.PROSECUTOR,
)
def download_document(document_id, current_user):
    user_id = str(current_user.id)
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


@documents_bp.route("/documents/<uuid:document_id>/check-integrity", methods=["POST"])
@require_roles(
    Role.SUPER_ADMIN,
    Role.CASE_OFFICER,
    Role.INVESTIGATOR,
    Role.PROSECUTOR,
)
def check_integrity(document_id, current_user):
    user_id = str(current_user.id)
    try:
        document_service.check_document_integrity(str(document_id), user_id)
    except IntegrityError:
        raise APIError(422, "INTEGRITY_VIOLATION", "Document failed integrity verification")
    return jsonify({"ok": True}), 200


_delete_schema = DocumentDeleteSchema()


@documents_bp.route("/documents/<uuid:document_id>", methods=["DELETE"])
@jwt_required()
@require_roles(Role.SUPER_ADMIN, Role.CASE_OFFICER)
@require_recent_mfa()
def delete_document(document_id, current_user):
    from app.core import totp as _totp

    data = _delete_schema.load(request.get_json(silent=True) or {})
    if not current_user.totp_secret:
        raise APIError(403, "FORBIDDEN", "MFA is not enabled on this account")
    secret = _totp.decrypt_secret(current_user.totp_secret)
    if not _totp.verify(secret, data["totp_code"]):
        audit_service.record(
            AuditEventType.MFA_STEP_UP_FAILED.value,
            actor_user_id=current_user.id,
        )
        raise APIError(401, "UNAUTHORIZED", "Invalid TOTP code")

    doc = document_service.soft_delete(str(document_id), current_user)
    audit_service.record(
        AuditEventType.DOCUMENT_DELETED.value,
        actor_user_id=current_user.id,
        target_type="document",
        target_id=doc.id,
        case_id=doc.case_id,
        metadata={"filename": doc.filename, "totp_verified": True},
    )
    return "", 204


# ── OCR ───────────────────────────────────────────────────────────

@documents_bp.route("/documents/<uuid:document_id>/ocr", methods=["POST"])
@jwt_required()
def trigger_ocr(document_id):
    user_id = get_jwt_identity()
    body = request.get_json(silent=True) or {}
    force = bool(body.get("force", False))
    doc = document_service.generate_ocr_for_document(str(document_id), user_id, force=force)
    audit_service.record(
        AuditEventType.DOCUMENT_UPLOADED.value,  # closest available event; add OCR_GENERATED later
        actor_user_id=user_id,
        target_type="document",
        target_id=doc.id,
        case_id=doc.case_id,
        metadata={"action": "ocr_generated", "ocr_status": doc.ocr_status},
    )
    return jsonify(_metadata_schema.dump(doc)), 200


@documents_bp.route("/documents/<uuid:document_id>/ocr/approve", methods=["POST"])
@jwt_required()
def approve_ocr(document_id):
    user_id = get_jwt_identity()
    payload = _ocr_action_schema.load(request.get_json(silent=True) or {})
    doc = document_service.approve_ocr(str(document_id), user_id, payload["action"])
    audit_service.record(
        AuditEventType.DOCUMENT_UPLOADED.value,
        actor_user_id=user_id,
        target_type="document",
        target_id=doc.id,
        case_id=doc.case_id,
        metadata={"action": f"ocr_{payload['action']}d", "ocr_status": doc.ocr_status},
    )
    return jsonify(_metadata_schema.dump(doc)), 200


# ── Personal vault ────────────────────────────────────────────────

@documents_bp.route("/me/documents", methods=["POST"])
@jwt_required()
@limiter.limit(UPLOAD_LIMITS)
def upload_personal_document():
    user_id = get_jwt_identity()
    file = request.files.get("file")
    if file is None or not file.filename:
        raise APIError(400, "VALIDATION_ERROR", "Missing 'file' part")

    payload = _parse_upload_payload()

    doc = document_service.upload_personal_document(
        file_stream=file.stream,
        filename=file.filename,
        mime_type=file.mimetype,
        doc_type=payload["doc_type"],
        uploader_id=user_id,
        title=payload.get("title"),
        tags=payload.get("tags"),
        auto_ocr=payload.get("auto_ocr", False),
    )
    audit_service.record(
        AuditEventType.DOCUMENT_UPLOADED.value,
        actor_user_id=user_id,
        target_type="document",
        target_id=doc.id,
        case_id=None,
        metadata={
            "filename": doc.filename,
            "size_bytes": doc.file_size_bytes,
            "chunks": doc.total_chunks,
            "personal": True,
            "auto_ocr": payload.get("auto_ocr", False),
        },
    )
    return jsonify(_metadata_schema.dump(doc)), 201


@documents_bp.route("/me/documents", methods=["GET"])
@jwt_required()
def list_personal_documents():
    user_id = get_jwt_identity()
    docs = document_service.list_personal_documents(user_id)
    return jsonify(_metadata_list_schema.dump(docs)), 200
