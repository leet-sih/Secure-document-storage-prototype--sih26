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

## Screen JSX reference files

These extracted JSX files in `design/screens/` are for agent reference. Read the matching
file before implementing any page — it contains the exact layout, colors, and component
structure to reproduce in React/TypeScript.

| Screen | JSX reference file |
|---|---|
| Login + MFA step | design/screens/LoginPage.jsx |
| MFA setup | design/screens/MfaSetupPage.jsx |
| Public share access | design/screens/ShareAccessPage.jsx |
| App shell (top bar) | design/screens/AppShell.jsx |
| Dashboard | design/screens/DashboardPage.jsx |
| Case detail | design/screens/CaseDetailPage.jsx |
| Documents tab | design/screens/DocumentsTab.jsx |
| Activity tab | design/screens/ActivityTab.jsx |
| Members tab | design/screens/MembersTab.jsx |
| Overview tab | design/screens/OverviewTab.jsx |
| Document detail panel | design/screens/DocumentDetailPanel.jsx |
| Search | design/screens/SearchPage.jsx |
| Audit log | design/screens/AuditPage.jsx |
| User admin | design/screens/UserAdminPage.jsx |
| Profile | design/screens/ProfilePage.jsx |
| Step-up MFA modal | design/screens/StepUpMfaModal.jsx |
| Share modal | design/screens/ShareModal.jsx |
| Create case modal | design/screens/CreateCaseModal.jsx |
| Create user modal | design/screens/CreateUserModal.jsx |
| Edit role modal | design/screens/EditRoleModal.jsx |
| Confirm modal | design/screens/ConfirmModal.jsx |
| Design tokens | design/screens/tokens.js |
