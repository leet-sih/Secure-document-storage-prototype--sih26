"""
sharing.py — owner-side share management (authenticated).

DOCUMENT scope (under /api/v1):
    POST   /documents/{id}/share                [SUPER_ADMIN, CASE_OFFICER] + step-up MFA
    GET    /documents/{id}/shares               [SUPER_ADMIN, CASE_OFFICER]
    DELETE /documents/{id}/shares/{share_id}    [creator or SUPER_ADMIN]

CASE scope (under /api/v1):
    POST   /cases/{id}/share                    [SUPER_ADMIN, CASE_OFFICER] + step-up MFA
    GET    /cases/{id}/shares                   [SUPER_ADMIN, CASE_OFFICER]
    DELETE /cases/{id}/shares/{share_id}        [creator or SUPER_ADMIN]

Records DOCUMENT_SHARED / CASE_SHARED / SHARE_LINK_REVOKED. Public access side: share_access.py.
See feature_plans/specs/secure_sharing_spec.md.
"""

from flask import Blueprint, current_app, jsonify, request

from app.core.audit_events import AuditEventType
from app.core.errors import APIError
from app.core import totp as _totp
from app.core.rbac import Role, require_roles
from app.schemas.sharing_schemas import CaseShareCreateSchema, ShareCreateSchema
from app.services import sharing_service
from app.services.audit_service import audit_service

sharing_bp = Blueprint("sharing", __name__)

_doc_create_schema = ShareCreateSchema()
_case_create_schema = CaseShareCreateSchema()


def _verify_totp(current_user, data: dict) -> None:
    """Inline TOTP step-up check — share creation requires a fresh TOTP code."""
    totp_code = data.get("totp_code")
    if not totp_code:
        raise APIError(400, "VALIDATION_ERROR", "totp_code is required to create a share link")
    if not current_user.totp_secret:
        raise APIError(403, "FORBIDDEN", "MFA is not enabled on this account")
    secret = _totp.decrypt_secret(current_user.totp_secret)
    if not _totp.verify(secret, totp_code):
        audit_service.record(
            AuditEventType.MFA_STEP_UP_FAILED.value,
            actor_user_id=current_user.id,
        )
        raise APIError(401, "UNAUTHORIZED", "Invalid TOTP code")


# ── Document share ───────────────────────────────────────────────────────────────

@sharing_bp.route("/documents/<uuid:document_id>/share", methods=["POST"])
@require_roles(Role.SUPER_ADMIN, Role.CASE_OFFICER)
def create_document_share(document_id, current_user):
    body = request.get_json(silent=True) or {}
    _verify_totp(current_user, body)

    # Remove totp_code before schema validation (it's not in ShareCreateSchema).
    body_clean = {k: v for k, v in body.items() if k != "totp_code"}
    opts = _doc_create_schema.load(body_clean)

    link, raw_token = sharing_service.create_share_document(
        str(document_id), current_user, opts
    )

    audit_service.record(
        AuditEventType.DOCUMENT_SHARED.value,
        actor_user_id=current_user.id,
        target_type="document",
        target_id=document_id,
        case_id=link.case_id,
        ip_address=request.remote_addr,
        metadata={
            "share_id": str(link.id),
            "expires_at": link.expires_at.isoformat(),
            "allowed_email": link.allowed_email,
            "max_uses": link.max_uses,
        },
    )

    frontend = current_app.config["CORS_ORIGINS"][0].rstrip("/")
    share_url = f"{frontend}/share/{raw_token}"
    return jsonify({
        "share_id": str(link.id),
        "share_url": share_url,
        "expires_at": link.expires_at.isoformat(),
        "max_uses": link.max_uses,
    }), 201


@sharing_bp.route("/documents/<uuid:document_id>/shares", methods=["GET"])
@require_roles(Role.SUPER_ADMIN, Role.CASE_OFFICER)
def list_document_shares(document_id, current_user):
    shares = sharing_service.list_shares_for_document(str(document_id), current_user)
    return jsonify({"shares": shares}), 200


@sharing_bp.route("/documents/<uuid:document_id>/shares/<uuid:share_id>", methods=["DELETE"])
@require_roles(Role.SUPER_ADMIN, Role.CASE_OFFICER)
def revoke_document_share(document_id, share_id, current_user):
    sharing_service.revoke_share(str(share_id), current_user)
    audit_service.record(
        AuditEventType.SHARE_LINK_REVOKED.value,
        actor_user_id=current_user.id,
        target_type="document",
        target_id=document_id,
        ip_address=request.remote_addr,
        metadata={"share_id": str(share_id)},
    )
    return "", 204


# ── Case share ───────────────────────────────────────────────────────────────────

@sharing_bp.route("/cases/<uuid:case_id>/share", methods=["POST"])
@require_roles(Role.SUPER_ADMIN, Role.CASE_OFFICER)
def create_case_share(case_id, current_user):
    body = request.get_json(silent=True) or {}
    _verify_totp(current_user, body)

    body_clean = {k: v for k, v in body.items() if k != "totp_code"}
    opts = _case_create_schema.load(body_clean)

    link, raw_token = sharing_service.create_share_case(
        str(case_id), opts["share_scope"], current_user, opts
    )

    audit_service.record(
        AuditEventType.CASE_SHARED.value,
        actor_user_id=current_user.id,
        target_type="case",
        target_id=case_id,
        case_id=case_id,
        ip_address=request.remote_addr,
        metadata={
            "share_id": str(link.id),
            "share_scope": opts["share_scope"],
            "expires_at": link.expires_at.isoformat(),
            "allowed_email": link.allowed_email,
            "max_uses": link.max_uses,
        },
    )

    frontend = current_app.config["CORS_ORIGINS"][0].rstrip("/")
    share_url = f"{frontend}/share/{raw_token}"
    return jsonify({
        "share_id": str(link.id),
        "share_url": share_url,
        "expires_at": link.expires_at.isoformat(),
        "max_uses": link.max_uses,
        "share_scope": link.share_scope,
    }), 201


@sharing_bp.route("/cases/<uuid:case_id>/shares", methods=["GET"])
@require_roles(Role.SUPER_ADMIN, Role.CASE_OFFICER)
def list_case_shares(case_id, current_user):
    shares = sharing_service.list_shares_for_case(str(case_id), current_user)
    return jsonify({"shares": shares}), 200


@sharing_bp.route("/cases/<uuid:case_id>/shares/<uuid:share_id>", methods=["DELETE"])
@require_roles(Role.SUPER_ADMIN, Role.CASE_OFFICER)
def revoke_case_share(case_id, share_id, current_user):
    sharing_service.revoke_share(str(share_id), current_user)
    audit_service.record(
        AuditEventType.SHARE_LINK_REVOKED.value,
        actor_user_id=current_user.id,
        target_type="case",
        target_id=case_id,
        case_id=case_id,
        ip_address=request.remote_addr,
        metadata={"share_id": str(share_id)},
    )
    return "", 204
