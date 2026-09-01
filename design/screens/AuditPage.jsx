// DESIGN REFERENCE — match this layout exactly when building src/pages/AuditPage.tsx

import { ShieldCheck, AlertTriangle, ChevronLeft, ChevronRight } from 'lucide-react';

/**
 * Props:
 *   chain          {object}  — { bg, border, color, anim, icon (JSX), text }
 *                              Verified:  bg #14391f, border #22c55e, color #22c55e, anim "none", icon <ShieldCheck>
 *                              Tampered:  bg #3d1010, border #ef4444, color #ef4444, anim "pulseborder 1.5s infinite", icon <AlertTriangle>
 *                              Idle:      bg #1a1d24, border #2a2d35, color #8b8fa8, anim "none"
 *   chainBroken    {boolean} — show the broken-chain error banner
 *   auditRows      {array}   — [{
 *     id       (string),
 *     when     (string),
 *     dot      (string)   — color for the event type dot,
 *     event    (string)   — e.g. "DOCUMENT_DOWNLOADED",
 *     actor    (string),
 *     rb       { color, bg, text } — role badge,
 *     target   (string),
 *     ip       (string),
 *     chev     (JSX)      — expand chevron icon,
 *     expanded (boolean),
 *     meta     (string)   — JSON/text shown in expanded pre block,
 *     toggle   (fn)
 *   }]
 *   onVerifyChain  {fn}
 *   onClearFilters {fn}
 */
export default function AuditPage({
  chain = { bg: "#1a1d24", border: "#2a2d35", color: "#8b8fa8", anim: "none", icon: null, text: "Not verified" },
  chainBroken = false,
  auditRows = [],
  onVerifyChain,
  onClearFilters,
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
      <h1 style={{ margin: 0, fontSize: "30px", fontWeight: 700, color: "#e8eaf0" }}>Audit Log</h1>

      {/* Chain verify badge + stats */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", alignItems: "center" }}>
        <div style={{
          display: "flex", alignItems: "center", gap: "10px",
          padding: "10px 14px", borderRadius: "8px",
          background: chain.bg, border: `1px solid ${chain.border}`,
          color: chain.color, animation: chain.anim
        }}>
          {chain.icon}
          <span style={{ fontSize: "13px", fontWeight: 500 }}>{chain.text}</span>
        </div>

        <span style={{ fontSize: "13px", color: "#8b8fa8" }}>4,821 events recorded</span>

        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: "8px" }}>
          <button
            type="button"
            onClick={onVerifyChain}
            style={{
              height: "34px", padding: "0 14px",
              display: "flex", alignItems: "center", gap: "8px",
              background: "#1a1d24", border: "1px solid #2a2d35", borderRadius: "4px",
              color: "#e8eaf0", fontSize: "14px", whiteSpace: "nowrap", cursor: "pointer"
            }}
            /* hover: background #1e2028 */
          >
            <ShieldCheck size={16} /> Verify Chain
          </button>
          {/* PROTOTYPE-ONLY "simulate tampered" button — do not implement in real app */}
        </div>
      </div>

      {/* Broken chain error banner */}
      {chainBroken && (
        <div style={{
          display: "flex", gap: "10px", alignItems: "flex-start",
          background: "#3d1010", border: "1px solid #ef4444",
          borderRadius: "8px", padding: "14px 16px"
        }}>
          <span style={{ color: "#ef4444", marginTop: "1px", display: "flex" }}><AlertTriangle size={18} /></span>
          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
            <span style={{ fontSize: "14px", fontWeight: 500, color: "#e8eaf0" }}>Hash chain broken at event #3042</span>
            <span style={{ fontSize: "13px", color: "#8b8fa8", lineHeight: 1.55, maxWidth: "720px" }}>
              Events after #3042 can no longer be proven unmodified. Preserve the database, notify the system administrator, and do not export the log as evidence until the break is investigated.
            </span>
          </div>
        </div>
      )}

      {/* Filters row */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center" }}>
        <select aria-label="Event type filter" style={{ height: "34px", padding: "0 8px", background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px", color: "#e8eaf0", fontSize: "13px" }}>
          <option>Event type — all</option>
          <option>DOCUMENT_DOWNLOADED</option>
          <option>DOCUMENT_SHARED</option>
          <option>UNAUTHORIZED_ACCESS_ATTEMPT</option>
          <option>INTEGRITY_VIOLATION</option>
        </select>
        <select aria-label="Actor filter" style={{ height: "34px", padding: "0 8px", background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px", color: "#e8eaf0", fontSize: "13px" }}>
          <option>Role / actor — all</option>
          <option>CASE_OFFICER</option>
          <option>INVESTIGATOR</option>
          <option>PROSECUTOR</option>
        </select>
        <select aria-label="Case filter" style={{ height: "34px", padding: "0 8px", background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px", color: "#e8eaf0", fontSize: "13px" }}>
          <option>Case — all</option>
          <option>CR-2026-0042</option>
          <option>CR-2026-0038</option>
        </select>
        <input type="date" aria-label="From date" style={{ height: "34px", padding: "0 8px", background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px", color: "#8b8fa8", fontSize: "13px" }} />
        <input type="date" aria-label="To date" style={{ height: "34px", padding: "0 8px", background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px", color: "#8b8fa8", fontSize: "13px" }} />
        <button type="button" onClick={onClearFilters} style={{ height: "34px", padding: "0 12px", background: "transparent", border: "none", color: "#8b8fa8", fontSize: "13px", cursor: "pointer" }}
          /* hover: color #e8eaf0 */>
          Clear filters
        </button>
      </div>

      {/* Audit table */}
      <div style={{ background: "#111318", border: "1px solid #2a2d35", borderRadius: "8px", overflow: "hidden" }}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", minWidth: "1080px", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#14161c" }}>
                <th style={{ textAlign: "left", padding: "10px 14px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>#</th>
                <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>TIMESTAMP</th>
                <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>EVENT</th>
                <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>ACTOR</th>
                <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>TARGET</th>
                <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>IP</th>
                <th style={{ width: "44px", padding: "10px 14px 10px 12px", borderBottom: "1px solid #2a2d35" }} />
              </tr>
            </thead>
            {auditRows.map((a, i) => (
              <tbody key={i}>
                {/* Row */}
                <tr onClick={a.toggle} style={{ cursor: "pointer" }} /* hover: background #1a1d24 */>
                  <td style={{ padding: "11px 14px", borderBottom: "1px solid #1e2028", fontFamily: "'JetBrains Mono', monospace", fontSize: "12px", color: "#555869" }}>{a.id}</td>
                  <td style={{ padding: "11px 12px", borderBottom: "1px solid #1e2028", fontSize: "12px", color: "#8b8fa8", whiteSpace: "nowrap" }}>{a.when}</td>
                  <td style={{ padding: "11px 12px", borderBottom: "1px solid #1e2028" }}>
                    <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span style={{ width: "7px", height: "7px", flex: "none", borderRadius: "50%", background: a.dot }} />
                      <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "11px", letterSpacing: "0.03em", color: "#e8eaf0" }}>{a.event}</span>
                    </span>
                  </td>
                  <td style={{ padding: "11px 12px", borderBottom: "1px solid #1e2028" }}>
                    <span style={{ display: "flex", alignItems: "center", gap: "8px", whiteSpace: "nowrap" }}>
                      <span style={{ fontSize: "13px", color: "#e8eaf0" }}>{a.actor}</span>
                      <span style={{ fontSize: "10px", letterSpacing: "0.05em", padding: "2px 6px", borderRadius: "4px", color: a.rb.color, background: a.rb.bg }}>{a.rb.text}</span>
                    </span>
                  </td>
                  <td style={{ padding: "11px 12px", borderBottom: "1px solid #1e2028", fontSize: "12px", color: "#8b8fa8", maxWidth: "260px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{a.target}</td>
                  <td style={{ padding: "11px 12px", borderBottom: "1px solid #1e2028", fontFamily: "'JetBrains Mono', monospace", fontSize: "12px", color: "#8b8fa8" }}>{a.ip}</td>
                  <td style={{ padding: "11px 14px 11px 12px", borderBottom: "1px solid #1e2028", color: "#555869" }}>{a.chev}</td>
                </tr>

                {/* Expanded metadata row */}
                {a.expanded && (
                  <tr>
                    <td colSpan={7} style={{ padding: "0 14px 14px", borderBottom: "1px solid #1e2028", background: "#0d0f14" }}>
                      <pre style={{
                        margin: 0, padding: "12px 14px",
                        background: "#0a0c10", border: "1px solid #2a2d35", borderRadius: "6px",
                        fontFamily: "'JetBrains Mono', monospace", fontSize: "12px",
                        lineHeight: 1.6, color: "#8b8fa8", overflowX: "auto"
                      }}>
                        {a.meta}
                      </pre>
                    </td>
                  </tr>
                )}
              </tbody>
            ))}
          </table>
        </div>
      </div>

      {/* Pagination */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <span style={{ fontSize: "12px", color: "#8b8fa8" }}>Showing 4,808–4,821 of 4,821 events</span>
        <div style={{ marginLeft: "auto", display: "flex", gap: "6px" }}>
          <button type="button" title="Previous page" aria-label="Previous page" style={{ width: "32px", height: "32px", display: "flex", alignItems: "center", justifyContent: "center", background: "#1a1d24", border: "1px solid #2a2d35", borderRadius: "4px", color: "#8b8fa8", cursor: "pointer" }} /* hover: color #e8eaf0 */>
            <ChevronLeft size={16} />
          </button>
          <button type="button" title="Next page" aria-label="Next page" style={{ width: "32px", height: "32px", display: "flex", alignItems: "center", justifyContent: "center", background: "#1a1d24", border: "1px solid #2a2d35", borderRadius: "4px", color: "#555869", cursor: "not-allowed" }}>
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
