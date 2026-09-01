// DESIGN REFERENCE — match this layout exactly when building src/components/DocumentDetailPanel.tsx

import { X, Download, PenLine, Share2, BadgeCheck } from 'lucide-react';

/**
 * Slide-in panel anchored to the right side of the viewport.
 * Appears when a document row is clicked in DocumentsTab.
 *
 * Props:
 *   panel  {object | null}  — null hides the panel; when open:
 *     {
 *       icon        (JSX),
 *       filename    (string),
 *       typeLabel   (string),
 *       size        (string),
 *       chunks      (number|string),
 *       status      (string)     — e.g. "VERIFIED"
 *       hash        (string)     — SHA-256 hex
 *       ocr         { icon (JSX), color, label }
 *       sigs        [{ icon (JSX), name, rb { color, bg, text }, at }]
 *       noSigs      (boolean)
 *       tags        [{ label }]
 *       uploadedBy  (string)
 *       created     (string)
 *       close       (fn)
 *       download    (fn)
 *       sign        (fn)
 *       share       (fn)
 *     }
 */
export default function DocumentDetailPanel({ panel }) {
  if (!panel) return null;

  return (
    <div style={{
      position: "fixed", right: 0, top: "56px", bottom: 0,
      width: "400px", maxWidth: "100%", zIndex: 45,
      background: "#111318", borderLeft: "1px solid #2a2d35",
      boxShadow: "-18px 0 40px rgba(0,0,0,0.45)",
      padding: "18px 20px", overflowY: "auto",
      display: "flex", flexDirection: "column", gap: "18px",
      animation: "slidein 180ms ease-out"
    }}>

      {/* Panel header */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: "10px" }}>
        <div style={{ color: "#3b82f6", marginTop: "2px", display: "flex" }}>{panel.icon}</div>
        <div style={{ fontSize: "14px", fontWeight: 500, color: "#e8eaf0", wordBreak: "break-all", lineHeight: 1.4 }}>
          {panel.filename}
        </div>
        <button
          type="button"
          title="Close panel"
          aria-label="Close panel"
          onClick={panel.close}
          style={{
            marginLeft: "auto", width: "28px", height: "28px", flex: "none",
            display: "flex", alignItems: "center", justifyContent: "center",
            background: "transparent", border: "none", borderRadius: "4px",
            color: "#8b8fa8", cursor: "pointer"
          }}
          /* hover: color #e8eaf0; background #1a1d24 */
        >
          <X size={16} />
        </button>
      </div>

      {/* Metadata grid */}
      <div style={{ display: "grid", gridTemplateColumns: "84px 1fr", gap: "10px 12px", fontSize: "13px" }}>
        <span style={{ color: "#8b8fa8" }}>Type</span>
        <span style={{ color: "#e8eaf0" }}>{panel.typeLabel}</span>

        <span style={{ color: "#8b8fa8" }}>Size</span>
        <span style={{ color: "#e8eaf0" }}>{panel.size}</span>

        <span style={{ color: "#8b8fa8" }}>Chunks</span>
        <span style={{ color: "#e8eaf0" }}>{panel.chunks}</span>

        <span style={{ color: "#8b8fa8" }}>Status</span>
        <span style={{ color: "#22c55e" }}>{panel.status}</span>

        <span style={{ color: "#8b8fa8" }}>SHA-256</span>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace", fontSize: "11px",
          color: "#8b8fa8", wordBreak: "break-all"
        }}>{panel.hash}</span>
      </div>

      {/* OCR status */}
      <div style={{ display: "flex", flexDirection: "column", gap: "8px", borderTop: "1px solid #2a2d35", paddingTop: "16px" }}>
        <div style={{ fontSize: "11px", letterSpacing: "0.06em", color: "#555869", fontFamily: "'JetBrains Mono', monospace" }}>
          OCR STATUS
        </div>
        <span style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "13px", color: panel.ocr.color }}>
          {panel.ocr.icon} {panel.ocr.label}
        </span>
      </div>

      {/* Signatures */}
      <div style={{ display: "flex", flexDirection: "column", gap: "10px", borderTop: "1px solid #2a2d35", paddingTop: "16px" }}>
        <div style={{ fontSize: "11px", letterSpacing: "0.06em", color: "#555869", fontFamily: "'JetBrains Mono', monospace" }}>
          SIGNATURES
        </div>
        {panel.sigs.map((g, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "#e8eaf0" }}>
            <span style={{ color: "#22c55e", display: "flex" }}>{g.icon}</span>
            <span>{g.name}</span>
            <span style={{
              fontSize: "10px", letterSpacing: "0.05em",
              padding: "2px 6px", borderRadius: "4px",
              color: g.rb.color, background: g.rb.bg
            }}>{g.rb.text}</span>
            <span style={{ marginLeft: "auto", fontSize: "11px", color: "#555869", whiteSpace: "nowrap" }}>{g.at}</span>
          </div>
        ))}
        {panel.noSigs && (
          <div style={{ fontSize: "13px", color: "#555869" }}>Not signed yet.</div>
        )}
      </div>

      {/* Tags */}
      <div style={{ display: "flex", flexDirection: "column", gap: "8px", borderTop: "1px solid #2a2d35", paddingTop: "16px" }}>
        <div style={{ fontSize: "11px", letterSpacing: "0.06em", color: "#555869", fontFamily: "'JetBrains Mono', monospace" }}>
          TAGS
        </div>
        <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
          {panel.tags.map((t, i) => (
            <span key={i} style={{
              fontSize: "11px", padding: "3px 8px", borderRadius: "6px",
              background: "#1e2028", border: "1px solid #2a2d35", color: "#8b8fa8"
            }}>
              {t.label}
            </span>
          ))}
        </div>
      </div>

      {/* Uploaded by */}
      <div style={{ display: "grid", gridTemplateColumns: "84px 1fr", gap: "10px 12px", fontSize: "13px", borderTop: "1px solid #2a2d35", paddingTop: "16px" }}>
        <span style={{ color: "#8b8fa8" }}>Uploaded by</span>
        <span style={{ color: "#e8eaf0" }}>{panel.uploadedBy}</span>

        <span style={{ color: "#8b8fa8" }}>Uploaded</span>
        <span style={{ color: "#8b8fa8" }}>{panel.created}</span>
      </div>

      {/* Action buttons */}
      <div style={{ display: "flex", gap: "8px", marginTop: "auto", paddingTop: "16px", borderTop: "1px solid #2a2d35" }}>
        <button
          type="button"
          onClick={panel.download}
          style={{
            flex: 1, height: "34px", display: "flex", alignItems: "center", justifyContent: "center", gap: "6px",
            background: "#3b82f6", color: "#ffffff", border: "none", borderRadius: "4px",
            fontSize: "13px", fontWeight: 500, cursor: "pointer"
          }}
          /* hover: background #2563eb */
        >
          <Download size={14} /> Download
        </button>
        <button
          type="button"
          onClick={panel.sign}
          style={{
            height: "34px", padding: "0 12px", display: "flex", alignItems: "center", gap: "6px",
            background: "#1a1d24", border: "1px solid #2a2d35", borderRadius: "4px",
            color: "#e8eaf0", fontSize: "13px", cursor: "pointer"
          }}
          /* hover: background #1e2028 */
        >
          <PenLine size={14} /> Sign
        </button>
        <button
          type="button"
          onClick={panel.share}
          style={{
            height: "34px", padding: "0 12px", display: "flex", alignItems: "center", gap: "6px",
            background: "#1a1d24", border: "1px solid #2a2d35", borderRadius: "4px",
            color: "#e8eaf0", fontSize: "13px", cursor: "pointer"
          }}
          /* hover: background #1e2028 */
        >
          <Share2 size={14} /> Share
        </button>
      </div>
    </div>
  );
}
