// DESIGN REFERENCE — match this layout exactly when building src/pages/CaseDetailPage.tsx (Activity tab)

/**
 * Props:
 *   activity   {array}  — [{
 *     icon      (JSX),
 *     color     (string) — e.g. "#22c55e",
 *     actor     (string),
 *     roleLabel (string),
 *     event     (string) — e.g. "DOCUMENT_UPLOADED",
 *     target    (string),
 *     when      (string) — ISO or formatted timestamp
 *   }]
 *   onLoadMore {fn}
 */
export default function ActivityTab({ activity = [], onLoadMore }) {
  return (
    <div style={{
      background: "#111318", border: "1px solid #2a2d35",
      borderRadius: "8px", padding: "8px 4px"
    }}>
      {activity.map((a, i) => (
        <div
          key={i}
          style={{
            display: "flex", gap: "12px",
            padding: "14px 16px", borderBottom: "1px solid #1e2028"
          }}
        >
          {/* Event icon chip */}
          <div style={{
            width: "26px", height: "26px", flex: "none",
            display: "flex", alignItems: "center", justifyContent: "center",
            borderRadius: "6px", background: "rgba(255,255,255,0.04)",
            color: a.color
          }}>
            {a.icon}
          </div>

          {/* Text block */}
          <div style={{ display: "flex", flexDirection: "column", gap: "3px", minWidth: 0 }}>
            <div style={{ fontSize: "13px", color: "#e8eaf0" }}>
              {a.actor} <span style={{ color: "#8b8fa8" }}>({a.roleLabel})</span>
            </div>
            <div style={{ fontSize: "12px", color: "#8b8fa8" }}>
              <span style={{ fontFamily: "'JetBrains Mono', monospace", color: a.color }}>{a.event}</span>
              {" · "}{a.target}
            </div>
            <div style={{ fontSize: "11px", fontFamily: "'JetBrains Mono', monospace", color: "#555869" }}>
              {a.when}
            </div>
          </div>
        </div>
      ))}

      {/* Load more */}
      <div style={{ display: "flex", justifyContent: "center", padding: "14px" }}>
        <button
          type="button"
          onClick={onLoadMore}
          style={{
            height: "30px", padding: "0 14px",
            background: "#1a1d24", border: "1px solid #2a2d35", borderRadius: "4px",
            color: "#8b8fa8", fontSize: "13px", cursor: "pointer"
          }}
          /* hover: color #e8eaf0 */
        >
          Load more
        </button>
      </div>
    </div>
  );
}
