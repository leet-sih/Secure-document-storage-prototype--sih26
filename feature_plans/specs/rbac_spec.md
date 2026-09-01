# Feature Spec: RBAC Enforcement

## 1. Purpose

Implement Role-Based Access Control (RBAC) across PRAMAAN using the existing authentication, MFA, and case-access systems.

This feature does NOT reimplement:
- Authentication
- TOTP / Step-up MFA
- Case management
- Case membership

RBAC is enforced at the backend API layer. Frontend role checks are only for user experience.

## 2. System Roles

- SUPER_ADMIN
- CASE_OFFICER
- INVESTIGATOR
- PROSECUTOR
- AUDITOR
- VIEWER

## 3. Permission Matrix

| Action | SUPER_ADMIN | CASE_OFFICER | INVESTIGATOR | PROSECUTOR | AUDITOR | VIEWER |
|---|---|---|---|---|---|---|
| Manage users | Yes | No | No | No | No | No |
| Upload case documents | Yes | Yes | No | No | No | No |
| Download accessible case documents | Yes | Yes | Yes | Yes | No | No |
| Delete case documents | Yes | Yes | No | No | No | No |
| Sign documents | Yes | Yes | Yes | No | No | No |
| Share documents | Yes | Yes | No | No | No | No |
| View system audit | Yes | No | No | No | Yes | No |
| Verify audit chain | Yes | No | No | No | Yes | No |

## 4. Security Rules

1. Backend authorization is authoritative.
2. A global role failure returns 403.
3. An inaccessible case-scoped resource returns 404.
4. Role possession alone does not grant access to an unrelated case.
5. Existing case-access helpers must be reused.
6. Existing step-up MFA must be reused for sensitive operations.
7. Users cannot change their own role or department.
8. Unauthorized security-relevant attempts are audited.

## 5. Files in Scope

### Backend
- `backend/app/core/rbac.py`
- `backend/app/blueprints/users.py`
- `backend/app/services/user_service.py`
- `backend/app/schemas/user_schemas.py`
- `backend/app/blueprints/documents.py`
- `backend/app/blueprints/audit.py`
- `backend/app/blueprints/signatures.py`
- `backend/app/blueprints/sharing.py`

### Tests
- RBAC/user authorization tests added under `backend/tests/` as required.

Files that already correctly enforce the required authorization policy will not be modified.

## 6. Review

### Security
- RBAC is enforced on the backend, never only through the frontend.
- Case membership checks remain separate from global role checks.
- Inaccessible case-scoped resources return 404 to prevent resource enumeration.
- Role and account-status changes are restricted to SUPER_ADMIN.
- Existing MFA protection is preserved.

### Conflict Check
- Authentication and MFA logic will not be rewritten.
- Case management and case membership logic will not be rewritten.
- Existing `require_roles()` and case-access helpers will be reused.
- Only files requiring RBAC enforcement will be changed.

### Main Risks
- Privilege escalation through user update endpoints.
- Access to documents outside assigned cases.
- Frontend restrictions being mistaken for security.
- Accidentally weakening existing MFA or case-access checks.

### Mitigation
- Validate all update bodies with Marshmallow `unknown=RAISE`.
- Enforce roles at API endpoints.
- Reuse existing case-access helpers.
- Test allowed and denied actions for every affected role.