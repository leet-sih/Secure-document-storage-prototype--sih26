# src/components/ — reusable UI components

Presentational + small stateful widgets shared across pages. No direct Axios calls (take
data/handlers via props, or use a hook).

| Component | Responsibility |
|-----------|----------------|
| `ProtectedRoute.tsx` | Route guard: redirect to /login if anon, /change-password if isFirstLogin, /mfa-setup if MFA missing; optional `roles` prop for role-gated routes. |
| `AppShell.tsx` | Top nav + sidebar layout wrapper for authenticated pages. |
| `CaseCard.tsx` | Case summary card (status/priority badges, counts). |
| `StatusBadge.tsx` | Color-coded case status pill. |
| `DocumentUploader.tsx` | Drag-and-drop upload with XHR progress; client-side type/size check before POST. |
| `DocumentList.tsx` | Table of documents with type/date filters + download/delete actions. |
| `SignaturePanel.tsx` | List signatures + validity badges + "Verify" + "Sign" buttons. |
| `ShareModal.tsx` | Create share link; show the raw URL ONCE with a copy button + "won't be shown again". |
| `AuditTable.tsx` | Paginated audit rows, severity color-coding, detail modal. |
| `ChainVerifyBadge.tsx` | Calls GET /audit/verify; shows "Chain Valid ✓" or "TAMPERING DETECTED ✗". |
| `SessionTimeout.tsx` | Warns ~2 min before access-token expiry; refreshes on activity. |
| `ConfirmModal.tsx` | Generic destructive-action confirmation. |

SEVERITY COLORS (AuditTable): green=normal, yellow=access/share, orange=delete/role change,
red=UNAUTHORIZED_ACCESS_ATTEMPT / INTEGRITY_VIOLATION / AUDIT_CHAIN_BROKEN / LOGIN_FAILED.
