/**
 * DashboardPage.tsx — "/" (auth)
 *
 * Minimal authenticated landing for the auth wire-up. The real case-list dashboard is a
 * later feature; this confirms a completed session and links admins to user management.
 */
import { useNavigate } from "react-router-dom";

import { useAuthActions } from "../hooks/useAuth";
import { useAuth } from "../store/AuthContext";

export default function DashboardPage() {
  const navigate = useNavigate();
  const { logout } = useAuthActions();
  const { user } = useAuth();

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#0a0c10",
        color: "#e8eaf0",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 16,
        padding: 24,
      }}
    >
      <div style={{ fontSize: 24, fontWeight: 700, letterSpacing: "0.18em" }}>PRAMAAN</div>
      <div style={{ fontSize: 14, color: "#8b8fa8" }}>
        Signed in as <span style={{ color: "#e8eaf0" }}>{user?.fullName}</span> · {user?.role}
      </div>

      <div style={{ display: "flex", gap: 10 }}>
        {user?.role === "SUPER_ADMIN" && (
          <button
            type="button"
            onClick={() => navigate("/admin/users")}
            style={{
              height: 34,
              padding: "0 14px",
              background: "#3b82f6",
              color: "#fff",
              border: "none",
              borderRadius: 4,
              fontSize: 14,
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            User Admin
          </button>
        )}
        <button
          type="button"
          onClick={() => logout().then(() => navigate("/login", { replace: true }))}
          style={{
            height: 34,
            padding: "0 14px",
            background: "#1a1d24",
            border: "1px solid #2a2d35",
            borderRadius: 4,
            color: "#e8eaf0",
            fontSize: 14,
            cursor: "pointer",
          }}
        >
          Sign out
        </button>
      </div>
    </div>
  );
}
