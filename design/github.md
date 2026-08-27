repo: leet-sih/Secure-document-storage-prototype--sih26
branch: main
path: codebase/frontend

## Last sync
date: 2026-08-27T00:00:00Z

### Updated in this project
- Built "PRAMAAN Prototype.dc.html" — clickable front-end prototype covering login + MFA, MFA setup, dashboard, case detail (4 tabs), search, user admin, profile, public share access.
- Confirmed the repo's frontend is scaffolding only (pages/components return null / TODO), so screens were authored from the PRAMAAN design context doc, matching the repo's declared types and route map.
- Design tokens (dark palette, Inter / JetBrains Mono, Lucide icon set) applied as inline styles; no backend calls — all state is local mock data.

## Screen map
| Project screen | Repo files it corresponds to |
|---|---|
| Login + MFA step | codebase/frontend/src/pages/LoginPage.tsx |
| MFA setup | codebase/frontend/src/pages/MfaSetupPage.tsx |
| Dashboard (case list) | codebase/frontend/src/pages/DashboardPage.tsx, components/CaseCard.tsx |
| Case detail (Documents / Activity / Members / Overview) | codebase/frontend/src/pages/CaseDetailPage.tsx, components/DocumentList.tsx, DocumentUploader.tsx, DocumentDetailPanel.tsx |
| Search | codebase/frontend/src/pages/SearchPage.tsx |
| Audit log | codebase/frontend/src/pages/AuditPage.tsx, components/ChainVerifyBadge.tsx, AuditTable.tsx |
| User admin | codebase/frontend/src/pages/UserAdminPage.tsx |
| Profile | codebase/frontend/src/pages/ProfilePage.tsx |
| Share access (public) | codebase/frontend/src/pages/ShareAccessPage.tsx |
| Shell (top bar + sidebar) | codebase/frontend/src/components/AppShell.tsx |
| Step-up MFA / Share / Confirm modals | codebase/frontend/src/components/StepUpMfaModal.tsx, ShareModal.tsx, ConfirmModal.tsx |
| Types & routes reference | codebase/frontend/src/types/index.ts, src/App.tsx |
