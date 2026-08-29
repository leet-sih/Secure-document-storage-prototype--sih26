# Auth frontend wire-up + admin-created signup

## What and why

Wire the existing (backend-only) TOTP auth to the React frontend, and add the one
missing backend piece the flow needs: **admin-created user accounts** ("signup is by
admin, not self-service") plus the **first-login change-password** step. After this
change the full auth journey works end-to-end against the Flask API:

1. **Admin creates a user** (SUPER_ADMIN only) → server generates a one-time temporary
   password shown once.
2. New user **logs in** with the temp password → gets an access token flagged
   `mfa_setup_required`, `is_first_login=true`.
3. Forced **change password** (first login).
4. Forced **MFA (TOTP) setup** — scan QR / enter key → confirm 6-digit code.
5. Thereafter: login → password → **6-digit TOTP** → session.

Self-service signup is intentionally NOT added — accounts are provisioned by an admin.

**Out of this feature:** edit-role / deactivate row actions on the admin table (backend
`update_user`/`deactivate_user` stay stubbed — deferred to `docs/TODO.md`), the real
dashboard/case UI, step-up modal, AppShell chrome, WebAuthn.

## Exact files

**Backend — modify**
- `app/blueprints/users.py` — add `POST /users`, `GET /users`, `GET /users/departments`, `POST /users/me/change-password` (keep existing `GET /me`).
- `app/services/user_service.py` — implement `create_user`, `list_users`, `get_user`, `change_password` (leave `update_user`, `deactivate_user` stubbed — deferred).
- `app/schemas/user_schemas.py` — add `DepartmentSchema` (id, name, dept_type).
- `seed.py` — add a SUPER_ADMIN + seed the three demo departments, so the admin-only
  create-user flow is reachable out of the box (the existing seed only makes a CASE_OFFICER).
- `docs/TODO.md` — note deferred edit-role/deactivate row actions.

**Frontend — create**
- `src/pages/MfaSetupPage.tsx`, `src/pages/ChangePasswordPage.tsx`, `src/pages/UserAdminPage.tsx`, `src/pages/DashboardPage.tsx` (minimal authed landing).

**Frontend — modify**
- `src/lib/apiClient.ts` — export `ApiError { status, code, message }`; skip the auto clear+redirect for `/auth/*` 401s and for `code === "MFA_REQUIRED"`; always throw `ApiError` so callers can read the code/message.
- `src/hooks/useAuth.ts` — implement `useAuthActions()` (login, verifyMfa, setupMfa, confirmMfa, changePassword, logout, bootstrap). Renamed from the placeholder `useAuth` to avoid colliding with `AuthContext`'s state hook.
- `src/store/AuthContext.tsx` — add `SET_USER` action + `setUser(user)` (update `user` without rewriting the token; used after change-password / MFA confirm / bootstrap).
- `src/components/ProtectedRoute.tsx` — implement redirects (loading→spinner, anon→/login, isFirstLogin→/change-password, !mfaEnabled→/mfa-setup, role gate).
- `src/App.tsx` — wire routes + `bootstrap()` on mount.
- `src/pages/LoginPage.tsx` — implement two-step credentials→TOTP form.
- `src/types/index.ts` — add `Department`, `AdminUser`, `LoginResult`, `MfaSetupResult`, `CreateUserResult`.

No other files. No new dependencies. No DB migration (all columns exist in `001_auth_totp.py`).

## Data model

No schema change. Uses existing `users` columns (`is_first_login`, `password_changed_at`,
`totp_secret*`) and `departments`. `department_id`→name mapping is done client-side from
`GET /users/departments` (avoids adding a relationship/serializer to the User model).

## API contract

| Method | Path | Auth | Body | Success |
|--------|------|------|------|---------|
| POST | `/api/v1/users` | SUPER_ADMIN | `{email, full_name, role, department_id, employee_id?}` | 201 `{user, temp_password}` |
| GET | `/api/v1/users` | SUPER_ADMIN | — | 200 `{users: [UserResponse...]}` |
| GET | `/api/v1/users/departments` | SUPER_ADMIN | — | 200 `{departments: [{id,name,dept_type}]}` |
| POST | `/api/v1/users/me/change-password` | access JWT (not `purpose=mfa`) | `{current_password, new_password}` | 204 |
| GET | `/api/v1/users/me` | access JWT | — | 200 UserResponse (existing) |

Errors: 400 `VALIDATION_ERROR`; 401 `UNAUTHORIZED` (wrong current password); 403 `FORBIDDEN`
(not admin); 404 `NOT_FOUND` (department missing); 409 `CONFLICT` (email/employee_id taken).
`temp_password` is returned exactly once, never stored in plaintext, never logged.

## Security threat model

- All `/users` admin routes gated by `require_roles(Role.SUPER_ADMIN)` (403 on miss + `UNAUTHORIZED_ACCESS_ATTEMPT` audit). These are system-global (not case-scoped), so 403 (not 404) is correct.
- `change-password` gated by `require_access_jwt` (rejects `purpose=mfa` temp tokens); verifies `current_password` before applying; strength enforced by `PasswordChangeSchema`; new must differ from current.
- Temp password: generated with `secrets`, 16 chars covering all policy classes, bcrypt-hashed immediately (≤72 bytes), returned once, `is_first_login=True`.
- New users receive a real access token pre-MFA (needed to reach change-password/mfa-setup); UI gates them to those pages only, and `require_recent_mfa` endpoints stay blocked (`mfa_at=0`). Matches the existing `auth_totp` decision (spec §3.7).
- No document/PII content logged — only IDs + event types (`USER_CREATED`, `PASSWORD_CHANGED`).
- Frontend never logs tokens/passwords; temp password shown once in the modal and not persisted.

## Edge cases (`docs/EDGE_CASES.md`)

- 3.2 deactivated account → `authenticate` already returns 403; `/me` 401 clears session.
- 3.4 bcrypt 72-byte cap — enforced in `hash_password` and `PasswordChangeSchema`.
- 3.7 first-login: `is_first_login` + `mfa_enabled` from `/me` drive the forced-redirect order (password → MFA) in `ProtectedRoute`.
- Duplicate email/employee_id → 409 (no partial row; check before insert / catch IntegrityError).
- Login bad creds returns 401 from `/auth/*`; apiClient must NOT treat that as session-expiry (no redirect loop) — LoginPage shows the message.

## Assumptions

- Vite proxies `/api` → Flask `:5000` (confirmed in `vite.config.ts`).
- After change-password and MFA confirm, the client re-fetches `/me` (bootstrap) to refresh `is_first_login`/`mfa_enabled` rather than trusting local flips.
- Styling uses inline design tokens (matches the prototype authoring style and guarantees pixel match) rather than Tailwind classes.

## Review

1. **Security holes?** Temp password is the main sensitive value — generated server-side, hashed at once, returned once, never logged; admin-only creation. Wrong-current-password on change returns 401 without leaking. Pre-MFA access token is scoped by UI + `require_recent_mfa`; consistent with existing auth. No new plaintext secret at rest.
2. **Contradicts CLAUDE.md / SECURITY.md / plans?** No. Uses `require_roles`, marshmallow `unknown=RAISE` schemas (no `request.json` misuse), parameterized ORM, audit events from the canonical enum. `require_roles` returns 403 (allowed — not a case-scoped resource, so the 404 rule doesn't apply). Inline styles are permitted by the design workflow (github.md authored the prototype the same way).
3. **Simpler design?** Client-side `department_id`→name mapping avoids a User serializer/relationship change. Reusing `bootstrap()` after each forced step avoids a bespoke user-patch protocol. Renaming the actions hook (`useAuthActions`) resolves the pre-existing `useAuth` name collision with minimal churn.
4. **EDGE_CASES handled?** 3.2, 3.4, 3.7, duplicate-key, and the 401-on-auth-endpoint redirect trap — all covered above.
5. **Breaks existing?** `apiClient` throw type changes from `Error` to `ApiError` (subclass of `Error`) — all current callers are stubs, so no runtime break; message still readable. Backend adds routes only; `GET /me` untouched. Registering `""` collection routes under the `/api/v1/users` prefix does not collide with `/me`, `/departments`, or `/me/change-password`.

## Later (not this branch)

- `PATCH /users/{id}` edit-role + `deactivate_user` wired to the admin table row actions (backend stubs already present) — tracked in `docs/TODO.md`.
- Step-up MFA modal on sensitive actions; AppShell chrome; real dashboard.
