// DESIGN REFERENCE — match this layout exactly when building src/pages/UserAdminPage.tsx

import { Search, Plus, BadgeCheck, UserX } from 'lucide-react';

/**
 * Props:
 *   usersView   {array}   — [{
 *     name        (string),
 *     email       (string),
 *     rb          { color, bg, text } — role badge,
 *     icon        (JSX)    — role icon,
 *     dept        (string),
 *     statusColor (string) — dot color,
 *     statusLabel (string) — "Active", "Locked", "Inactive",
 *     last        (string) — "2 hours ago" etc.,
 *     exact       (string) — ISO timestamp for title attribute,
 *     editRole    (fn),
 *     deactivate  (fn)
 *   }]
 *   onNewUser   {fn}
 */
export default function UserAdminPage({ usersView = [], onNewUser }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
      <h1 style={{ margin: 0, fontSize: "30px", fontWeight: 700, color: "#e8eaf0" }}>User Management</h1>

      {/* Toolbar */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center" }}>
        <div style={{
          display: "flex", alignItems: "center", gap: "8px",
          height: "34px", padding: "0 10px",
          background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px",
          minWidth: "240px", color: "#555869"
        }}>
          <Search size={16} />
          <input
            placeholder="Search users…"
            style={{ flex: 1, height: "32px", background: "transparent", border: "none", color: "#e8eaf0", fontSize: "14px" }}
          />
        </div>

        <select aria-label="Role filter" style={{ height: "34px", padding: "0 8px", background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px", color: "#e8eaf0", fontSize: "13px" }}>
          <option>Role — all</option>
          <option>SUPER_ADMIN</option>
          <option>CASE_OFFICER</option>
          <option>INVESTIGATOR</option>
          <option>PROSECUTOR</option>
          <option>AUDITOR</option>
        </select>

        <select aria-label="Status filter" style={{ height: "34px", padding: "0 8px", background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px", color: "#e8eaf0", fontSize: "13px" }}>
          <option>Status — all</option>
          <option>ACTIVE</option>
          <option>LOCKED</option>
          <option>INACTIVE</option>
        </select>

        <button
          type="button"
          onClick={onNewUser}
          style={{
            marginLeft: "auto", height: "34px", padding: "0 14px",
            display: "flex", alignItems: "center", gap: "8px",
            background: "#3b82f6", color: "#ffffff",
            border: "none", borderRadius: "4px", fontSize: "14px", fontWeight: 500, cursor: "pointer"
          }}
          /* hover: background #2563eb */
        >
          <Plus size={16} /> Create User
        </button>
      </div>

      {/* Users table */}
      <div style={{ background: "#111318", border: "1px solid #2a2d35", borderRadius: "8px", overflow: "hidden" }}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", minWidth: "1080px", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#14161c" }}>
                <th style={{ textAlign: "left", padding: "10px 14px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>NAME</th>
                <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>EMAIL</th>
                <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>ROLE</th>
                <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>DEPARTMENT</th>
                <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>STATUS</th>
                <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>LAST LOGIN</th>
                <th style={{ textAlign: "right", padding: "10px 14px 10px 12px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {usersView.map((u, i) => (
                <tr key={i} /* hover: background #1a1d24 */>
                  <td style={{ padding: "12px 14px", borderBottom: "1px solid #1e2028", fontSize: "13px", color: "#e8eaf0", whiteSpace: "nowrap" }}>{u.name}</td>
                  <td style={{ padding: "12px", borderBottom: "1px solid #1e2028", fontFamily: "'JetBrains Mono', monospace", fontSize: "12px", color: "#8b8fa8" }}>{u.email}</td>
                  <td style={{ padding: "12px", borderBottom: "1px solid #1e2028" }}>
                    <span style={{
                      display: "inline-flex", alignItems: "center", gap: "5px",
                      fontSize: "11px", fontWeight: 500, letterSpacing: "0.05em",
                      padding: "3px 7px", borderRadius: "4px", whiteSpace: "nowrap",
                      color: u.rb.color, background: u.rb.bg
                    }}>
                      {u.icon} {u.rb.text}
                    </span>
                  </td>
                  <td style={{ padding: "12px", borderBottom: "1px solid #1e2028", fontSize: "13px", color: "#8b8fa8", whiteSpace: "nowrap" }}>{u.dept}</td>
                  <td style={{ padding: "12px", borderBottom: "1px solid #1e2028" }}>
                    <span style={{ display: "flex", alignItems: "center", gap: "7px", fontSize: "12px", color: "#8b8fa8", whiteSpace: "nowrap" }}>
                      <span style={{ width: "7px", height: "7px", borderRadius: "50%", background: u.statusColor }} />
                      {u.statusLabel}
                    </span>
                  </td>
                  <td title={u.exact} style={{ padding: "12px", borderBottom: "1px solid #1e2028", fontSize: "13px", color: "#8b8fa8", whiteSpace: "nowrap" }}>{u.last}</td>
                  <td style={{ padding: "8px 14px 8px 12px", borderBottom: "1px solid #1e2028", textAlign: "right", whiteSpace: "nowrap" }}>
                    <button
                      type="button"
                      onClick={u.editRole}
                      style={{
                        height: "28px", padding: "0 10px", marginRight: "6px",
                        display: "inline-flex", alignItems: "center", gap: "6px",
                        background: "#1a1d24", border: "1px solid #2a2d35", borderRadius: "4px",
                        color: "#e8eaf0", fontSize: "12px", cursor: "pointer"
                      }}
                      /* hover: background #1e2028 */
                    >
                      <BadgeCheck size={14} /> Edit role
                    </button>
                    <button
                      type="button"
                      onClick={u.deactivate}
                      style={{
                        height: "28px", padding: "0 10px",
                        display: "inline-flex", alignItems: "center", gap: "6px",
                        background: "transparent", border: "1px solid #2a2d35", borderRadius: "4px",
                        color: "#8b8fa8", fontSize: "12px", cursor: "pointer"
                      }}
                      /* hover: color #ef4444; border-color #ef4444 */
                    >
                      <UserX size={14} /> Deactivate
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
