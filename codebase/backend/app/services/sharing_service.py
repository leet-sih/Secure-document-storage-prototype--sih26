"""
sharing_service.py — time-limited external share links.

create_share(document_id, creator, opts) -> (DocumentShareLink, raw_token)
    token = secrets.token_urlsafe(32); store SHA256(token) only. RETURNS raw token ONCE.
access_share(token, email=None) -> Document
    Hash token -> atomic conditional UPDATE (increment use_count only if not
    revoked/expired/exhausted, race-safe RETURNING). Enforce optional email gate
    (case-insensitive). 410 on invalid/expired/exhausted; 403 on email mismatch; 404 unknown.
revoke_share(document_id, share_id, actor) -> None
    Only creator or SUPER_ADMIN. Sets is_revoked=True.
list_shares(document_id, actor) -> list

STORES: rows in document_share_links (token_hash only, never the raw token).
Full design + concurrency: ../../feature_plans/document_sharing_plan.md
"""


def create_share(document_id: str, creator, opts: dict):
    raise NotImplementedError


def access_share(token: str, email: str | None = None):
    raise NotImplementedError


def revoke_share(document_id: str, share_id: str, actor) -> None:
    raise NotImplementedError


def list_shares(document_id: str, actor) -> list:
    raise NotImplementedError
