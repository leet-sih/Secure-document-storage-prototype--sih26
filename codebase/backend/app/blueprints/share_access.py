"""
share_access.py — PUBLIC external download. Prefix: /api/v1/share   (NO JWT)

This is the ONLY document path reachable without an account. Aggressively rate-limited.

ROUTES:
    GET  /{token}/info       public info (filename, size, expiry, requires_email); 410 if invalid
    POST /{token}/download   {email?} -> streams the decrypted document if the link is valid
        Atomic use_count increment; email gate (case-insensitive) if set.
        410 expired/revoked/exhausted; 403 email mismatch; 404 unknown token.

Records SHARE_LINK_ACCESSED (with IP + user agent). Never reveals why a token is invalid
beyond the status code. See document_sharing_plan.md + docs/EDGE_CASES.md 2.2.
"""

from flask import Blueprint

share_access_bp = Blueprint("share_access", __name__)

# TODO: implement routes.
# from app.extensions import limiter
# from app.core.rate_limit import SHARE_ACCESS_LIMITS
# from app.schemas.sharing_schemas import ShareAccessSchema
# from app.services import sharing_service
