/**
 * ProtectedRoute.tsx — gate for authenticated routes.
 *
 * BEHAVIOUR (order matters):
 *   - status "loading"          -> spinner (session bootstrap in flight).
 *   - status "anon"             -> <Navigate to="/login">.
 *   - user.isFirstLogin         -> <Navigate to="/change-password"> (unless already there).
 *   - !user.mfaEnabled          -> <Navigate to="/mfa-setup"> (unless already there).
 *   - `roles` set & role not in it -> 403 view.
 *   - otherwise                 -> render children.
 *
 * The pathname checks let the same guard wrap the onboarding pages (/change-password,
 * /mfa-setup) without redirecting them to themselves.
 *
 * Usage: <ProtectedRoute roles={["SUPER_ADMIN","AUDITOR"]}><AuditPage/></ProtectedRoute>
 */
import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useAuth } from "../store/AuthContext";
import type { Role } from "../types";

interface Props {
  children: ReactNode;
  roles?: Role[];
}

export default function ProtectedRoute({ children, roles }: Props) {
  const { user, status } = useAuth();
  const { pathname } = useLocation();

  if (status === "loading") {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#0a0c10",
          color: "#8b8fa8",
          fontSize: 13,
        }}
      >
        Loading…
      </div>
    );
  }

  if (status === "anon" || !user) {
    return <Navigate to="/login" replace />;
  }

  if (user.isFirstLogin && pathname !== "/change-password") {
    return <Navigate to="/change-password" replace />;
  }

  if (!user.mfaEnabled && pathname !== "/mfa-setup" && pathname !== "/change-password") {
    return <Navigate to="/mfa-setup" replace />;
  }

  if (roles && !roles.includes(user.role)) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 8,
          background: "#0a0c10",
          color: "#e8eaf0",
        }}
      >
        <div style={{ fontSize: 17, fontWeight: 600 }}>403 — Access denied</div>
        <div style={{ fontSize: 13, color: "#8b8fa8" }}>
          Your role does not permit access to this page.
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
