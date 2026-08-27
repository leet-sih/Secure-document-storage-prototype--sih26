// DESIGN REFERENCE — match this layout exactly when building src/pages/CaseDetailPage.tsx

/**
 * This file covers the outer wrapper of the case detail view:
 * breadcrumb, case header, and tab navigation.
 *
 * Tab content lives in separate files:
 *   DocumentsTab.jsx  — tabDocuments
 *   ActivityTab.jsx   — tabActivity
 *   MembersTab.jsx    — tabMembers
 *   OverviewTab.jsx   — tabOverview
 *   DocumentDetailPanel.jsx — hasPanel (slide-in)
 *
 * Props:
 *   caseNumber    {string}   — e.g. "CR-2026-0042"
 *   caseTitle     {string}
 *   caseSt        {object}   — { color, bg, text }
 *   casePr        {object}   — { color, bg, text }
 *   caseDocs      {number}
 *   caseMembers   {number}
 *   caseCreated   {string}   — formatted date
 *   tabs          {array}    — [{ label, icon (JSX), border, color, go (fn) }]
 *                              Active tab: border "#3b82f6", color "#e8eaf0"
 *                              Inactive:   border "transparent", color "#8b8fa8"
 *   onBackToCases {fn}
 *   children      {ReactNode} — active tab content
 *   panel         {ReactNode} — DocumentDetailPanel if open, null otherwise
 */
export default function CaseDetailPage({
  caseNumber = "CR-2026-0042",
  caseTitle = "",
  caseSt = { color: "#6366f1", bg: "#1e1e4a", text: "OPEN" },
  casePr = { color: "#ef4444", bg: "#3d1010", text: "CRITICAL" },
  caseDocs = 0,
  caseMembers = 0,
  caseCreated = "",
  tabs = [],
  onBackToCases,
  children,
  panel = null,
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>

      {/* Breadcrumb */}
      <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "#8b8fa8" }}>
        <button
          type="button"
          onClick={onBackToCases}
          style={{ background: "none", border: "none", padding: 0, color: "#8b8fa8", fontSize: "12px", cursor: "pointer" }}
          /* hover: color #e8eaf0 */
        >
          Cases
        </button>
        <span style={{ color: "#555869" }}>/</span>
        <span style={{ fontFamily: "'JetBrains Mono', monospace", color: "#e8eaf0" }}>{caseNumber}</span>
      </div>

      {/* Case header */}
      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        <h1 style={{
          margin: 0, fontSize: "24px", fontWeight: 600,
          color: "#e8eaf0", lineHeight: 1.35, maxWidth: "780px"
        }}>
          {caseTitle}
        </h1>
        <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
          <span style={{
            fontSize: "11px", fontWeight: 500, letterSpacing: "0.05em",
            textTransform: "uppercase", padding: "3px 7px", borderRadius: "4px",
            color: caseSt.color, background: caseSt.bg
          }}>{caseSt.text}</span>
          <span style={{
            fontSize: "11px", fontWeight: 500, letterSpacing: "0.05em",
            textTransform: "uppercase", padding: "3px 7px", borderRadius: "4px",
            color: casePr.color, background: casePr.bg
          }}>{casePr.text}</span>
          <span style={{ fontSize: "12px", color: "#8b8fa8" }}>
            {caseDocs} documents · {caseMembers} members · created {caseCreated}
          </span>
        </div>
      </div>

      {/* Tab bar */}
      <div style={{ display: "flex", gap: "4px", borderBottom: "1px solid #2a2d35" }}>
        {tabs.map((t) => (
          <button
            key={t.label}
            type="button"
            onClick={t.go}
            style={{
              display: "flex", alignItems: "center", gap: "8px",
              height: "38px", padding: "0 12px",
              background: "transparent", border: "none",
              borderBottom: `2px solid ${t.border}`,
              color: t.color, fontSize: "14px", cursor: "pointer"
            }}
            /* hover: color #e8eaf0 */
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* Active tab content */}
      {children}

      {/* Slide-in document detail panel (rendered via DocumentDetailPanel.jsx) */}
      {panel}
    </div>
  );
}
