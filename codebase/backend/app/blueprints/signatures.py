"""
signatures.py — document digital signatures. Prefix: /api/v1/documents/{id}

ROUTES:
    POST /{id}/sign                    [SUPER_ADMIN, CASE_OFFICER, INVESTIGATOR]  sign; 409 if already signed
    GET  /{id}/signatures              [members]  list signatures + validity
    POST /{id}/signatures/verify       [members]  re-verify all signatures now
    DELETE /{id}/signatures/{sig_id}   [signer or SUPER_ADMIN]  revoke (row kept)

Blocked on ARCHIVED cases. Records DOCUMENT_SIGNED / SIGNATURE_VERIFIED / SIGNATURE_REVOKED.
See digital_signatures_plan.md.
"""

from flask import Blueprint

signatures_bp = Blueprint("signatures", __name__)

# TODO: implement routes.
# from app.core.rbac import require_roles, Role
# from app.schemas.signature_schemas import SignatureResponseSchema
# from app.services import signature_service
