// DESIGN REFERENCE — match this layout exactly when building src/components/AppShell.tsx

import { Shield, UserCircle, ChevronDown, LogOut, BadgeCheck } from 'lucide-react';

/**
 * Props:
 *   me              {object}   — { name, roleLabel }
 *   nav             {array}    — [{ label, icon (JSX), bg, bar, color, go (fn) }]
 *                                bg/bar/color differ for active vs inactive tab
 *                                Active:   bg "transparent", bar "#3b82f6", color "#e8eaf0"
 *                                Inactive: bg "transparent", bar "transparent", color "#8b8fa8"
 *   userMenuOpen    {boolean}
 *   roleOptions     {array}    — [{ label, icon (JSX), bg, color, pick (fn) }] prototype-only; omit in real app
 *   onToggleMenu    {fn}
 *   onGoProfile     {fn}
 *   onLogout        {fn}
 *   children        {ReactNode} — page content rendered inside the main area
 */
export default function AppShell({
  me = { name: "Insp. Ravi Kumar", roleLabel: "Case Officer" },
  nav = [],
  userMenuOpen = false,
  onToggleMenu,
  onGoProfile,
  onLogout,
  children,
}) {
  return (
    <div style={{ minHeight: "100vh", background: "#0a0c10", color: "#e8eaf0" }}>

      {/* ── Top bar ── */}
      <div style={{
        position: "sticky", top: 0, zIndex: 40,
        height: "56px",
        background: "#111318", borderBottom: "1px solid #2a2d35",
        display: "flex", alignItems: "stretch",
        padding: "0 20px", gap: "24px"
      }}>

        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#3b82f6", flex: "none" }}>
          <Shield size={18} />
          <span style={{ fontSize: "15px", fontWeight: 600, letterSpacing: "0.14em", color: "#e8eaf0" }}>
            PRAMAAN
          </span>
        </div>

        {/* Nav tabs */}
        <div style={{
          display: "flex", alignItems: "stretch",
          gap: "2px", minWidth: 0, overflowX: "auto"
        }}>
          {nav.map((n) => (
            <button
              key={n.label}
              type="button"
              title={n.label}
              onClick={n.go}
              style={{
                display: "flex", alignItems: "center", gap: "8px",
                height: "100%", padding: "0 14px",
                background: n.bg,
                border: "none", borderBottom: `2px solid ${n.bar}`,
                color: n.color, fontSize: "14px",
                whiteSpace: "nowrap", cursor: "pointer"
              }}
              /* hover: background #1a1d24; color #e8eaf0 */
            >
              {n.icon} {n.label}
            </button>
          ))}
        </div>

        {/* User menu trigger */}
        <div style={{ marginLeft: "auto", alignSelf: "center", flex: "none", position: "relative" }}>
          <button
            type="button"
            onClick={onToggleMenu}
            style={{
              display: "flex", alignItems: "center", gap: "10px",
              height: "36px", padding: "0 8px 0 10px",
              background: "transparent", border: "1px solid #2a2d35",
              borderRadius: "6px", cursor: "pointer"
            }}
            /* hover: background #1a1d24 */
          >
            <span style={{ color: "#8b8fa8", display: "flex" }}><UserCircle size={18} /></span>
            <span style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", lineHeight: 1.2 }}>
              <span style={{ fontSize: "13px", color: "#e8eaf0" }}>{me.name}</span>
              <span style={{ fontSize: "10px", color: "#8b8fa8", letterSpacing: "0.04em" }}>{me.roleLabel}</span>
            </span>
            <span style={{ color: "#555869", display: "flex" }}><ChevronDown size={14} /></span>
          </button>

          {/* Dropdown */}
          {userMenuOpen && (
            <div style={{
              position: "absolute", right: 0, top: "44px",
              width: "268px",
              background: "#1a1d24", border: "1px solid #2a2d35",
              borderRadius: "8px", boxShadow: "0 18px 40px rgba(0,0,0,0.55)",
              padding: "6px", animation: "fadein 120ms ease-out"
            }}>
              <button
                type="button"
                onClick={onGoProfile}
                style={{
                  width: "100%", display: "flex", alignItems: "center", gap: "10px",
                  height: "34px", padding: "0 10px",
                  background: "transparent", border: "none", borderRadius: "4px",
                  color: "#e8eaf0", fontSize: "13px", textAlign: "left", cursor: "pointer"
                }}
                /* hover: background #1e2028 */
              >
                <UserCircle size={16} /> Profile
              </button>
              <button
                type="button"
                onClick={onLogout}
                style={{
                  width: "100%", display: "flex", alignItems: "center", gap: "10px",
                  height: "34px", padding: "0 10px",
                  background: "transparent", border: "none", borderRadius: "4px",
                  color: "#e8eaf0", fontSize: "13px", textAlign: "left", cursor: "pointer"
                }}
                /* hover: background #1e2028 */
              >
                <LogOut size={16} /> Log out
              </button>
              {/* NOTE: "PROTOTYPE — PREVIEW AS ROLE" section below is PROTOTYPE-ONLY.
                  Do NOT implement in the real app. */}
            </div>
          )}
        </div>
      </div>

      {/* ── Main content area ── */}
      <div style={{ display: "flex", alignItems: "stretch", minHeight: "calc(100vh - 56px)" }}>
        <div style={{ flex: 1, minWidth: 0, padding: "24px 28px 40px", background: "#0a0c10" }}>
          <div style={{ maxWidth: "1280px", margin: "0 auto" }}>
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}
