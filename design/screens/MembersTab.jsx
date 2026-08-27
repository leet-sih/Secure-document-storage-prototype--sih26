// DESIGN REFERENCE — match this layout exactly when building src/pages/CaseDetailPage.tsx (Members tab)

import { Plus, BadgeCheck, Trash2 } from 'lucide-react';

/**
 * Props:
 *   membersView {array}  — [{
 *     name      (string),
 *     rb        { color, bg, text } — role badge,
 *     dept      (string),
 *     added     (string),
 *     canRemove (boolean),
 *     remove    (fn)
 *   }]
 *   onAddMember {fn}
 */
export default function MembersTab({ membersView = [], onAddMember }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>

      {/* Add member button */}
      <div style={{ display: "flex" }}>
        <button
          type="button"
          onClick={onAddMember}
          style={{
            marginLeft: "auto", height: "34px", padding: "0 14px",
            display: "flex", alignItems: "center", gap: "8px",
            background: "#1a1d24", border: "1px solid #2a2d35", borderRadius: "4px",
            color: "#e8eaf0", fontSize: "14px", whiteSpace: "nowrap", cursor: "pointer"
          }}
          /* hover: background #1e2028 */
        >
          <Plus size={16} /> Add Member
        </button>
      </div>

      {/* Members table */}
      <div style={{ background: "#111318", border: "1px solid #2a2d35", borderRadius: "8px", overflow: "hidden" }}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", minWidth: "760px", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#14161c" }}>
                <th style={{ textAlign: "left", padding: "10px 14px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>NAME</th>
                <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>ROLE</th>
                <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>DEPARTMENT</th>
                <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>ADDED</th>
                <th style={{ textAlign: "right", padding: "10px 14px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {membersView.map((m, i) => (
                <tr key={i} /* hover: background #1a1d24 */>
                  <td style={{ padding: "12px 14px", borderBottom: "1px solid #1e2028", fontSize: "13px", color: "#e8eaf0" }}>{m.name}</td>
                  <td style={{ padding: "12px", borderBottom: "1px solid #1e2028" }}>
                    <span style={{
                      display: "inline-flex", alignItems: "center", gap: "5px",
                      fontSize: "11px", fontWeight: 500, letterSpacing: "0.05em",
                      padding: "3px 7px", borderRadius: "4px",
                      color: m.rb.color, background: m.rb.bg
                    }}>
                      <BadgeCheck size={14} /> {m.rb.text}
                    </span>
                  </td>
                  <td style={{ padding: "12px", borderBottom: "1px solid #1e2028", fontSize: "13px", color: "#8b8fa8" }}>{m.dept}</td>
                  <td style={{ padding: "12px", borderBottom: "1px solid #1e2028", fontSize: "13px", color: "#8b8fa8" }}>{m.added}</td>
                  <td style={{ padding: "8px 14px", borderBottom: "1px solid #1e2028", textAlign: "right" }}>
                    {m.canRemove && (
                      <button
                        type="button"
                        onClick={m.remove}
                        style={{
                          height: "28px", padding: "0 10px",
                          display: "inline-flex", alignItems: "center", gap: "6px",
                          background: "transparent", border: "1px solid #2a2d35", borderRadius: "4px",
                          color: "#8b8fa8", fontSize: "12px", cursor: "pointer"
                        }}
                        /* hover: color #ef4444; border-color #ef4444 */
                      >
                        <Trash2 size={14} /> Remove
                      </button>
                    )}
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
