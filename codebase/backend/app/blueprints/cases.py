"""
cases.py — case CRUD, membership, timeline. Prefix: /api/v1/cases

ROUTES:
    POST /                        [SUPER_ADMIN, CASE_OFFICER]  create case
    GET  /                        [auth]     list cases the user can access (paginated)
    GET  /{id}                    [members]  detail (+ members + document summary); audit CASE_ACCESSED
    PATCH /{id}                   [CASE_OFFICER own, SUPER_ADMIN]  update / status transition
    POST /{id}/members            [CASE_OFFICER own, SUPER_ADMIN]  add member
    DELETE /{id}/members/{uid}    [CASE_OFFICER own, SUPER_ADMIN]  soft-remove member
    GET  /{id}/timeline           [members]  chronological case activity feed

Non-members receive 404 (never 403). Records CASE_CREATED / CASE_UPDATED / CASE_MEMBER_ADDED /
CASE_MEMBER_REMOVED. See case_management_plan.md.
"""

from flask import Blueprint

cases_bp = Blueprint("cases", __name__)

# TODO: implement routes.
# from app.core.rbac import require_roles, Role
# from app.schemas.case_schemas import CaseCreateSchema, CasePatchSchema, CaseMemberAddSchema, CaseResponseSchema
# from app.services import case_service
