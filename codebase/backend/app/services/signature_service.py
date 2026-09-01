"""
signature_service.py — Ed25519 document signatures.

sign_document(document_id, signer) -> DocumentSignature
    Loads/creates signer keypair (private -> users.signing_private_key_enc, public -> users.signing_public_key).
    Builds payload = SHA256(integrity_hash | doc_id | signer_id | ts), signs, stores.
    409 if signer already signed this document (UNIQUE constraint).
verify_signatures(document_id, requesting_user_id) -> list[dict]
    For each signature: verify Ed25519 AND check current integrity_hash still equals
    integrity_hash_at_signing. Updates is_valid/last_verified_at.
revoke_signature(document_id, signature_id, actor) -> None
    Only the signer or SUPER_ADMIN. Sets revoked_at + is_valid=False (row kept for audit).

STORES: rows in document_signatures; private+public keys in users.
Full design: ../../feature_plans/digital_signatures_plan.md
"""

import hashlib
from datetime import datetime, timezone

from app.core import signing
from app.core.errors import APIError
from app.extensions import db
from app.models.case import Case
from app.models.case_member import CaseMember
from app.models.document import Document
from app.models.document_signature import DocumentSignature
from app.models.user import User


def _load_doc_assert_access(document_id: str, user_id: str) -> Document:
    """Load document and verify the user is an active case member (or SUPER_ADMIN).
    Returns 404 to non-members so they cannot enumerate document existence."""
    doc = db.session.get(Document, document_id)
    if doc is None or doc.is_deleted:
        raise APIError(404, "NOT_FOUND", "Document not found")

    user = db.session.get(User, user_id)
    if user and user.role == "SUPER_ADMIN":
        return doc

    member = CaseMember.query.filter_by(
        case_id=doc.case_id, user_id=user_id, is_active=True
    ).first()
    if member is None:
        raise APIError(404, "NOT_FOUND", "Document not found")

    return doc


def _get_or_create_keypair(user: User) -> bytes:
    """Return the raw Ed25519 private key bytes for `user`, generating + storing if first use."""
    if user.signing_private_key_enc and user.signing_public_key:
        return signing.decrypt_private_key(user.signing_private_key_enc)

    private_bytes, public_bytes = signing.generate_keypair()
    user.signing_private_key_enc = signing.encrypt_private_key(private_bytes)
    user.signing_public_key = public_bytes.hex()
    db.session.flush()
    return private_bytes


def _load_signatures(document_id: str, requesting_user_id: str) -> list[DocumentSignature]:
    """Return all signature rows for `document_id`. Enforces case membership (404 for non-members)."""
    _load_doc_assert_access(document_id, requesting_user_id)
    return DocumentSignature.query.filter_by(document_id=document_id).order_by(
        DocumentSignature.created_at
    ).all()


def sign_document(document_id: str, signer, comment: str | None = None) -> DocumentSignature:
    """Cryptographically sign `document_id` as `signer`.
    Returns the new DocumentSignature row. Raises 409 if already signed or case archived."""
    signer_id = str(signer.id)
    doc = _load_doc_assert_access(document_id, signer_id)

    case = db.session.get(Case, doc.case_id)
    if case and case.status == "ARCHIVED":
        raise APIError(409, "CONFLICT", "Cannot sign documents in an archived case")

    existing = DocumentSignature.query.filter_by(
        document_id=document_id, signer_user_id=signer_id
    ).first()
    if existing:
        raise APIError(409, "CONFLICT", "You have already signed this document")

    user = db.session.get(User, signer_id)
    private_bytes = _get_or_create_keypair(user)

    ts = datetime.now(timezone.utc).replace(microsecond=0)
    ts_iso = ts.isoformat()
    payload = signing.build_signed_payload(doc.integrity_hash, str(doc.id), signer_id, ts_iso)
    sig_hex = signing.sign(private_bytes, payload)
    payload_hash = hashlib.sha256(payload).hexdigest()

    sig = DocumentSignature(
        document_id=doc.id,
        signer_user_id=signer_id,
        integrity_hash_at_signing=doc.integrity_hash,
        signed_payload_hash=payload_hash,
        signature_hex=sig_hex,
        comment=comment,
        created_at=ts,
    )
    db.session.add(sig)
    db.session.commit()
    return sig


def verify_signatures(document_id: str, requesting_user_id: str) -> list[dict]:
    """Re-verify every signature on `document_id`. Updates is_valid/last_verified_at.
    Returns a list of per-signature result dicts."""
    doc = _load_doc_assert_access(document_id, requesting_user_id)

    sigs = DocumentSignature.query.filter_by(document_id=document_id).all()
    now = datetime.now(timezone.utc)
    results = []

    for sig in sigs:
        signer = db.session.get(User, sig.signer_user_id)
        result: dict = {
            "signature_id": str(sig.id),
            "signer_email": signer.email if signer else "unknown",
        }

        if sig.revoked_at is not None:
            sig.is_valid = False
            sig.last_verified_at = now
            result["is_valid"] = False
            result["reason"] = "Signature was revoked"
            results.append(result)
            continue

        if not signer or not signer.signing_public_key:
            sig.is_valid = False
            sig.last_verified_at = now
            result["is_valid"] = False
            result["reason"] = "Signer public key not found"
            results.append(result)
            continue

        ts_iso = sig.created_at.replace(microsecond=0).isoformat()
        payload = signing.build_signed_payload(
            sig.integrity_hash_at_signing,
            str(sig.document_id),
            str(sig.signer_user_id),
            ts_iso,
        )

        crypto_valid = signing.verify(
            bytes.fromhex(signer.signing_public_key),
            sig.signature_hex,
            payload,
        )
        doc_unmodified = doc.integrity_hash == sig.integrity_hash_at_signing

        is_valid = crypto_valid and doc_unmodified
        sig.is_valid = is_valid
        sig.last_verified_at = now

        result["is_valid"] = is_valid
        if not is_valid:
            if not doc_unmodified:
                result["reason"] = "Document modified after signing"
            else:
                result["reason"] = "Cryptographic signature invalid"

        results.append(result)

    db.session.commit()
    return results


def revoke_signature(document_id: str, signature_id: str, actor) -> None:
    """Revoke a signature. Only the signer or SUPER_ADMIN may revoke.
    Row is kept; revoked_at + is_valid=False marks it as revoked."""
    actor_id = str(actor.id)
    sig = DocumentSignature.query.filter_by(
        id=signature_id, document_id=document_id
    ).first()
    if sig is None:
        raise APIError(404, "NOT_FOUND", "Signature not found")

    if sig.revoked_at is not None:
        raise APIError(409, "CONFLICT", "Signature already revoked")

    if str(sig.signer_user_id) != actor_id and actor.role != "SUPER_ADMIN":
        raise APIError(403, "FORBIDDEN", "You can only revoke your own signature")

    sig.revoked_at = datetime.now(timezone.utc)
    sig.is_valid = False
    db.session.commit()
