// DESIGN REFERENCE — match this layout exactly when building src/pages/CaseDetailPage.tsx (Overview tab)

/**
 * Props:
 *   caseNumber    {string}
 *   caseTitle     {string}
 *   statusValue   {string}   — controlled value for status select
 *   priorityValue {string}   — controlled value for priority select
 *   caseCreated   {string}   — formatted date
 *   savedAt       {string}   — "" or "Saved at 14:32" (shown in green after save)
 *   onSetStatus   {fn}
 *   onSetPriority {fn}
 *   onSaveCase    {fn}
 */
export default function OverviewTab({
  caseNumber = "",
  caseTitle = "",
  statusValue = "UNDER_INVESTIGATION",
  priorityValue = "CRITICAL",
  caseCreated = "",
  savedAt = "",
  onSetStatus,
  onSetPriority,
  onSaveCase,
}) {
  return (
    <div style={{
      background: "#111318", border: "1px solid #2a2d35", borderRadius: "8px",
      padding: "20px", display: "flex", flexDirection: "column", gap: "18px",
      maxWidth: "720px"
    }}>
      {/* Metadata grid */}
      <div style={{
        display: "grid", gridTemplateColumns: "160px 1fr",
        gap: "14px 20px", alignItems: "center"
      }}>
        <span style={{ fontSize: "13px", color: "#8b8fa8" }}>Case number</span>
        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "13px", color: "#e8eaf0" }}>{caseNumber}</span>

        <span style={{ fontSize: "13px", color: "#8b8fa8" }}>Title</span>
        <span style={{ fontSize: "13px", color: "#e8eaf0" }}>{caseTitle}</span>

        <span style={{ fontSize: "13px", color: "#8b8fa8" }}>Status</span>
        <select
          value={statusValue}
          onChange={onSetStatus}
          aria-label="Case status"
          style={{
            height: "34px", padding: "0 8px",
            background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px",
            color: "#e8eaf0", fontSize: "13px", maxWidth: "260px"
          }}
        >
          <option value="OPEN">Open</option>
          <option value="UNDER_INVESTIGATION">Under investigation</option>
          <option value="CLOSED">Closed</option>
          <option value="ARCHIVED">Archived</option>
        </select>

        <span style={{ fontSize: "13px", color: "#8b8fa8" }}>Priority</span>
        <select
          value={priorityValue}
          onChange={onSetPriority}
          aria-label="Case priority"
          style={{
            height: "34px", padding: "0 8px",
            background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px",
            color: "#e8eaf0", fontSize: "13px", maxWidth: "260px"
          }}
        >
          <option value="LOW">Low</option>
          <option value="NORMAL">Normal</option>
          <option value="HIGH">High</option>
          <option value="CRITICAL">Critical</option>
        </select>

        <span style={{ fontSize: "13px", color: "#8b8fa8", alignSelf: "flex-start", paddingTop: "8px" }}>Description</span>
        <textarea
          rows={4}
          defaultValue="Organised crypto-fraud syndicate operating through three exchange accounts; seizure of six hardware wallets on 24 Aug. Forensic tracing in progress with Forensic Lab."
          style={{
            padding: "10px", background: "#1e2028", border: "1px solid #2a2d35",
            borderRadius: "6px", color: "#e8eaf0", fontSize: "13px",
            lineHeight: 1.55, resize: "vertical"
          }}
        />

        <span style={{ fontSize: "13px", color: "#8b8fa8" }}>Created by</span>
        <span style={{ fontSize: "13px", color: "#e8eaf0" }}>Insp. Ravi Kumar · Cybercrime Unit</span>

        <span style={{ fontSize: "13px", color: "#8b8fa8" }}>Created at</span>
        <span style={{ fontSize: "13px", color: "#8b8fa8" }} title="2026-08-24T09:12:00+05:30">{caseCreated}</span>
      </div>

      {/* Save row */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px", borderTop: "1px solid #2a2d35", paddingTop: "16px" }}>
        <button
          type="button"
          onClick={onSaveCase}
          style={{
            height: "34px", padding: "0 16px",
            background: "#3b82f6", color: "#ffffff",
            border: "none", borderRadius: "4px",
            fontSize: "14px", fontWeight: 500, cursor: "pointer"
          }}
          /* hover: background #2563eb */
        >
          Save Changes
        </button>
        {savedAt && (
          <span style={{ fontSize: "12px", color: "#22c55e" }}>{savedAt}</span>
        )}
      </div>
    </div>
  );
}
