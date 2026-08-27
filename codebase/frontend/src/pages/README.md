# src/pages/ — route-level components

One component per route. Pages compose components/, call hooks/, and never call apiFetch()
directly except through hooks or lib/apiClient. Each page owns its data fetching + loading/
error states.

| File | Route | Role | Responsibility |
|------|-------|------|----------------|
| `LoginPage.tsx` | `/login` | public | Email+password, then MFA code step. Handles `mfaSetupRequired` and `MFA_REQUIRED` step-up prompt. |
| `MfaSetupPage.tsx` | `/mfa-setup` | auth | Show QR + confirm code to activate MFA. |
| `ChangePasswordPage.tsx` | `/change-password` | auth | Forced on first login; strength meter. |
| `DashboardPage.tsx` | `/` | auth | Grid of accessible cases; create-case modal. |
| `CaseDetailPage.tsx` | `/cases/:id` | members | Documents list, upload, members, timeline tabs. |
| `SearchPage.tsx` | `/search` | auth | Search bar + filters + results (case-scoped). |
| `AuditPage.tsx` | `/audit` | SUPER_ADMIN, AUDITOR | Audit table + filters + "Verify chain" badge. |
| `UserAdminPage.tsx` | `/admin/users` | SUPER_ADMIN | User CRUD; shows temp password once on create. |
| `ProfilePage.tsx` | `/profile` | auth | Own info, change password, MFA status. |
| `ShareAccessPage.tsx` | `/share/:token` | PUBLIC | External download page (filename, expiry, optional email gate). |
| `NotFoundPage.tsx` | `*` | — | 404. |

RULES: never store document bytes in localStorage/sessionStorage; downloads go straight to
a browser download (blob URL revoked after use). Show 404-style "not found" for both missing
and forbidden case resources (backend returns 404 for non-members).
