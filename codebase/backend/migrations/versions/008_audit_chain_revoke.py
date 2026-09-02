"""Revoke UPDATE and DELETE on audit_events from the app DB user.

Revision ID: 008_audit_chain_revoke
Revises: 007_encrypt_ocr_text_fields
Create Date: 2026-09-02

audit_events is append-only by design. The application user must never be able
to silently edit or remove a row — tampering must require superuser access, which
makes it detectable (DB-level auth logs + the hash-chain verify endpoint).

This migration REVOKEs the two dangerous privileges from dms_app_user. The REVOKE
is read from the DB_APP_USER env var so it works in any environment without
hardcoding. It falls back to 'dms_app_user' (the prototype default).

Downgrade re-GRANTs the privileges (restoring the previous state) so rollback is
clean — but note that the chain's tamper-evidence guarantee no longer holds after
a downgrade.
"""

import os

from alembic import op

revision = "008_audit_chain_revoke"
down_revision = "007_encrypt_ocr_text_fields"
branch_labels = None
depends_on = None

_APP_USER = os.environ.get("DB_APP_USER", "dms_app_user")


def upgrade() -> None:
    op.execute(f'REVOKE UPDATE, DELETE ON audit_events FROM "{_APP_USER}"')


def downgrade() -> None:
    op.execute(f'GRANT UPDATE, DELETE ON audit_events TO "{_APP_USER}"')
