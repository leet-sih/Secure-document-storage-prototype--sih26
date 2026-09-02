/**
 * App.tsx — top-level routing + auth gating.
 *
 * ROUTE MAP:
 *   /login            LoginPage          (public)
 *   /change-password  ChangePasswordPage (auth, forced on first login)
 *   /mfa-setup        MfaSetupPage       (auth, forced until TOTP enrolled)
 *   /cases            DashboardPage      (auth, AppShell)
 *   /cases/:id        CaseDetailPage     (auth, AppShell)
 *   /admin/users      UserAdminPage      (auth, SUPER_ADMIN, AppShell)
 *   /                 -> /cases
 *   *                 -> /cases
 */
import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import AppShell from "./components/AppShell";
import ProtectedRoute from "./components/ProtectedRoute";
import { useAuthActions } from "./hooks/useAuth";
import CaseDetailPage from "./pages/CaseDetailPage";
import ChangePasswordPage from "./pages/ChangePasswordPage";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import MfaSetupPage from "./pages/MfaSetupPage";
import PersonalVaultPage from "./pages/PersonalVaultPage";
import ShareAccessPage from "./pages/ShareAccessPage";
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
      <Route path="/share/:token" element={<ShareAccessPage />} />
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
        path="/cases"
        element={
          <ProtectedRoute>
            <AppShell>
              <DashboardPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/cases/:id"
        element={
          <ProtectedRoute>
            <AppShell>
              <CaseDetailPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/my-documents"
        element={
          <ProtectedRoute>
            <AppShell>
              <PersonalVaultPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/users"
        element={
          <ProtectedRoute roles={["SUPER_ADMIN"]}>
            <AppShell>
              <UserAdminPage />
            </AppShell>
          </ProtectedRoute>
        }
      />
      <Route path="/" element={<Navigate to="/cases" replace />} />
      <Route path="*" element={<Navigate to="/cases" replace />} />
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
