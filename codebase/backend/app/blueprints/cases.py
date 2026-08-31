"""
cases.py — case management routes. Prefix: /api/v1/cases

Routes:
    POST   /                           -> create case (CASE_OFFICER, SUPER_ADMIN)
    GET    /                           -> list cases (any authenticated user)
    GET    /<case_id>                  -> get case detail (member or SUPER_ADMIN)
    PATCH  /<case_id>                  -> update case (CASE_OFFICER member or SUPER_ADMIN)
    POST   /<case_id>/members          -> add member (CASE_OFFICER member or SUPER_ADMIN)
    DELETE /<case_id>/members/<uid>    -> remove member (CASE_OFFICER member or SUPER_ADMIN)
    POST   /<case_id>/transfer         -> transfer case (requires recent MFA)
    GET    /<case_id>/transfer-options -> list depts + officers for transfer form
    GET    /<case_id>/timeline         -> audit timeline for this case
"""

from flask import Blueprint, request

from app.core.audit_events import AuditEventType
from app.core.rbac import Role, require_recent_mfa, require_roles
from app.core.security import current_user_required, require_access_jwt
from app.schemas.case_schemas import (
    CaseCreateSchema,
    CasePatchSchema,
    CaseDetailSchema,
    CaseListItemSchema,
    CaseMemberAddSchema,
    CaseMemberSchema,
    CaseTransferSchema,
    TimelineEventSchema,
    TransferOptionsSchema,
)
from app.services import case_service
from app.services.audit_service import audit_service

cases_bp = Blueprint("cases", __name__)


def _ip() -> str | None:
    return request.remote_addr


# ── Create ─────────────────────────────────────────────────────────────────────

@cases_bp.post("")
@require_roles(Role.SUPER_ADMIN, Role.CASE_OFFICER)
def create_case(current_user):
    data = CaseCreateSchema().load(request.get_json(silent=True) or {})
    detail = case_service.create_case(data, current_user)
    return CaseDetailSchema().dump(detail), 201


# ── List ───────────────────────────────────────────────────────────────────────

@cases_bp.get("")
@require_access_jwt
def list_cases():
    user = current_user_required()
    args = request.args
    filters = {
        "status": args.get("status"),
        "priority": args.get("priority"),
        "search": args.get("search"),
    }
    try:
        page = max(1, int(args.get("page", 1)))
        limit = min(100, max(1, int(args.get("limit", 20))))
    except ValueError:
        page, limit = 1, 20

    result = case_service.list_cases(user, filters, page, limit)
    return {
        "cases": CaseListItemSchema(many=True).dump(result["cases"]),
        "total": result["total"],
        "page": result["page"],
        "limit": result["limit"],
    }


# ── Detail ─────────────────────────────────────────────────────────────────────

@cases_bp.get("/<uuid:case_id>")
@require_access_jwt
def get_case(case_id):
    user = current_user_required()
    case = case_service.get_case_for_user(case_id, str(user.id))
    detail = case_service._build_detail(case)
    audit_service.record(
        AuditEventType.CASE_ACCESSED.value,
        actor_user_id=user.id,
        target_type="case",
        target_id=case_id,
        case_id=case_id,
        ip_address=_ip(),
    )
    return CaseDetailSchema().dump(detail)


# ── Update ─────────────────────────────────────────────────────────────────────

@cases_bp.patch("/<uuid:case_id>")
@require_access_jwt
def update_case(case_id):
    user = current_user_required()
    data = CasePatchSchema().load(request.get_json(silent=True) or {})
    detail = case_service.update_case(case_id, data, user)
    return CaseDetailSchema().dump(detail)


# ── Members ────────────────────────────────────────────────────────────────────

@cases_bp.post("/<uuid:case_id>/members")
@require_access_jwt
def add_member(case_id):
    user = current_user_required()
    data = CaseMemberAddSchema().load(request.get_json(silent=True) or {})
    member = case_service.add_member(case_id, data["user_id"], data["role"], user)
    return CaseMemberSchema().dump(member), 201


@cases_bp.delete("/<uuid:case_id>/members/<uuid:user_id>")
@require_access_jwt
def remove_member(case_id, user_id):
    user = current_user_required()
    case_service.remove_member(case_id, user_id, user)
    return ("", 204)


# ── Transfer ───────────────────────────────────────────────────────────────────

@cases_bp.post("/<uuid:case_id>/transfer")
@require_recent_mfa()
def transfer_case(current_user, case_id):
    data = CaseTransferSchema().load(request.get_json(silent=True) or {})
    detail = case_service.transfer_case(case_id, data, current_user)
    return CaseDetailSchema().dump(detail)


@cases_bp.get("/<uuid:case_id>/transfer-options")
@require_access_jwt
def transfer_options(case_id):
    user = current_user_required()
    case_service.get_case_for_user(case_id, str(user.id))  # access check
    opts = case_service.get_transfer_options()
    return TransferOptionsSchema().dump(opts)


# ── Timeline ───────────────────────────────────────────────────────────────────

@cases_bp.get("/<uuid:case_id>/timeline")
@require_access_jwt
def get_timeline(case_id):
    user = current_user_required()
    events = case_service.get_case_timeline(case_id, user)
    return {"events": TimelineEventSchema(many=True).dump(events)}
