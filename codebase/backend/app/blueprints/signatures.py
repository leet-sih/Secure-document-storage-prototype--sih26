"""
signatures.py — document digital signatures. Prefix: /api/v1/documents/{id}

ROUTES:
    POST /{id}/sign                    [SUPER_ADMIN, CASE_OFFICER, INVESTIGATOR]  sign; 409 if already signed
    GET  /{id}/signatures              [any JWT]  list signatures + validity; 404 if not a member
    POST /{id}/signatures/verify       [any JWT]  re-verify all signatures; 404 if not a member
    DELETE /{id}/signatures/{sig_id}   [signer or SUPER_ADMIN]  revoke (row kept)

Blocked on ARCHIVED cases (enforced in service). Records DOCUMENT_SIGNED / SIGNATURE_VERIFIED / SIGNATURE_REVOKED.
See digital_signatures_plan.md and feature_plans/specs/digital_signatures_spec.md.
"""

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.core.audit_events import AuditEventType
from app.core.rbac import Role, require_roles
from app.core.security import current_user_required, require_access_jwt
from app.schemas.signature_schemas import SignRequestSchema, SignatureResponseSchema, VerifyResponseSchema
from app.services import signature_service
from app.services.audit_service import audit_service

signatures_bp = Blueprint("signatures", __name__)

_sign_req_schema = SignRequestSchema()
_sig_schema = SignatureResponseSchema()
_sig_list_schema = SignatureResponseSchema(many=True)


@signatures_bp.route("/documents/<uuid:doc_id>/sign", methods=["POST"])
@require_roles(Role.SUPER_ADMIN, Role.CASE_OFFICER, Role.INVESTIGATOR)
def sign_document(doc_id, current_user):
    body = _sign_req_schema.load(request.get_json(silent=True) or {})
    sig = signature_service.sign_document(str(doc_id), current_user, comment=body.get("comment"))
    audit_service.record(
        AuditEventType.DOCUMENT_SIGNED.value,
        actor_user_id=current_user.id,
        target_type="document",
        target_id=doc_id,
        case_id=None,
        ip_address=request.remote_addr,
        metadata={"auto": False},
    )
    return jsonify(_sig_schema.dump(sig)), 201


@signatures_bp.route("/documents/<uuid:doc_id>/signatures", methods=["GET"])
@require_access_jwt
def list_signatures(doc_id):
    current_user = current_user_required()
    sigs = signature_service._load_signatures(str(doc_id), str(current_user.id))
    return jsonify({"document_id": str(doc_id), "signatures": _sig_list_schema.dump(sigs)}), 200


@signatures_bp.route("/documents/<uuid:doc_id>/signatures/verify", methods=["POST"])
@require_access_jwt
def verify_signatures(doc_id):
    current_user = current_user_required()
    results = signature_service.verify_signatures(str(doc_id), str(current_user.id))
    audit_service.record(
        AuditEventType.SIGNATURE_VERIFIED.value,
        actor_user_id=current_user.id,
        target_type="document",
        target_id=doc_id,
        ip_address=request.remote_addr,
    )
    now = datetime.now(timezone.utc)
    body = VerifyResponseSchema().dump(
        {"document_id": doc_id, "verified_at": now, "results": results}
    )
    return jsonify(body), 200


@signatures_bp.route(
    "/documents/<uuid:doc_id>/signatures/<uuid:sig_id>", methods=["DELETE"]
)
@require_access_jwt
def revoke_signature(doc_id, sig_id):
    current_user = current_user_required()
    signature_service.revoke_signature(str(doc_id), str(sig_id), current_user)
    audit_service.record(
        AuditEventType.SIGNATURE_REVOKED.value,
        actor_user_id=current_user.id,
        target_type="document",
        target_id=doc_id,
        ip_address=request.remote_addr,
        metadata={"signature_id": str(sig_id)},
    )
    return "", 204
