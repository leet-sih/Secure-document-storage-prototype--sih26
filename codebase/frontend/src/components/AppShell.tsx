import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  Shield,
  UserCircle,
  ChevronDown,
  LogOut,
  FolderOpen,
  Users,
  Vault,
} from "lucide-react";
import type { ReactNode } from "react";
import { useAuth } from "../store/AuthContext";
import { useAuthActions } from "../hooks/useAuth";

interface Props {
  children: ReactNode;
}

const ROLE_LABEL: Record<string, string> = {
  SUPER_ADMIN: "System Admin",
  CASE_OFFICER: "Case Officer",
  INVESTIGATOR: "Investigator",
  PROSECUTOR: "Prosecutor",
  AUDITOR: "Auditor",
  VIEWER: "Viewer",
};

export default function AppShell({ children }: Props) {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { user } = useAuth();
  const { logout } = useAuthActions();
  const [menuOpen, setMenuOpen] = useState(false);

  function isActive(path: string) {
    return pathname === path || pathname.startsWith(path + "/");
  }

  type NavItem = {
    label: string;
    icon: ReactNode;
    bar: string;
    color: string;
    go: () => void;
  };

  const navItems: NavItem[] = [
    {
      label: "Cases",
      icon: <FolderOpen size={16} />,
      bar: isActive("/cases") ? "#3b82f6" : "transparent",
      color: isActive("/cases") ? "#e8eaf0" : "#8b8fa8",
      go: () => navigate("/cases"),
    },
    {
      label: "My Vault",
      icon: <Vault size={16} />,
      bar: isActive("/my-documents") ? "#3b82f6" : "transparent",
      color: isActive("/my-documents") ? "#e8eaf0" : "#8b8fa8",
      go: () => navigate("/my-documents"),
    },
    ...(user?.role === "SUPER_ADMIN"
      ? [
          {
            label: "Users",
            icon: <Users size={16} />,
            bar: isActive("/admin/users") ? "#3b82f6" : "transparent",
            color: isActive("/admin/users") ? "#e8eaf0" : "#8b8fa8",
            go: () => navigate("/admin/users"),
          } as NavItem,
        ]
      : []),
  ];

  async function handleLogout() {
    setMenuOpen(false);
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div style={{ minHeight: "100vh", background: "#0a0c10", color: "#e8eaf0" }}>
      {/* ── Top bar ── */}
      <div
        style={{
          position: "sticky",
          top: 0,
          zIndex: 40,
          height: "56px",
          background: "#111318",
          borderBottom: "1px solid #2a2d35",
          display: "flex",
          alignItems: "stretch",
          padding: "0 20px",
          gap: "24px",
        }}
      >
        {/* Logo */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            flex: "none",
          }}
        >
          <Shield size={18} color="#3b82f6" />
          <span
            style={{
              fontSize: "15px",
              fontWeight: 600,
              letterSpacing: "0.14em",
              color: "#e8eaf0",
            }}
          >
            PRAMAAN
          </span>
        </div>

        {/* Nav tabs */}
        <div
          style={{
            display: "flex",
            alignItems: "stretch",
            gap: "2px",
            minWidth: 0,
            overflowX: "auto",
          }}
        >
          {navItems.map((n) => (
            <button
              key={n.label}
              type="button"
              onClick={n.go}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                height: "100%",
                padding: "0 14px",
                background: "transparent",
                border: "none",
                borderBottom: `2px solid ${n.bar}`,
                color: n.color,
                fontSize: "14px",
                whiteSpace: "nowrap",
                cursor: "pointer",
              }}
            >
              {n.icon} {n.label}
            </button>
          ))}
        </div>

        {/* User menu */}
        <div
          style={{
            marginLeft: "auto",
            alignSelf: "center",
            flex: "none",
            position: "relative",
          }}
        >
          <button
            type="button"
            onClick={() => setMenuOpen((v) => !v)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              height: "36px",
              padding: "0 8px 0 10px",
              background: "transparent",
              border: "1px solid #2a2d35",
              borderRadius: "6px",
              cursor: "pointer",
            }}
          >
            <span style={{ color: "#8b8fa8", display: "flex" }}>
              <UserCircle size={18} />
            </span>
            <span
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "flex-start",
                lineHeight: 1.2,
              }}
            >
              <span style={{ fontSize: "13px", color: "#e8eaf0" }}>
                {user?.fullName ?? "—"}
              </span>
              <span
                style={{
                  fontSize: "10px",
                  color: "#8b8fa8",
                  letterSpacing: "0.04em",
                }}
              >
                {ROLE_LABEL[user?.role ?? ""] ?? user?.role}
              </span>
            </span>
            <span style={{ color: "#555869", display: "flex" }}>
              <ChevronDown size={14} />
            </span>
          </button>

          {menuOpen && (
            <div
              style={{
                position: "absolute",
                right: 0,
                top: "44px",
                width: "200px",
                background: "#1a1d24",
                border: "1px solid #2a2d35",
                borderRadius: "8px",
                boxShadow: "0 18px 40px rgba(0,0,0,0.55)",
                padding: "6px",
                animation: "fadein 120ms ease-out",
              }}
            >
              <button
                type="button"
                onClick={handleLogout}
                style={{
                  width: "100%",
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  height: "34px",
                  padding: "0 10px",
                  background: "transparent",
                  border: "none",
                  borderRadius: "4px",
                  color: "#e8eaf0",
                  fontSize: "13px",
                  textAlign: "left",
                  cursor: "pointer",
                }}
              >
                <LogOut size={16} /> Log out
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ── Main content area ── */}
      <div
        style={{
          display: "flex",
          alignItems: "stretch",
          minHeight: "calc(100vh - 56px)",
        }}
      >
        <div
          style={{
            flex: 1,
            minWidth: 0,
            padding: "24px 28px 40px",
            background: "#0a0c10",
          }}
        >
          <div style={{ maxWidth: "1280px", margin: "0 auto" }}>
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
