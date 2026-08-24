"""
blueprints/ — HTTP route handlers. Thin: validate -> call service -> serialize -> audit.

Registered under /api/v1 in app.create_app(). Each blueprint owns one resource:

    auth_bp          /api/v1/auth/*          login, MFA, refresh, logout        (public + auth)
    users_bp         /api/v1/users/*         user admin + self profile
    cases_bp         /api/v1/cases/*         case CRUD + members + timeline
    documents_bp     /api/v1/...             upload/list/download/preview/delete
    audit_bp         /api/v1/audit/*         audit log + chain verify
    signatures_bp    /api/v1/documents/*/signatures
    sharing_bp       /api/v1/documents/*/share (authenticated owner side)
    share_access_bp  /api/v1/share/*         PUBLIC (no JWT) external download
    search_bp        /api/v1/documents/search

CHECKLIST for every handler: @jwt_required (unless public) -> @require_roles ->
schema.load(request) -> service call -> schema.dump -> audit_service.record(...).
"""
