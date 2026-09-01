// DESIGN REFERENCE — match this layout exactly when building src/pages/SearchPage.tsx

import { Search, X, ArrowRight } from 'lucide-react';

/**
 * Props:
 *   queryValue    {string}
 *   hasResults    {boolean}
 *   searchEmpty   {boolean}  — query ran, zero results
 *   searchIdle    {boolean}  — no query yet
 *   resultCount   {number|string}
 *   searchRows    {array}    — [{
 *     icon      (JSX),
 *     nameEl    (string|JSX) — filename, possibly with <mark> highlights,
 *     caseNumber (string),
 *     typeLabel  (string),
 *     date       (string),
 *     size       (string),
 *     relWidth   (string)   — CSS width for relevance bar e.g. "78%",
 *     open       (fn),
 *     goCase     (fn)
 *   }]
 *   onSetQuery    {fn}
 *   onClearQuery  {fn}
 */
export default function SearchPage({
  queryValue = "",
  hasResults = false,
  searchEmpty = false,
  searchIdle = true,
  resultCount = 0,
  searchRows = [],
  onSetQuery,
  onClearQuery,
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      <h1 style={{ margin: 0, fontSize: "30px", fontWeight: 700, color: "#e8eaf0" }}>Search Documents</h1>

      {/* Search bar */}
      <div style={{
        display: "flex", alignItems: "center", gap: "10px",
        height: "46px", padding: "0 14px",
        background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "8px",
        color: "#555869"
      }}>
        <Search size={20} />
        <input
          value={queryValue}
          onChange={onSetQuery}
          placeholder="Search filenames and document text…"
          style={{
            flex: 1, height: "44px", background: "transparent",
            border: "none", color: "#e8eaf0", fontSize: "17px"
          }}
        />
        <button
          type="button"
          title="Clear search"
          aria-label="Clear search"
          onClick={onClearQuery}
          style={{
            width: "28px", height: "28px", display: "flex", alignItems: "center", justifyContent: "center",
            background: "transparent", border: "none", borderRadius: "4px",
            color: "#8b8fa8", cursor: "pointer"
          }}
          /* hover: color #e8eaf0; background #1a1d24 */
        >
          <X size={16} />
        </button>
      </div>

      <div style={{ display: "flex", gap: "20px", alignItems: "flex-start", flexWrap: "wrap" }}>

        {/* ── Filters sidebar ── */}
        <div style={{
          width: "240px", flex: "none",
          background: "#111318", border: "1px solid #2a2d35", borderRadius: "8px",
          padding: "16px", display: "flex", flexDirection: "column", gap: "18px"
        }}>

          {/* Document type */}
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <div style={{ fontSize: "11px", letterSpacing: "0.06em", fontFamily: "'JetBrains Mono', monospace", color: "#555869" }}>DOCUMENT TYPE</div>
            {["FIR", "Evidence record", "Forensic report", "Court filing"].map((label) => (
              <label key={label} style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "#8b8fa8" }}>
                <input type="checkbox" /> {label}
              </label>
            ))}
          </div>

          {/* Date range */}
          <div style={{ display: "flex", flexDirection: "column", gap: "8px", borderTop: "1px solid #2a2d35", paddingTop: "16px" }}>
            <div style={{ fontSize: "11px", letterSpacing: "0.06em", fontFamily: "'JetBrains Mono', monospace", color: "#555869" }}>DATE RANGE</div>
            <input type="date" aria-label="From date" style={{ height: "32px", padding: "0 8px", background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px", color: "#8b8fa8", fontSize: "12px" }} />
            <input type="date" aria-label="To date" style={{ height: "32px", padding: "0 8px", background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px", color: "#8b8fa8", fontSize: "12px" }} />
          </div>

          {/* Tags */}
          <div style={{ display: "flex", flexDirection: "column", gap: "8px", borderTop: "1px solid #2a2d35", paddingTop: "16px" }}>
            <div style={{ fontSize: "11px", letterSpacing: "0.06em", fontFamily: "'JetBrains Mono', monospace", color: "#555869" }}>TAGS</div>
            <input placeholder="wallet, seizure" style={{ height: "32px", padding: "0 8px", background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px", color: "#e8eaf0", fontSize: "12px" }} />
          </div>

          {/* Case */}
          <div style={{ display: "flex", flexDirection: "column", gap: "8px", borderTop: "1px solid #2a2d35", paddingTop: "16px" }}>
            <div style={{ fontSize: "11px", letterSpacing: "0.06em", fontFamily: "'JetBrains Mono', monospace", color: "#555869" }}>CASE</div>
            <select aria-label="Case filter" style={{ height: "32px", padding: "0 6px", background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px", color: "#e8eaf0", fontSize: "12px" }}>
              <option>All cases</option>
              <option>CR-2026-0042</option>
              <option>CR-2026-0038</option>
              <option>CR-2026-0031</option>
            </select>
          </div>

          {/* OCR status */}
          <div style={{ display: "flex", flexDirection: "column", gap: "8px", borderTop: "1px solid #2a2d35", paddingTop: "16px" }}>
            <div style={{ fontSize: "11px", letterSpacing: "0.06em", fontFamily: "'JetBrains Mono', monospace", color: "#555869" }}>OCR STATUS</div>
            {["Verified", "Low confidence", "Not applicable"].map((label) => (
              <label key={label} style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "#8b8fa8" }}>
                <input type="checkbox" /> {label}
              </label>
            ))}
          </div>
        </div>

        {/* ── Results area ── */}
        <div style={{ flex: 1, minWidth: "340px", display: "flex", flexDirection: "column", gap: "10px" }}>

          {/* Results table */}
          {hasResults && (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              <div style={{ fontSize: "12px", color: "#8b8fa8" }}>{resultCount} found</div>
              <div style={{ background: "#111318", border: "1px solid #2a2d35", borderRadius: "8px", overflow: "hidden" }}>
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", minWidth: "820px", borderCollapse: "collapse" }}>
                    <thead>
                      <tr style={{ background: "#14161c" }}>
                        <th style={{ width: "40px", padding: "10px 0 10px 14px", borderBottom: "1px solid #2a2d35" }} />
                        <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>FILENAME</th>
                        <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>CASE</th>
                        <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>TYPE</th>
                        <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>DATE</th>
                        <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>SIZE</th>
                        <th style={{ textAlign: "left", padding: "10px 14px 10px 12px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>RELEVANCE</th>
                      </tr>
                    </thead>
                    <tbody>
                      {searchRows.map((r, i) => (
                        <tr key={i} onClick={r.open} style={{ cursor: "pointer" }} /* hover: background #1a1d24 */>
                          <td style={{ padding: "12px 0 12px 14px", borderBottom: "1px solid #1e2028", color: "#8b8fa8" }}>{r.icon}</td>
                          <td style={{ padding: "12px", borderBottom: "1px solid #1e2028", fontSize: "13px", color: "#e8eaf0", maxWidth: "280px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.nameEl}</td>
                          <td style={{ padding: "12px", borderBottom: "1px solid #1e2028" }}>
                            <button
                              type="button"
                              onClick={r.goCase}
                              style={{ background: "none", border: "none", padding: 0, fontFamily: "'JetBrains Mono', monospace", fontSize: "12px", color: "#3b82f6", cursor: "pointer" }}
                              /* hover: color #60a5fa */
                            >
                              {r.caseNumber}
                            </button>
                          </td>
                          <td style={{ padding: "12px", borderBottom: "1px solid #1e2028", fontSize: "11px", letterSpacing: "0.05em", color: "#8b8fa8", textTransform: "uppercase" }}>{r.typeLabel}</td>
                          <td style={{ padding: "12px", borderBottom: "1px solid #1e2028", fontSize: "13px", color: "#8b8fa8", whiteSpace: "nowrap" }}>{r.date}</td>
                          <td style={{ padding: "12px", borderBottom: "1px solid #1e2028", fontSize: "13px", color: "#8b8fa8", whiteSpace: "nowrap" }}>{r.size}</td>
                          <td style={{ padding: "12px 14px 12px 12px", borderBottom: "1px solid #1e2028", minWidth: "110px" }}>
                            <div style={{ height: "4px", background: "#1e2028", borderRadius: "2px", overflow: "hidden" }}>
                              <div style={{ height: "4px", width: r.relWidth, background: "#3b82f6" }} />
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* Empty state */}
          {searchEmpty && (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "10px", padding: "64px 24px", color: "#555869" }}>
              <Search size={36} />
              <div style={{ fontSize: "14px", color: "#8b8fa8" }}>No documents match your search.</div>
            </div>
          )}

          {/* Idle state */}
          {searchIdle && (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "10px", padding: "64px 24px", color: "#555869" }}>
              <Search size={36} />
              <div style={{ fontSize: "15px", color: "#e8eaf0" }}>Search across all your case documents.</div>
              <div style={{ fontSize: "13px", color: "#8b8fa8" }}>Filenames and OCR-extracted text are both indexed.</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
