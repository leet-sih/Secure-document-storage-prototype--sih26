"""
audit.py — audit log access + integrity verification. Prefix: /api/v1/audit

ROUTES:
    GET /              [SUPER_ADMIN, AUDITOR]           paginated, filterable audit log
    GET /cases/{id}    [SUPER_ADMIN, AUDITOR, CASE_OFFICER of case]  case-scoped log
    GET /verify        [SUPER_ADMIN, AUDITOR]           recompute chain -> {chain_valid, first_break_at}

Responses use AuditEventSchema, which NEVER dumps prev_hash/this_hash. See audit_trail_plan.md.
"""

from flask import Blueprint, request

from app.core.rbac import Role, require_roles
from app.models.audit_event import AuditEvent
from app.schemas.audit_schemas import AuditEventSchema, AuditQuerySchema, AuditVerifySchema
from app.services.audit_service import audit_service
from app.services import case_service

audit_bp = Blueprint("audit", __name__)

@audit_bp.get("")
@require_roles(Role.SUPER_ADMIN, Role.AUDITOR)
def list_audit_events(current_user):
    params = AuditQuerySchema().load(request.args)

    query = AuditEvent.query

    if params.get("event_type"):
        query = query.filter_by(event_type=params["event_type"])

    if params.get("actor_id"):
        query = query.filter_by(actor_user_id=params["actor_id"])

    if params.get("case_id"):
        query = query.filter_by(case_id=str(params["case_id"]))

    if params.get("target_type"):
        query = query.filter_by(target_type=params["target_type"])

    if params.get("from_date"):
        query = query.filter(AuditEvent.created_at >= params["from_date"])

    if params.get("to_date"):
        query = query.filter(AuditEvent.created_at <= params["to_date"])

    total = query.count()
    page = params["page"]
    limit = params["limit"]

    events = (
        query.order_by(AuditEvent.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return {
        "items": AuditEventSchema(many=True).dump(events),
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit,
    }

@audit_bp.get("/verify")
@require_roles(Role.SUPER_ADMIN, Role.AUDITOR)
def verify_audit_chain(current_user):
    result = audit_service.verify_chain()
    return AuditVerifySchema().dump(result)


@audit_bp.get("/cases/<uuid:case_id>")
@require_roles(Role.SUPER_ADMIN, Role.AUDITOR, Role.CASE_OFFICER)
def list_case_audit(case_id, current_user):
    if current_user.role == Role.CASE_OFFICER.value:
       case_service.get_case_for_user(case_id, str(current_user.id))

    events = (
        AuditEvent.query
        .filter_by(case_id=str(case_id))
        .order_by(AuditEvent.id.desc())
        .limit(200)
        .all()
    )

    return {"items": AuditEventSchema(many=True).dump(events)}