// DESIGN REFERENCE — match this layout exactly when building src/components/ShareModal.tsx

import { Share2, X, AlertTriangle, Copy } from 'lucide-react';

/**
 * Props:
 *   modalFilename   {string}   — filename shown in monospace
 *   hasShareUrl     {boolean}  — share URL was generated; show the copy row
 *   shareUrl        {string}   — the generated URL
 *   copiedUrl       {string}   — "Copy" or "Copied!" label
 *   onCreateLink    {fn}
 *   onCopyUrl       {fn}
 *   onClose         {fn}
 */
export default function ShareModal({
  modalFilename = "",
  hasShareUrl = false,
  shareUrl = "",
  copiedUrl = "Copy",
  onCreateLink,
  onCopyUrl,
  onClose,
}) {
  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 90,
      background: "rgba(0,0,0,0.6)",
      display: "flex", alignItems: "center", justifyContent: "center",
      padding: "24px", animation: "fadein 120ms ease-out"
    }}>
      <div style={{
        width: "512px", maxWidth: "100%",
        background: "#1a1d24", border: "1px solid #2a2d35", borderRadius: "8px",
        boxShadow: "0 28px 60px rgba(0,0,0,0.6)",
        padding: "22px", display: "flex", flexDirection: "column", gap: "16px"
      }}>

        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ color: "#3b82f6", display: "flex" }}><Share2 size={18} /></span>
          <span style={{ fontSize: "17px", fontWeight: 600, color: "#e8eaf0" }}>Share document</span>
          <button
            type="button"
            title="Close"
            aria-label="Close"
            onClick={onClose}
            style={{
              marginLeft: "auto", width: "28px", height: "28px",
              display: "flex", alignItems: "center", justifyContent: "center",
              background: "transparent", border: "none", borderRadius: "4px",
              color: "#8b8fa8", cursor: "pointer"
            }}
            /* hover: color #e8eaf0; background #1e2028 */
          >
            <X size={16} />
          </button>
        </div>

        {/* Filename */}
        <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "12px", color: "#8b8fa8", wordBreak: "break-all" }}>
          {modalFilename}
        </div>

        {/* Recipient email */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <label htmlFor="sm-email" style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>Recipient email</label>
          <input
            id="sm-email"
            type="email"
            placeholder="prosecutor@court.gov.in"
            style={{
              height: "34px", padding: "0 10px",
              background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px",
              color: "#e8eaf0", fontSize: "13px"
            }}
          />
        </div>

        {/* Expiry + max uses */}
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px", flex: 1, minWidth: "140px" }}>
            <label htmlFor="sm-exp" style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>Expires in</label>
            <select id="sm-exp" style={{ height: "34px", padding: "0 8px", background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px", color: "#e8eaf0", fontSize: "13px" }}>
              <option>24 hours</option>
              <option>1 hour</option>
              <option>6 hours</option>
              <option>12 hours</option>
              <option>48 hours</option>
            </select>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px", flex: 1, minWidth: "140px" }}>
            <label htmlFor="sm-uses" style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>Maximum uses</label>
            <select id="sm-uses" style={{ height: "34px", padding: "0 8px", background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px", color: "#e8eaf0", fontSize: "13px" }}>
              <option>3</option>
              <option>1</option>
              <option>5</option>
              <option>10</option>
            </select>
          </div>
        </div>

        {/* Note */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <label htmlFor="sm-note" style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>
            Note <span style={{ color: "#8b8fa8", fontWeight: 400 }}>(optional)</span>
          </label>
          <textarea
            id="sm-note"
            rows={2}
            placeholder="For remand hearing on 29 Aug."
            style={{
              padding: "8px 10px",
              background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px",
              color: "#e8eaf0", fontSize: "13px", resize: "vertical"
            }}
          />
        </div>

        {/* Generated URL */}
        {hasShareUrl && (
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <div style={{
              display: "flex", alignItems: "center", gap: "8px",
              background: "#1e2028", border: "1px solid #2a2d35",
              borderRadius: "6px", padding: "10px"
            }}>
              <code style={{ flex: 1, fontFamily: "'JetBrains Mono', monospace", fontSize: "12px", color: "#e8eaf0", wordBreak: "break-all" }}>
                {shareUrl}
              </code>
              <button
                type="button"
                onClick={onCopyUrl}
                style={{
                  height: "28px", padding: "0 10px",
                  display: "flex", alignItems: "center", gap: "6px",
                  background: "#1a1d24", border: "1px solid #2a2d35", borderRadius: "4px",
                  color: "#e8eaf0", fontSize: "12px", cursor: "pointer"
                }}
                /* hover: background #14161c */
              >
                <Copy size={14} /> {copiedUrl}
              </button>
            </div>
            <div style={{
              display: "flex", alignItems: "center", gap: "8px",
              background: "#3d2c08", border: "1px solid #f59e0b",
              borderRadius: "6px", padding: "9px 11px", fontSize: "12px", color: "#e8eaf0"
            }}>
              <span style={{ color: "#f59e0b", display: "flex" }}><AlertTriangle size={14} /></span>
              This URL will not be shown again.
            </div>
          </div>
        )}

        {/* Footer actions */}
        <div style={{ display: "flex", gap: "8px", borderTop: "1px solid #2a2d35", paddingTop: "16px" }}>
          <button
            type="button"
            onClick={onCreateLink}
            style={{
              height: "34px", padding: "0 16px",
              background: "#3b82f6", color: "#ffffff",
              border: "none", borderRadius: "4px",
              fontSize: "14px", fontWeight: 500, cursor: "pointer"
            }}
            /* hover: background #2563eb */
          >
            Create Link
          </button>
          <button
            type="button"
            onClick={onClose}
            style={{
              height: "34px", padding: "0 14px",
              background: "transparent", border: "1px solid #2a2d35", borderRadius: "4px",
              color: "#8b8fa8", fontSize: "14px", cursor: "pointer"
            }}
            /* hover: color #e8eaf0 */
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
