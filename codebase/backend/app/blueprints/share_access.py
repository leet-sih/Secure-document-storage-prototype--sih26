"""
share_access.py — PUBLIC external access. Prefix: /api/v1/share   (NO JWT)

This is the ONLY document path reachable without an account. Aggressively rate-limited.

ROUTES:
    GET  /{token}/info                  Public info (scope, filename/case, expiry, requires_email,
                                        allow_download). 410 if invalid/expired/revoked
    POST /{token}/request-otp           Send a 6-digit OTP to the recipient's email. Must be called
                                        before any access endpoint when email is provided.
    POST /{token}/download              Validate email + OTP + increment use_count + deliver:
                                        - DOCUMENT scope: streams the decrypted file (403 if
                                          allow_download=False)
                                        - CASE_DOCUMENTS scope: JSON doc list + metadata
                                        - CASE_FULL scope: JSON case detail + members + doc list
                                        410 expired/revoked/exhausted; 403 email/OTP mismatch
    POST /{token}/preview               DOCUMENT scope only. Server-side PNG/text preview —
                                        never sends the raw file. Does not count against use_count.
    POST /{token}/file/{doc_id}         CASE scope only. Streams one document (403 if
                                        allow_download=False).
    POST /{token}/file/{doc_id}/preview CASE scope. Server-side preview of one document.

Every access logs SHARE_LINK_ACCESSED or SHARE_LINK_PREVIEWED (IP, user_agent, share_id, scope).
Integrity verified before any plaintext byte is sent.

See feature_plans/specs/secure_sharing_spec.md + feature_plans/specs/share_otp_spec.md.
"""

import uuid as _uuid

from flask import Blueprint, Response, jsonify, request

from app.core import email_otp
from app.core.audit_events import AuditEventType
from app.core.errors import APIError
from app.core.rate_limit import OTP_REQUEST_LIMITS, SHARE_ACCESS_LIMITS
from app.extensions import db, limiter
from app.models.document import Document
from app.schemas.sharing_schemas import OtpRequestSchema, ShareAccessSchema
from app.services import sharing_service
from app.services.audit_service import audit_service
from app.services.document_service import IntegrityError

share_access_bp = Blueprint("share_access", __name__)

_access_schema = ShareAccessSchema()
_otp_request_schema = OtpRequestSchema()


def _parse_access() -> tuple[str | None, str | None]:
    """Return (email, otp) from request body. Both default to None on parse failure."""
    body = request.get_json(silent=True) or {}
    try:
        data = _access_schema.load(body)
        return data.get("email"), data.get("otp")
    except Exception:
        return None, None


def _log_failed_access(err: APIError, token: str, share_id: str | None = None) -> None:
    audit_service.record(
        AuditEventType.UNAUTHORIZED_ACCESS_ATTEMPT.value,
        ip_address=request.remote_addr,
        metadata={
            "reason": err.code,
            "token_prefix": token[:8],
            "user_agent": request.user_agent.string,
            **({"share_id": share_id} if share_id else {}),
        },
    )


# ── Info ─────────────────────────────────────────────────────────────────────────

@share_access_bp.route("/<token>/info", methods=["GET"])
@limiter.limit(SHARE_ACCESS_LIMITS)
def share_info(token: str):
    info = sharing_service.get_share_info(token)
    return jsonify(info), 200


# ── OTP request ───────────────────────────────────────────────────────────────────

@share_access_bp.route("/<token>/request-otp", methods=["POST"])
@limiter.limit(OTP_REQUEST_LIMITS)
def request_otp(token: str):
    """Send a 6-digit OTP to the recipient. Email gate is validated before sending."""
    body = request.get_json(silent=True) or {}
    try:
        data = _otp_request_schema.load(body)
    except Exception:
        raise APIError(400, "VALIDATION_ERROR", "A valid email address is required")

    email: str = data["email"]

    # Validate link + email gate without touching use_count
    try:
        link = sharing_service.validate_token_no_increment(token, email)
    except APIError as exc:
        _log_failed_access(exc, token)
        raise

    hint = "document" if link.share_scope == "DOCUMENT" else "case"
    email_otp.generate_and_send(token, email, hint)

    audit_service.record(
        AuditEventType.SHARE_OTP_SENT.value,
        ip_address=request.remote_addr,
        metadata={
            "share_id": str(link.id),
            "scope": link.share_scope,
            "token_prefix": token[:8],
        },
    )

    return jsonify({"message": "OTP sent to your email. Valid for 10 minutes."}), 200


# ── Download (all scopes) ─────────────────────────────────────────────────────────

@share_access_bp.route("/<token>/download", methods=["POST"])
@limiter.limit(SHARE_ACCESS_LIMITS)
def share_download(token: str):
    email, otp = _parse_access()

    # OTP verified in-memory BEFORE use_count is incremented (no wasted uses on wrong OTP)
    try:
        email_otp.verify_or_raise(token, email, otp)
    except APIError as exc:
        _log_failed_access(exc, token)
        raise

    try:
        link = sharing_service.validate_token(token, email)
    except APIError as exc:
        _log_failed_access(exc, token)
        raise

    audit_service.record(
        AuditEventType.SHARE_LINK_ACCESSED.value,
        target_type=link.share_scope.lower(),
        target_id=link.document_id or link.case_id,
        case_id=link.case_id,
        ip_address=request.remote_addr,
        metadata={
            "share_id": str(link.id),
            "scope": link.share_scope,
            "user_agent": request.user_agent.string,
        },
    )

    if link.share_scope == "DOCUMENT":
        if not link.allow_download:
            raise APIError(403, "DOWNLOAD_NOT_PERMITTED", "This link allows preview only — download is not permitted")
        return _stream_document(link.document_id)

    if link.share_scope == "CASE_DOCUMENTS":
        docs = sharing_service.get_case_documents_for_share(str(link.case_id))
        return jsonify({
            "scope": "CASE_DOCUMENTS",
            "case_id": str(link.case_id),
            "documents": docs,
        }), 200

    # CASE_FULL
    case_detail = sharing_service.get_case_detail_for_share(str(link.case_id))
    docs = sharing_service.get_case_documents_for_share(str(link.case_id))
    return jsonify({
        "scope": "CASE_FULL",
        "case": case_detail,
        "documents": docs,
    }), 200


# ── Per-file download (CASE scope) ────────────────────────────────────────────────

@share_access_bp.route("/<token>/file/<uuid:doc_id>", methods=["POST"])
@limiter.limit(SHARE_ACCESS_LIMITS)
def share_file_download(token: str, doc_id):
    email, otp = _parse_access()

    try:
        email_otp.verify_or_raise(token, email, otp)
    except APIError as exc:
        _log_failed_access(exc, token)
        raise

    try:
        link = sharing_service.validate_token_no_increment(token, email)
    except APIError as exc:
        _log_failed_access(exc, token)
        raise

    if link.share_scope == "DOCUMENT":
        raise APIError(400, "BAD_REQUEST", "Use /download for single-document share links")

    doc = db.session.get(Document, _uuid.UUID(str(doc_id)))
    if doc is None or doc.is_deleted:
        raise APIError(404, "NOT_FOUND", "Document not found")
    if str(doc.case_id) != str(link.case_id):
        raise APIError(404, "NOT_FOUND", "Document not found in this share")

    audit_service.record(
        AuditEventType.SHARE_LINK_ACCESSED.value,
        target_type="document",
        target_id=doc_id,
        case_id=link.case_id,
        ip_address=request.remote_addr,
        metadata={
            "share_id": str(link.id),
            "scope": link.share_scope,
            "sub_download": True,
            "doc_id": str(doc_id),
            "user_agent": request.user_agent.string,
        },
    )

    if not link.allow_download:
        raise APIError(403, "DOWNLOAD_NOT_PERMITTED", "This link allows preview only — download is not permitted")

    return _stream_document(doc.id)


# ── Preview (DOCUMENT scope) ──────────────────────────────────────────────────────

@share_access_bp.route("/<token>/preview", methods=["POST"])
@limiter.limit(SHARE_ACCESS_LIMITS)
def share_preview(token: str):
    """Server-side preview — DOCUMENT scope only. Does not count against use_count."""
    email, otp = _parse_access()

    try:
        email_otp.verify_or_raise(token, email, otp)
    except APIError as exc:
        _log_failed_access(exc, token)
        raise

    try:
        link = sharing_service.validate_token_no_increment(token, email)
    except APIError as exc:
        _log_failed_access(exc, token)
        raise

    if link.share_scope != "DOCUMENT":
        raise APIError(400, "BAD_REQUEST", "Use /file/{doc_id}/preview for case-scope links")

    doc = db.session.get(Document, _uuid.UUID(str(link.document_id)))
    if doc is None or doc.is_deleted:
        raise APIError(404, "NOT_FOUND", "Document not available")

    from app.services.document_service import preview_document_public
    payload = preview_document_public(doc)

    audit_service.record(
        AuditEventType.SHARE_LINK_PREVIEWED.value,
        target_type="document",
        target_id=link.document_id,
        case_id=link.case_id,
        ip_address=request.remote_addr,
        metadata={
            "share_id": str(link.id),
            "scope": link.share_scope,
            "filename": doc.filename,
        },
    )
    return jsonify(payload), 200


# ── Preview (CASE scope) ──────────────────────────────────────────────────────────

@share_access_bp.route("/<token>/file/<uuid:doc_id>/preview", methods=["POST"])
@limiter.limit(SHARE_ACCESS_LIMITS)
def share_file_preview(token: str, doc_id):
    """Server-side preview of one file in a case share. Does not count against use_count."""
    email, otp = _parse_access()

    try:
        email_otp.verify_or_raise(token, email, otp)
    except APIError as exc:
        _log_failed_access(exc, token)
        raise

    try:
        link = sharing_service.validate_token_no_increment(token, email)
    except APIError as exc:
        _log_failed_access(exc, token)
        raise

    if link.share_scope == "DOCUMENT":
        raise APIError(400, "BAD_REQUEST", "Use /preview for single-document share links")

    doc = db.session.get(Document, _uuid.UUID(str(doc_id)))
    if doc is None or doc.is_deleted:
        raise APIError(404, "NOT_FOUND", "Document not found")
    if str(doc.case_id) != str(link.case_id):
        raise APIError(404, "NOT_FOUND", "Document not found in this share")

    from app.services.document_service import preview_document_public
    payload = preview_document_public(doc)

    audit_service.record(
        AuditEventType.SHARE_LINK_PREVIEWED.value,
        target_type="document",
        target_id=doc_id,
        case_id=link.case_id,
        ip_address=request.remote_addr,
        metadata={
            "share_id": str(link.id),
            "scope": link.share_scope,
            "filename": doc.filename,
        },
    )
    return jsonify(payload), 200


# ── Internal: decrypt + stream ───────────────────────────────────────────────────

def _stream_document(document_id) -> Response:
    """Integrity-verify and stream a document. 422 on tamper, 404 if missing."""
    from app.services.document_service import _verify_and_decrypt as _vd

    doc = db.session.get(Document, _uuid.UUID(str(document_id)))
    if doc is None or doc.is_deleted:
        raise APIError(404, "NOT_FOUND", "Document not available")

    try:
        parts = _vd(doc)
    except IntegrityError:
        audit_service.record(
            AuditEventType.INTEGRITY_VIOLATION.value,
            target_type="document",
            target_id=document_id,
            case_id=doc.case_id,
            ip_address=request.remote_addr,
            metadata={"filename": doc.filename, "via_share": True},
        )
        raise APIError(422, "INTEGRITY_VIOLATION", "Document failed integrity verification")

    def generate():
        for part in parts:
            yield part

    return Response(
        generate(),
        mimetype=doc.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{doc.filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )
