// DESIGN REFERENCE — match this layout exactly when building src/pages/ProfilePage.tsx

import { UserCircle, BadgeCheck, KeyRound } from 'lucide-react';

/**
 * Props:
 *   profileName       {string}
 *   profileEmail      {string}
 *   profileRole       {object}  — { color, bg, text }
 *   onChangePassword  {fn}
 *   onReconfigureMfa  {fn}
 */
export default function ProfilePage({
  profileName = "Insp. Ravi Kumar",
  profileEmail = "ravi.kumar@mah.police.gov.in",
  profileRole = { color: "#6366f1", bg: "#1e1e4a", text: "Case Officer" },
  onChangePassword,
  onReconfigureMfa,
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
      <h1 style={{ margin: 0, fontSize: "30px", fontWeight: 700, color: "#e8eaf0" }}>My Profile</h1>

      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
        gap: "16px", alignItems: "start"
      }}>

        {/* ── Identity card ── */}
        <div style={{
          background: "#111318", border: "1px solid #2a2d35", borderRadius: "8px",
          padding: "20px", display: "flex", flexDirection: "column", gap: "16px"
        }}>
          {/* Avatar + name + role */}
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span style={{ color: "#8b8fa8", display: "flex" }}><UserCircle size={36} /></span>
            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              <span style={{ fontSize: "17px", fontWeight: 600, color: "#e8eaf0" }}>{profileName}</span>
              <span style={{
                display: "inline-flex", alignItems: "center", gap: "5px", alignSelf: "flex-start",
                fontSize: "11px", fontWeight: 500, letterSpacing: "0.05em",
                padding: "3px 7px", borderRadius: "4px",
                color: profileRole.color, background: profileRole.bg
              }}>
                <BadgeCheck size={14} /> {profileRole.text}
              </span>
            </div>
          </div>

          {/* Fields grid */}
          <div style={{
            display: "grid", gridTemplateColumns: "110px 1fr",
            gap: "12px", fontSize: "13px",
            borderTop: "1px solid #2a2d35", paddingTop: "16px"
          }}>
            <span style={{ color: "#8b8fa8" }}>Full name</span>
            <input
              defaultValue={profileName}
              style={{
                height: "32px", padding: "0 10px",
                background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px",
                color: "#e8eaf0", fontSize: "13px"
              }}
            />

            <span style={{ color: "#8b8fa8" }}>Email</span>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "12px", color: "#8b8fa8", alignSelf: "center" }}>
              {profileEmail}
            </span>

            <span style={{ color: "#8b8fa8" }}>Department</span>
            <span style={{ color: "#e8eaf0", alignSelf: "center" }}>Cybercrime Unit</span>

            <span style={{ color: "#8b8fa8" }}>Member since</span>
            <span style={{ color: "#8b8fa8", alignSelf: "center" }} title="2025-11-04T10:12:00+05:30">
              Nov 4, 2025
            </span>
          </div>
        </div>

        {/* ── Security card ── */}
        <div style={{
          background: "#111318", border: "1px solid #2a2d35", borderRadius: "8px",
          padding: "20px", display: "flex", flexDirection: "column", gap: "18px"
        }}>

          {/* Password section */}
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <span style={{ fontSize: "11px", letterSpacing: "0.06em", fontFamily: "'JetBrains Mono', monospace", color: "#555869" }}>
              PASSWORD
            </span>
            <button
              type="button"
              onClick={onChangePassword}
              style={{
                alignSelf: "flex-start", height: "34px", padding: "0 14px",
                background: "#1a1d24", border: "1px solid #2a2d35", borderRadius: "4px",
                color: "#e8eaf0", fontSize: "13px", cursor: "pointer"
              }}
              /* hover: background #1e2028 */
            >
              Change Password
            </button>
          </div>

          {/* MFA section */}
          <div style={{ display: "flex", flexDirection: "column", gap: "10px", borderTop: "1px solid #2a2d35", paddingTop: "16px" }}>
            <span style={{ fontSize: "11px", letterSpacing: "0.06em", fontFamily: "'JetBrains Mono', monospace", color: "#555869" }}>
              TWO-FACTOR AUTHENTICATION
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "#22c55e" }}>
              <KeyRound size={16} /> Enabled
            </span>
            <button
              type="button"
              onClick={onReconfigureMfa}
              style={{
                alignSelf: "flex-start", height: "34px", padding: "0 14px",
                background: "#1a1d24", border: "1px solid #2a2d35", borderRadius: "4px",
                color: "#e8eaf0", fontSize: "13px", cursor: "pointer"
              }}
              /* hover: background #1e2028 */
            >
              Re-configure MFA
            </button>
          </div>

          {/* Active session */}
          <div style={{ display: "flex", flexDirection: "column", gap: "8px", borderTop: "1px solid #2a2d35", paddingTop: "16px" }}>
            <span style={{ fontSize: "11px", letterSpacing: "0.06em", fontFamily: "'JetBrains Mono', monospace", color: "#555869" }}>
              ACTIVE SESSION
            </span>
            <span style={{ fontSize: "13px", color: "#8b8fa8" }}>
              Token expires in{" "}
              <span style={{ fontFamily: "'JetBrains Mono', monospace", color: "#e8eaf0" }}>6h 43m</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
