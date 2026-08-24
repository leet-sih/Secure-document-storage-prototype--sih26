"""
user_service.py — user lifecycle.

FUNCTIONS (see user_management_plan.md):
    create_user(data, created_by) -> (user, temporary_password)
        Generates a strong temp password, bcrypt-hashes it, is_first_login=True.
        RETURNS the temp password ONCE (never stored in plaintext).
    list_users(filters, page, limit) -> paginated dict
    get_user(user_id) -> user
    update_user(user_id, data, actor) -> user            (role/dept/active; guards self-demote)
    change_password(user, current, new) -> None
        Verifies current, applies policy, revokes ALL refresh tokens, clears is_first_login.
    deactivate_user(user_id, actor) -> None
        is_active=False + revoke all refresh tokens. Cannot deactivate self.

STORES: rows in users. Never returns password_hash/totp_secret to callers.
"""


def create_user(data: dict, created_by: str):
    raise NotImplementedError


def list_users(filters: dict, page: int, limit: int) -> dict:
    raise NotImplementedError


def get_user(user_id: str):
    raise NotImplementedError


def update_user(user_id: str, data: dict, actor):
    raise NotImplementedError


def change_password(user, current_password: str, new_password: str) -> None:
    raise NotImplementedError


def deactivate_user(user_id: str, actor) -> None:
    raise NotImplementedError
