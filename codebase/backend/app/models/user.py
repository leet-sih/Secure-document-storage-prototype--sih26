"""
User model — a system account.

STORES: identity, credential hash, role, MFA secret (encrypted), lockout counters,
and the Ed25519 signing PUBLIC key. NEVER stores: plaintext password, plaintext TOTP
secret, or the signing PRIVATE key (that lives in Vault/KMS).

KEY RULES:
    - password_hash: bcrypt (cost >= 12). Passwords capped at 72 bytes before hashing.
    - totp_secret / totp_secret_pending: AES-encrypted with app SECRET_KEY at rest.
    - is_first_login: forces password change + MFA setup before any other page.
    - deactivating (is_active=False) must also delete all refresh:{id}:* keys in Redis.

Full lifecycle: ../../feature_plans/user_management_plan.md
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import UUID
from app.extensions import db

ROLES = ("SUPER_ADMIN", "CASE_OFFICER", "INVESTIGATOR", "PROSECUTOR", "AUDITOR", "VIEWER")


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = db.Column(db.Text, nullable=False, unique=True)
    password_hash = db.Column(db.Text, nullable=False)
    full_name = db.Column(db.Text, nullable=False)
    employee_id = db.Column(db.Text, unique=True)
    phone = db.Column(db.Text)

    role = db.Column(db.Text, nullable=False)  # one of ROLES; enforced by CHECK in migration
    department_id = db.Column(UUID(as_uuid=True), db.ForeignKey("departments.id"), nullable=False)

    # ── MFA ──
    totp_secret = db.Column(db.Text)            # active, AES-encrypted
    totp_secret_pending = db.Column(db.Text)    # unconfirmed setup secret

    # ── Signing ──
    signing_public_key = db.Column(db.Text)     # hex Ed25519 public key (private key -> Vault)

    # ── State / lockout ──
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_first_login = db.Column(db.Boolean, nullable=False, default=True)
    failed_logins = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.DateTime(timezone=True))
    last_login_at = db.Column(db.DateTime(timezone=True))
    password_changed_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    @property
    def mfa_enabled(self) -> bool:
        return self.totp_secret is not None
