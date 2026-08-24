"""
sharing.py — owner-side share management (authenticated). Prefix: /api/v1/documents/{id}

ROUTES:
    POST /{id}/share               [SUPER_ADMIN, CASE_OFFICER]  create link ->
        returns share_url with the RAW token ONCE (never retrievable again).
    GET  /{id}/shares              [SUPER_ADMIN, CASE_OFFICER]  list links for a document
    DELETE /{id}/shares/{share_id} [creator or SUPER_ADMIN]     revoke

Records DOCUMENT_SHARED / SHARE_LINK_REVOKED. The PUBLIC access side is share_access.py.
See document_sharing_plan.md.
"""

from flask import Blueprint

sharing_bp = Blueprint("sharing", __name__)

# TODO: implement routes.
# from app.core.rbac import require_roles, Role
# from app.schemas.sharing_schemas import ShareCreateSchema, ShareResponseSchema
# from app.services import sharing_service
