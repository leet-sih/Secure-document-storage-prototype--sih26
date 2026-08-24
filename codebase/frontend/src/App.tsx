/**
 * App.tsx — top-level routing + auth gating.
 *
 * WHAT IT DOES:
 *   - Defines all routes (React Router v6).
 *   - Wraps protected routes in <ProtectedRoute> (redirects to /login if unauthenticated,
 *     to /change-password if isFirstLogin, to /mfa-setup if MFA not yet configured).
 *   - Restores the session on first load via a silent refresh (useAuth.bootstrap()).
 *
 * ROUTE MAP (see each page file for its responsibility):
 *   /login                 LoginPage        (public)
 *   /mfa-setup             MfaSetupPage     (auth, first-time MFA)
 *   /change-password       ChangePasswordPage (auth, forced on first login)
 *   /                      DashboardPage    (auth) — case list
 *   /cases/:id             CaseDetailPage   (auth) — documents, members, timeline
 *   /search                SearchPage       (auth)
 *   /audit                 AuditPage        (auth, SUPER_ADMIN/AUDITOR)
 *   /admin/users           UserAdminPage    (auth, SUPER_ADMIN)
 *   /profile               ProfilePage      (auth)
 *   /share/:token          ShareAccessPage  (PUBLIC — external download)
 *   *                      NotFoundPage
 */
import { Routes, Route } from "react-router-dom";

// TODO: import pages from ./pages and a <ProtectedRoute> guard from ./components.

export default function App() {
  // TODO: const { bootstrap } = useAuth(); useEffect(() => { bootstrap(); }, []);
  return (
    <Routes>
      {/* TODO: wire the route map above. */}
    </Routes>
  );
}
