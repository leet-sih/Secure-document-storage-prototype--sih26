/**
 * App.tsx — top-level routing + auth gating.
 *
 * WHAT IT DOES:
 *   - Wraps the tree in <AuthProvider> and restores the session on load (bootstrap()).
 *   - Defines routes (React Router v6); protected routes go through <ProtectedRoute>,
 *     which redirects to /login (anon), /change-password (isFirstLogin), or /mfa-setup
 *     (MFA not yet enrolled), and enforces role gates.
 *
 * ROUTE MAP (auth wire-up scope — case/search/audit/profile pages land in later features):
 *   /login            LoginPage          (public)
 *   /change-password  ChangePasswordPage (auth, forced on first login)
 *   /mfa-setup        MfaSetupPage       (auth, forced until TOTP enrolled)
 *   /admin/users      UserAdminPage      (auth, SUPER_ADMIN)
 *   /                 DashboardPage      (auth) — minimal landing
 *   *                 -> "/"
 */
import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import ProtectedRoute from "./components/ProtectedRoute";
import { useAuthActions } from "./hooks/useAuth";
import ChangePasswordPage from "./pages/ChangePasswordPage";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import MfaSetupPage from "./pages/MfaSetupPage";
import UserAdminPage from "./pages/UserAdminPage";
import { AuthProvider } from "./store/AuthContext";

function AppRoutes() {
  const { bootstrap } = useAuthActions();

  useEffect(() => {
    void bootstrap();
    // Run once on mount to restore the session from a stored token.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/change-password"
        element={
          <ProtectedRoute>
            <ChangePasswordPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/mfa-setup"
        element={
          <ProtectedRoute>
            <MfaSetupPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/users"
        element={
          <ProtectedRoute roles={["SUPER_ADMIN"]}>
            <UserAdminPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}
