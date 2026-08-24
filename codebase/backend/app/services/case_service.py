"""
case_service.py — case CRUD + the case-scoped access checks that the whole system relies on.

ACCESS HELPERS (used by documents/search/audit too):
    user_has_access(user_id, case_id) -> bool
    get_case_for_user(case_id, user_id) -> Case | aborts 404   (404, NOT 403, for non-members)
    get_user_role_in_case(user_id, case_id) -> str | None
    get_accessible_case_ids(user_id) -> list[str]              (SUPER_ADMIN -> all)

CRUD:
    create_case(data, creator) -> Case         (auto-adds creator as CASE_OFFICER member)
    list_cases(user, filters, page, limit) -> dict
    update_case(case_id, data, actor) -> Case  (enforces valid status transitions)
    add_member(case_id, user_id, role, actor) -> CaseMember
    remove_member(case_id, user_id, actor) -> None
        Guards: cannot remove the last active CASE_OFFICER; cannot remove self.

STORES: rows in cases + case_members.
Full rules: ../../feature_plans/case_management_plan.md
"""


def user_has_access(user_id: str, case_id: str) -> bool:
    raise NotImplementedError


def get_case_for_user(case_id: str, user_id: str):
    raise NotImplementedError


def get_user_role_in_case(user_id: str, case_id: str):
    raise NotImplementedError


def get_accessible_case_ids(user_id: str) -> list[str]:
    raise NotImplementedError


def create_case(data: dict, creator):
    raise NotImplementedError


def list_cases(user, filters: dict, page: int, limit: int) -> dict:
    raise NotImplementedError


def update_case(case_id: str, data: dict, actor):
    raise NotImplementedError


def add_member(case_id: str, user_id: str, role: str, actor):
    raise NotImplementedError


def remove_member(case_id: str, user_id: str, actor) -> None:
    raise NotImplementedError
