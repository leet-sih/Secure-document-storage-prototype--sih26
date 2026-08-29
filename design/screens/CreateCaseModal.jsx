// DESIGN REFERENCE — match this layout exactly when building src/components/CreateCaseModal.tsx (or inline in DashboardPage)

import { X } from 'lucide-react';

/**
 * Props:
 *   onSubmit {fn}
 *   onClose  {fn}
 */
export default function CreateCaseModal({ onSubmit, onClose }) {
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
        padding: "22px", display: "flex", flexDirection: "column", gap: "14px"
      }}>

        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "17px", fontWeight: 600, color: "#e8eaf0" }}>New case</span>
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

        {/* Case number + Status */}
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px", flex: 1, minWidth: "160px" }}>
            <label htmlFor="nc-num" style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>Case number</label>
            <input
              id="nc-num"
              placeholder="CR-2026-0043"
              style={{
                height: "34px", padding: "0 10px",
                background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px",
                color: "#e8eaf0", fontFamily: "'JetBrains Mono', monospace", fontSize: "13px"
              }}
            />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px", flex: 1, minWidth: "160px" }}>
            <label htmlFor="nc-status" style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>Status</label>
            <select
              id="nc-status"
              style={{
                height: "34px", padding: "0 8px",
                background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px",
                color: "#e8eaf0", fontSize: "13px"
              }}
            >
              <option>OPEN</option>
              <option>UNDER_INVESTIGATION</option>
            </select>
          </div>
        </div>

        {/* Title */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <label htmlFor="nc-title" style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>Title</label>
          <input
            id="nc-title"
            placeholder="Short descriptive title"
            style={{
              height: "34px", padding: "0 10px",
              background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px",
              color: "#e8eaf0", fontSize: "13px"
            }}
          />
        </div>

        {/* Description */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <label htmlFor="nc-desc" style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>Description</label>
          <textarea
            id="nc-desc"
            rows={3}
            style={{
              padding: "8px 10px",
              background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px",
              color: "#e8eaf0", fontSize: "13px", resize: "vertical"
            }}
          />
        </div>

        {/* Priority */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px", maxWidth: "200px" }}>
          <label htmlFor="nc-pri" style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>Priority</label>
          <select
            id="nc-pri"
            style={{
              height: "34px", padding: "0 8px",
              background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px",
              color: "#e8eaf0", fontSize: "13px"
            }}
          >
            <option>NORMAL</option>
            <option>LOW</option>
            <option>HIGH</option>
            <option>CRITICAL</option>
          </select>
        </div>

        {/* Actions */}
        <div style={{ display: "flex", gap: "8px", borderTop: "1px solid #2a2d35", paddingTop: "16px" }}>
          <button
            type="button"
            onClick={onSubmit}
            style={{
              height: "34px", padding: "0 16px",
              background: "#3b82f6", color: "#ffffff",
              border: "none", borderRadius: "4px",
              fontSize: "14px", fontWeight: 500, cursor: "pointer"
            }}
            /* hover: background #2563eb */
          >
            Create Case
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
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
