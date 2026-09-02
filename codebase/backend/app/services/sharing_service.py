"""
sharing_service.py — time-limited external share links (DOCUMENT, CASE_DOCUMENTS, CASE_FULL).

create_share_document(document_id, creator, opts) -> (DocumentShareLink, raw_token)
create_share_case(case_id, share_scope, creator, opts) -> (DocumentShareLink, raw_token)
    token = secrets.token_urlsafe(32); store SHA256(token) only. RETURNS raw token ONCE.

validate_token(token, email=None) -> DocumentShareLink
    Hash token -> atomic conditional UPDATE (increment use_count only if not
    revoked/expired/exhausted, race-safe RETURNING). Enforce optional email gate
    (case-insensitive). 410 on invalid/expired/exhausted; 403 on email mismatch; 404 unknown.
    Does NOT increment use_count for sub-file downloads (see validate_token_no_increment).

validate_token_no_increment(token, email=None) -> DocumentShareLink
    Re-validates token+email without touching use_count. Used for per-file downloads
    inside a CASE scope (use was counted when the case listing was fetched).

get_share_info(token) -> dict    (public info, no side effects)
revoke_share(share_id, actor) -> None    (only creator or SUPER_ADMIN)
list_shares_for_document(document_id, actor) -> list
list_shares_for_case(case_id, actor) -> list

STORES: rows in document_share_links (token_hash only, never the raw token).
Full design: ../../feature_plans/document_sharing_plan.md + specs/secure_sharing_spec.md
"""

import hashlib
import secrets
import uuid as _uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from app.core.errors import APIError
from app.extensions import db
from app.models.document import Document
from app.models.document_share_link import DocumentShareLink
from app.services import case_service


# ── Token utilities ─────────────────────────────────────────────────────────────

def _make_token() -> tuple[str, str]:
    """Return (raw_token, token_hash). raw_token is never stored."""
    raw = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, token_hash


def _hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


# ── Creation ─────────────────────────────────────────────────────────────────────

def create_share_document(document_id: str, creator, opts: dict) -> tuple[DocumentShareLink, str]:
    """Create a DOCUMENT-scope share link. RETURNS (link_row, raw_token) — raw_token shown once."""
    doc = db.session.get(Document, _uuid.UUID(str(document_id)))
    if doc is None or doc.is_deleted:
        raise APIError(404, "NOT_FOUND", "Document not found")

    if doc.case_id:
        case = case_service.get_case_for_user(doc.case_id, str(creator.id))
        if case.status == "ARCHIVED":
            raise APIError(409, "CONFLICT", "Cannot share documents from an archived case")

    raw_token, token_hash = _make_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=opts["expires_in_hours"])
    max_uses = opts.get("max_uses", 1)

    # SUPER_ADMIN can set -1 (unlimited); others capped at 10.
    if max_uses == -1 and creator.role != "SUPER_ADMIN":
        raise APIError(403, "FORBIDDEN", "Only SUPER_ADMIN can create unlimited-use links")

    link = DocumentShareLink(
        share_scope="DOCUMENT",
        document_id=_uuid.UUID(str(document_id)),
        case_id=doc.case_id,
        token_hash=token_hash,
        created_by=creator.id,
        allowed_email=(opts.get("allowed_email") or "").strip().lower() or None,
        expires_at=expires_at,
        max_uses=max_uses,
        note=opts.get("note"),
        allow_download=opts.get("allow_download", True),
    )
    db.session.add(link)
    db.session.commit()
    return link, raw_token


def create_share_case(case_id: str, share_scope: str, creator, opts: dict) -> tuple[DocumentShareLink, str]:
    """Create a CASE_DOCUMENTS or CASE_FULL share link. RETURNS (link_row, raw_token)."""
    case = case_service.get_case_for_user(case_id, str(creator.id))
    if case.status == "ARCHIVED":
        raise APIError(409, "CONFLICT", "Cannot share an archived case")

    if share_scope not in ("CASE_DOCUMENTS", "CASE_FULL"):
        raise APIError(400, "VALIDATION_ERROR", "Invalid share_scope for case share")

    raw_token, token_hash = _make_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=opts["expires_in_hours"])
    max_uses = opts.get("max_uses", 1)

    if max_uses == -1 and creator.role != "SUPER_ADMIN":
        raise APIError(403, "FORBIDDEN", "Only SUPER_ADMIN can create unlimited-use links")

    link = DocumentShareLink(
        share_scope=share_scope,
        document_id=None,
        case_id=_uuid.UUID(str(case_id)),
        token_hash=token_hash,
        created_by=creator.id,
        allowed_email=(opts.get("allowed_email") or "").strip().lower() or None,
        expires_at=expires_at,
        max_uses=max_uses,
        note=opts.get("note"),
        allow_download=opts.get("allow_download", True),
    )
    db.session.add(link)
    db.session.commit()
    return link, raw_token


# ── Public access ─────────────────────────────────────────────────────────────────

def get_share_info(raw_token: str) -> dict:
    """Return public info about a share link without side effects. 410 if invalid."""
    token_hash = _hash(raw_token)
    now = datetime.now(timezone.utc)

    link = DocumentShareLink.query.filter_by(token_hash=token_hash).first()
    if link is None:
        raise APIError(410, "GONE", "This link is no longer valid")
    if link.is_revoked:
        raise APIError(410, "GONE", "This link is no longer valid")
    if link.expires_at.replace(tzinfo=timezone.utc) <= now:
        raise APIError(410, "GONE", "This link is no longer valid")
    if link.max_uses != -1 and link.use_count >= link.max_uses:
        raise APIError(410, "GONE", "This link is no longer valid")

    # Extra check: case archived after link was created
    if link.case_id:
        from app.models.case import Case
        case = db.session.get(Case, link.case_id)
        if case and case.status == "ARCHIVED":
            raise APIError(410, "GONE", "This link is no longer valid")

    info: dict = {
        "scope": link.share_scope,
        "filename": None,
        "case_title": None,
        "case_number": None,
        "doc_count": None,
        "file_size_bytes": None,
        "expires_at": link.expires_at.isoformat(),
        "requires_email": bool(link.allowed_email),
        "is_valid": True,
        "allow_download": link.allow_download,
    }

    if link.share_scope == "DOCUMENT" and link.document_id:
        doc = db.session.get(Document, link.document_id)
        if doc and not doc.is_deleted:
            info["filename"] = doc.filename
            info["file_size_bytes"] = doc.file_size_bytes

    if link.case_id:
        from app.models.case import Case
        from app.models.document import Document as Doc
        case = db.session.get(Case, link.case_id)
        if case:
            info["case_title"] = case.title
            info["case_number"] = case.case_number
        if link.share_scope in ("CASE_DOCUMENTS", "CASE_FULL"):
            count = Doc.query.filter_by(case_id=link.case_id, is_deleted=False).count()
            info["doc_count"] = count

    return info


def validate_token(raw_token: str, email: str | None = None) -> DocumentShareLink:
    """Validate token + email gate; atomically increment use_count. 404/410/403 on failure.

    ORDER: read row → check email gate → atomic increment. This ensures a wrong email
    attempt does not consume a use of the link.
    """
    token_hash = _hash(raw_token)
    now = datetime.now(timezone.utc)

    # Step 1: read-only pre-check (email gate, expiry, revocation).
    link = DocumentShareLink.query.filter_by(token_hash=token_hash).first()
    if link is None:
        raise APIError(404, "NOT_FOUND", "Share link not found")
    if link.is_revoked:
        raise APIError(410, "GONE", "This link is no longer valid")
    expires = link.expires_at.replace(tzinfo=timezone.utc) if link.expires_at.tzinfo is None else link.expires_at
    if expires <= now:
        raise APIError(410, "GONE", "This link has expired")
    if link.max_uses != -1 and link.use_count >= link.max_uses:
        raise APIError(410, "GONE", "This link has been used the maximum number of times")

    if link.case_id:
        from app.models.case import Case
        case = db.session.get(Case, link.case_id)
        if case and case.status == "ARCHIVED":
            raise APIError(410, "GONE", "This link is no longer valid")

    # Step 2: email gate — checked BEFORE incrementing so a wrong email doesn't burn a use.
    if link.allowed_email and not _email_matches(email, link.allowed_email):
        raise APIError(403, "EMAIL_MISMATCH", "Email does not match the link restriction")

    # Step 3: atomic increment — race-safe; only one concurrent winner at max_uses.
    result = db.session.execute(
        text("""
            UPDATE document_share_links
            SET use_count = use_count + 1
            WHERE token_hash = :hash
              AND is_revoked = FALSE
              AND expires_at > NOW()
              AND (max_uses = -1 OR use_count < max_uses)
            RETURNING id
        """),
        {"hash": token_hash},
    )
    if result.fetchone() is None:
        raise APIError(410, "GONE", "This link is expired, revoked, or exhausted")

    db.session.commit()
    # Re-fetch to get fresh use_count (harmless N+1 at this call frequency).
    return db.session.get(DocumentShareLink, link.id)


def validate_token_no_increment(raw_token: str, email: str | None = None) -> DocumentShareLink:
    """Re-validate token + email without incrementing use_count. Used for per-file downloads
    inside a case-scope session (use was already counted at listing time)."""
    token_hash = _hash(raw_token)
    now = datetime.now(timezone.utc)

    link = DocumentShareLink.query.filter_by(token_hash=token_hash).first()
    if link is None:
        raise APIError(404, "NOT_FOUND", "Share link not found")
    if link.is_revoked:
        raise APIError(410, "GONE", "This link is no longer valid")
    if link.expires_at.replace(tzinfo=timezone.utc) <= now:
        raise APIError(410, "GONE", "This link has expired")

    if link.case_id:
        from app.models.case import Case
        case = db.session.get(Case, link.case_id)
        if case and case.status == "ARCHIVED":
            raise APIError(410, "GONE", "This link is no longer valid")

    if link.allowed_email and not _email_matches(email, link.allowed_email):
        raise APIError(403, "EMAIL_MISMATCH", "Email does not match the link restriction")

    return link


def _email_matches(provided: str | None, required: str) -> bool:
    if not provided:
        return False
    return provided.strip().lower() == required.strip().lower()


# ── Revocation ──────────────────────────────────────────────────────────────────

def revoke_share(share_id: str, actor) -> None:
    """Revoke a share link. Only the creator or SUPER_ADMIN may revoke."""
    link = db.session.get(DocumentShareLink, _uuid.UUID(str(share_id)))
    if link is None:
        raise APIError(404, "NOT_FOUND", "Share link not found")

    if str(link.created_by) != str(actor.id) and actor.role != "SUPER_ADMIN":
        raise APIError(403, "FORBIDDEN", "Only the creator or SUPER_ADMIN can revoke this link")

    link.is_revoked = True
    link.revoked_by = actor.id
    link.revoked_at = datetime.now(timezone.utc)
    db.session.commit()


# ── Listing ─────────────────────────────────────────────────────────────────────

def list_shares_for_document(document_id: str, actor) -> list:
    """List all share links for a document. Caller must have case access."""
    doc = db.session.get(Document, _uuid.UUID(str(document_id)))
    if doc is None or doc.is_deleted:
        raise APIError(404, "NOT_FOUND", "Document not found")
    if doc.case_id and not case_service.user_has_access(str(actor.id), str(doc.case_id)):
        raise APIError(404, "NOT_FOUND", "Document not found")

    links = (
        DocumentShareLink.query
        .filter_by(document_id=_uuid.UUID(str(document_id)))
        .order_by(DocumentShareLink.created_at.desc())
        .all()
    )
    now = datetime.now(timezone.utc)
    return [_link_dict(l, now) for l in links]


def list_shares_for_case(case_id: str, actor) -> list:
    """List all share links for a case (all scopes). Caller must have case access."""
    case_service.get_case_for_user(case_id, str(actor.id))

    links = (
        DocumentShareLink.query
        .filter_by(case_id=_uuid.UUID(str(case_id)))
        .order_by(DocumentShareLink.created_at.desc())
        .all()
    )
    now = datetime.now(timezone.utc)
    return [_link_dict(l, now) for l in links]


def _link_dict(link: DocumentShareLink, now: datetime) -> dict:
    expires = link.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return {
        "id": str(link.id),
        "share_scope": link.share_scope,
        "document_id": str(link.document_id) if link.document_id else None,
        "case_id": str(link.case_id) if link.case_id else None,
        "allowed_email": link.allowed_email,
        "expires_at": expires.isoformat(),
        "max_uses": link.max_uses,
        "use_count": link.use_count,
        "is_revoked": link.is_revoked,
        "is_expired": expires <= now,
        "note": link.note,
        "allow_download": link.allow_download,
        "created_at": link.created_at.isoformat() if link.created_at else None,
    }


# ── Case document list (for CASE_* scopes) ──────────────────────────────────────

def get_case_documents_for_share(case_id: str) -> list[dict]:
    """Return serialisable metadata for all non-deleted docs in the case. OCR fields included."""
    from app.services.document_service import _decrypt_ocr_fields
    docs = (
        Document.query
        .filter_by(case_id=_uuid.UUID(str(case_id)), is_deleted=False)
        .order_by(Document.created_at.desc())
        .all()
    )
    result = []
    for doc in docs:
        _decrypt_ocr_fields(doc)
        result.append({
            "id": str(doc.id),
            "filename": doc.filename,
            "doc_type": doc.doc_type,
            "file_size_bytes": doc.file_size_bytes,
            "mime_type": doc.mime_type,
            "tags": doc.tags or [],
            "ocr_status": doc.ocr_status,
            "ocr_confidence": doc.ocr_confidence,
            "ocr_page_count": doc.ocr_page_count,
            "ocr_formatted_text": doc.search_text if doc.ocr_status == "DONE" else None,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        })
    return result


def get_case_detail_for_share(case_id: str) -> dict:
    """Return full case detail (no members' PII beyond names and roles) for CASE_FULL scope."""
    from app.models.case import Case
    from app.models.case_member import CaseMember
    from app.models.user import User
    from app.models.department import Department

    case = db.session.get(Case, _uuid.UUID(str(case_id)))
    if not case:
        raise APIError(404, "NOT_FOUND", "Case not found")

    members_q = CaseMember.query.filter_by(case_id=case.id, is_active=True).all()
    members = []
    for m in members_q:
        mu = db.session.get(User, m.user_id)
        if not mu:
            continue
        dept = db.session.get(Department, mu.department_id)
        members.append({
            "full_name": mu.full_name,
            "role": m.role,
            "department": dept.name if dept else None,
        })

    return {
        "id": str(case.id),
        "case_number": case.case_number,
        "title": case.title,
        "description": case.description,
        "status": case.status,
        "priority": case.priority,
        "category": case.category,
        "member_count": len(members),
        "members": members,
        "created_at": case.created_at.isoformat() if case.created_at else None,
    }
