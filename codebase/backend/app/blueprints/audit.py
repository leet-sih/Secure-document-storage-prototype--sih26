"""
audit.py — audit log access + integrity verification. Prefix: /api/v1/audit

ROUTES:
    GET /              [SUPER_ADMIN, AUDITOR]           paginated, filterable audit log
    GET /cases/{id}    [SUPER_ADMIN, AUDITOR, CASE_OFFICER of case]  case-scoped log
    GET /verify        [SUPER_ADMIN, AUDITOR]           recompute chain -> {chain_valid, first_break_at}

Responses use AuditEventSchema, which NEVER dumps prev_hash/this_hash. See audit_trail_plan.md.
"""

from flask import Blueprint

audit_bp = Blueprint("audit", __name__)

# TODO: implement routes.
# from app.core.rbac import require_roles, Role
# from app.schemas.audit_schemas import AuditQuerySchema, AuditEventSchema, AuditVerifySchema
# from app.services.audit_service import audit_service
