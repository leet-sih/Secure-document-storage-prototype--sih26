/**
 * ProtectedRoute.tsx — gate for authenticated routes.
 *
 * BEHAVIOUR:
 *   - status "loading"  -> render a spinner (session bootstrap in flight).
 *   - status "anon"     -> <Navigate to="/login">.
 *   - user.isFirstLogin -> <Navigate to="/change-password"> (unless already there).
 *   - MFA not enabled    -> <Navigate to="/mfa-setup">.
 *   - `roles` prop set and user.role not in it -> render a 403/NotFound view.
 *   - otherwise          -> render children.
 *
 * Usage: <ProtectedRoute roles={["SUPER_ADMIN","AUDITOR"]}><AuditPage/></ProtectedRoute>
 */
import type { ReactNode } from "react";
import type { Role } from "../types";

interface Props {
  children: ReactNode;
  roles?: Role[];
}

export default function ProtectedRoute({ children, roles }: Props) {
  // TODO: read useAuthStore(); implement the redirects described above.
  void roles;
  return <>{children}</>;
}
