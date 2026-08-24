# Feature Plan: User Management

## What Is This Feature?

User management covers the lifecycle of system accounts: creation, role assignment, deactivation, and profile management. There is no self-registration — every account must be created by a SUPER_ADMIN. This is a closed, invite-only system for government personnel.

---

## Why No Self-Registration?

This system serves law enforcement and legal institutions. An open registration flow would:
- Allow unauthorized parties to create accounts and probe the system
- Bypass the vetting process for sensitive access
- Create orphan accounts not tied to a real verified employee

Instead: HR or IT admin creates accounts, sets an initial password, and the user is forced to change it on first login and set up MFA.

---

## Database Schema

```sql
CREATE TABLE users (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email               TEXT NOT NULL UNIQUE,
    password_hash       TEXT NOT NULL,
    full_name           TEXT NOT NULL,
    employee_id         TEXT UNIQUE,                    -- government employee ID
    phone               TEXT,                           -- for future OTP fallback
    role                TEXT NOT NULL,
    department_id       UUID NOT NULL REFERENCES departments(id),
    totp_secret         TEXT,                           -- AES-encrypted
    totp_secret_pending TEXT,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    is_first_login      BOOLEAN NOT NULL DEFAULT TRUE,  -- force password change
    failed_logins       INTEGER NOT NULL DEFAULT 0,
    locked_until        TIMESTAMPTZ,
    last_login_at       TIMESTAMPTZ,
    password_changed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          UUID REFERENCES users(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_role CHECK (role IN (
        'SUPER_ADMIN', 'CASE_OFFICER', 'INVESTIGATOR',
        'PROSECUTOR', 'AUDITOR', 'VIEWER'
    ))
);

-- Prevent anyone from being their own creator except the genesis admin
ALTER TABLE users ADD CONSTRAINT chk_no_self_creation
    CHECK (created_by IS NULL OR created_by != id);
```

---

## Roles — Detailed Permissions

| Role | Can Create Cases | Can Upload Docs | Can Download Docs | Can Delete Docs | Can Sign Docs | Can View Audit | Can Manage Users |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| SUPER_ADMIN | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| CASE_OFFICER | ✓ | ✓ | ✓ | ✓ | ✓ | own cases | — |
| INVESTIGATOR | — | — | ✓ (assigned) | — | ✓ | own cases | — |
| PROSECUTOR | — | — | ✓ (shared) | — | — | — | — |
| AUDITOR | — | — | — | — | — | ✓ (all) | — |
| VIEWER | — | — | ✓ (link only) | — | — | — | — |

---

## API Endpoints

### POST /api/v1/users `[SUPER_ADMIN]`

Creates a new user. Initial password is temporary — user must change on first login.

```json
// Request
{
  "email": "investigator@ncrb.gov.in",
  "full_name": "Arjun Sharma",
  "employee_id": "NCRB-2024-1042",
  "role": "INVESTIGATOR",
  "department_id": "uuid"
}

// Response 201
{
  "id": "uuid",
  "email": "investigator@ncrb.gov.in",
  "full_name": "Arjun Sharma",
  "role": "INVESTIGATOR",
  "department": { "id": "...", "name": "Cybercrime Unit" },
  "is_active": true,
  "temporary_password": "Tmp!Abc123Xyz"   ← only shown once, on creation
}
```

Server:
1. Generate a secure temporary password (16 chars, mixed case/digit/special)
2. Hash with bcrypt (cost 12)
3. Set `is_first_login=True`
4. Record AuditEvent: USER_CREATED with metadata `{created_by, role, department}`
5. Return temporary password in response — never stored in plaintext again

### GET /api/v1/users `[SUPER_ADMIN]`

List all users with filters: `role`, `department_id`, `is_active`, `search` (name/email/employee_id)

```json
{
  "items": [
    {
      "id": "...",
      "email": "...",
      "full_name": "...",
      "employee_id": "...",
      "role": "INVESTIGATOR",
      "department": { "id": "...", "name": "..." },
      "is_active": true,
      "last_login_at": "2026-08-24T09:00:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "pages": 1
}
```

### GET /api/v1/users/{id} `[SUPER_ADMIN, or self]`

A user can view their own profile. SUPER_ADMIN can view any.

### PATCH /api/v1/users/{id} `[SUPER_ADMIN]`

Updatable by admin: `role`, `department_id`, `is_active`, `full_name`

Role change records AuditEvent: ROLE_CHANGED
Deactivation records AuditEvent: USER_DEACTIVATED — and immediately invalidates all their Redis refresh tokens.

### PATCH /api/v1/users/me `[All authenticated]`

Self-service updates: `full_name`, `phone`
Users cannot change their own role or department.

### POST /api/v1/users/me/change-password `[All authenticated]`

```json
// Request
{
  "current_password": "...",
  "new_password": "NewStr0ng!Pass#"
}
```

Validation:
- `current_password` must verify against stored hash
- `new_password` must meet strength policy (see auth_plan.md)
- `new_password` must not equal `current_password`

On success:
- Update hash
- Set `is_first_login=False`
- Set `password_changed_at=now()`
- Invalidate all refresh tokens for this user (force re-login everywhere)
- Record AuditEvent: PASSWORD_CHANGED

### GET /api/v1/users/me `[All authenticated]`

```json
{
  "id": "...",
  "email": "...",
  "full_name": "...",
  "role": "CASE_OFFICER",
  "department": { "id": "...", "name": "..." },
  "mfa_enabled": true,
  "is_first_login": false,
  "last_login_at": "..."
}
```

---

## First Login Flow

```
User receives temporary password via admin (email/in-person)
  ↓
User logs in with email + temp password
  ↓
Server: is_first_login == True
  → Issue a restricted token (claim: {"scope": "password_change_only"})
  → Frontend: redirect to /change-password (cannot access any other page)
  ↓
User sets a new password via POST /users/me/change-password
  ↓
Server: is_first_login = False, invalidate restricted token
  → Redirect to MFA setup (if totp_secret is NULL)
  ↓
User scans QR code with authenticator app
  → POST /auth/mfa/confirm with first valid code
  ↓
Full access granted, normal JWT pair issued
```

---

## User Deactivation

When a user is deactivated (`is_active=False`):
1. All Redis refresh tokens for this user are deleted: `DEL refresh:{user_id}:*`
2. The user's current access token will fail validation on its next request (middleware checks `is_active`)
3. The user's case memberships remain (for audit trail integrity — historical events still point to their ID)
4. The user cannot log in again until reactivated

A deactivated user who tries to log in gets: `403 "Account is deactivated. Contact your administrator."`

---

## Password Policy

```
Minimum length: 12 characters
Must contain:
  - At least 1 uppercase letter (A-Z)
  - At least 1 lowercase letter (a-z)
  - At least 1 digit (0-9)
  - At least 1 special character (!@#$%^&*...)

Must NOT contain:
  - The user's email address or any part of it
  - The user's full name or any part of it
  - Common passwords (check against a top-10000 list)
  - The previous password

Maximum length: 128 characters (truncation attacks)
bcrypt cost factor: 12 (balances security vs. login latency ~200ms)
```

---

## marshmallow Schemas

```python
class UserCreateSchema(Schema):
    email        = fields.Email(required=True)
    full_name    = fields.Str(required=True, validate=validate.Length(min=2, max=200))
    employee_id  = fields.Str(load_default=None, validate=validate.Length(max=50))
    role         = fields.Str(required=True, validate=validate.OneOf([
                     'SUPER_ADMIN', 'CASE_OFFICER', 'INVESTIGATOR',
                     'PROSECUTOR', 'AUDITOR', 'VIEWER'
                   ]))
    department_id = fields.UUID(required=True)

class UserPatchSchema(Schema):
    # Admin patch
    role          = fields.Str(validate=validate.OneOf([...]))
    department_id = fields.UUID()
    is_active     = fields.Bool()
    full_name     = fields.Str(validate=validate.Length(min=2, max=200))

class UserSelfPatchSchema(Schema):
    # Self-service patch (no role/dept/active changes)
    full_name     = fields.Str(validate=validate.Length(min=2, max=200))
    phone         = fields.Str(validate=validate.Regexp(r'^\+?[\d\s\-]{7,15}$'))

class UserResponseSchema(Schema):
    id            = fields.UUID(dump_only=True)
    email         = fields.Str(dump_only=True)
    full_name     = fields.Str(dump_only=True)
    employee_id   = fields.Str(dump_only=True)
    role          = fields.Str(dump_only=True)
    department    = fields.Nested(DepartmentSchema, dump_only=True)
    is_active     = fields.Bool(dump_only=True)
    mfa_enabled   = fields.Method("get_mfa_status", dump_only=True)
    last_login_at = fields.DateTime(dump_only=True)

    def get_mfa_status(self, obj):
        return obj.totp_secret is not None
    # Note: never dump totp_secret itself
```

---

## Frontend Components

| Component | Route | Description |
|-----------|-------|-------------|
| `UserManagementPage` | `/admin/users` | Table of all users; filter by role/dept/status |
| `CreateUserModal` | `/admin/users` | Form; shows temporary password after creation (one-time display) |
| `UserDetailPage` | `/admin/users/{id}` | View + edit role, department, active status |
| `DeactivateConfirmModal` | — | "Deactivating this user will immediately revoke their session. Confirm?" |
| `ProfilePage` | `/profile` | Self-service: view own info, change password, MFA status |
| `ChangePasswordPage` | `/change-password` | Forced on first login; password strength meter |
| `ForceFirstLoginGuard` | Global | Middleware component that redirects to /change-password if `is_first_login` |

---

## Temporary Password Generation

```python
import secrets
import string

def generate_temporary_password(length=16) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        # Ensure it meets policy
        has_upper   = any(c.isupper() for c in password)
        has_lower   = any(c.islower() for c in password)
        has_digit   = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*" for c in password)
        if has_upper and has_lower and has_digit and has_special:
            return password
```

---

## Edge Cases

| Scenario | Behaviour |
|----------|-----------|
| Admin creates user with existing email | 409 "Email already registered" |
| Admin creates user with existing employee_id | 409 "Employee ID already in use" |
| Admin deactivates themselves | 400 "Cannot deactivate your own account" |
| Admin changes role of user who is mid-session | Their current access token retains old role until expiry (15 min max). Acceptable for prototype; for production, add role claim to refresh check. |
| User tries to change their own role via PATCH /users/me | marshmallow UserSelfPatchSchema does not include `role` — field is silently ignored (or return 400 if unexpected fields are strict) |
| User with active cases is deactivated | Case memberships soft-remain. CASE_OFFICER must appoint a replacement. |
| SUPER_ADMIN changes their own role away from SUPER_ADMIN | 400 "Cannot demote yourself. Assign SUPER_ADMIN to another user first." |

---

## Testing Plan

```
tests/users/
├── test_user_create.py
│   ├── test_super_admin_can_create_user
│   ├── test_non_admin_cannot_create_user
│   ├── test_duplicate_email_returns_409
│   ├── test_temporary_password_meets_policy
│   ├── test_is_first_login_set_on_creation
│   └── test_create_records_audit_event
├── test_first_login.py
│   ├── test_first_login_issues_restricted_token
│   ├── test_restricted_token_cannot_access_cases
│   ├── test_password_change_clears_first_login_flag
│   └── test_mfa_setup_required_after_password_change
├── test_user_patch.py
│   ├── test_admin_can_change_role
│   ├── test_role_change_records_audit_event
│   ├── test_deactivation_revokes_tokens
│   ├── test_deactivated_user_cannot_login
│   └── test_admin_cannot_deactivate_self
├── test_password_change.py
│   ├── test_valid_password_change
│   ├── test_weak_password_rejected
│   ├── test_wrong_current_password_rejected
│   └── test_password_change_invalidates_sessions
```

---

## Implementation Order

1. `Department` model + seed data migration
2. `User` SQLAlchemy model + migration
3. `user_schemas.py` — marshmallow schemas (create, patch, response)
4. `user_service.py` — create_user, deactivate_user, change_password
5. `users.py` Blueprint — all user routes
6. First login guard middleware
7. Frontend: UserManagementPage + CreateUserModal
8. Frontend: ProfilePage + ChangePasswordPage + ForceFirstLoginGuard
9. Tests
