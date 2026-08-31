import { useState } from "react";
import { X } from "lucide-react";
import { createCase } from "../lib/caseApi";
import type { CaseDetail } from "../types";

interface Props {
  onCreated: (c: CaseDetail) => void;
  onClose: () => void;
}

export default function CreateCaseModal({ onCreated, onClose }: Props) {
  const [caseNumber, setCaseNumber] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("NORMAL");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit() {
    if (!caseNumber.trim() || !title.trim()) {
      setError("Case number and title are required.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const c = await createCase({
        caseNumber: caseNumber.trim(),
        title: title.trim(),
        description: description.trim() || undefined,
        priority,
      });
      onCreated(c);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create case.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 90,
        background: "rgba(0,0,0,0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px",
        animation: "fadein 120ms ease-out",
      }}
    >
      <div
        style={{
          width: "512px",
          maxWidth: "100%",
          background: "#1a1d24",
          border: "1px solid #2a2d35",
          borderRadius: "8px",
          boxShadow: "0 28px 60px rgba(0,0,0,0.6)",
          padding: "22px",
          display: "flex",
          flexDirection: "column",
          gap: "14px",
        }}
      >
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "17px", fontWeight: 600, color: "#e8eaf0" }}>
            New case
          </span>
          <button
            type="button"
            onClick={onClose}
            style={{
              marginLeft: "auto",
              width: "28px",
              height: "28px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background: "transparent",
              border: "none",
              borderRadius: "4px",
              color: "#8b8fa8",
              cursor: "pointer",
            }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Case number */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <label
            htmlFor="nc-num"
            style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}
          >
            Case number
          </label>
          <input
            id="nc-num"
            placeholder="CR-2026-0043"
            value={caseNumber}
            onChange={(e) => setCaseNumber(e.target.value)}
            style={{
              height: "34px",
              padding: "0 10px",
              background: "#1e2028",
              border: "1px solid #2a2d35",
              borderRadius: "6px",
              color: "#e8eaf0",
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: "13px",
            }}
          />
        </div>

        {/* Title */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <label
            htmlFor="nc-title"
            style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}
          >
            Title
          </label>
          <input
            id="nc-title"
            placeholder="Short descriptive title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            style={{
              height: "34px",
              padding: "0 10px",
              background: "#1e2028",
              border: "1px solid #2a2d35",
              borderRadius: "6px",
              color: "#e8eaf0",
              fontSize: "13px",
            }}
          />
        </div>

        {/* Description */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <label
            htmlFor="nc-desc"
            style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}
          >
            Description
          </label>
          <textarea
            id="nc-desc"
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            style={{
              padding: "8px 10px",
              background: "#1e2028",
              border: "1px solid #2a2d35",
              borderRadius: "6px",
              color: "#e8eaf0",
              fontSize: "13px",
              resize: "vertical",
            }}
          />
        </div>

        {/* Priority */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "6px",
            maxWidth: "200px",
          }}
        >
          <label
            htmlFor="nc-pri"
            style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}
          >
            Priority
          </label>
          <select
            id="nc-pri"
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            style={{
              height: "34px",
              padding: "0 8px",
              background: "#1e2028",
              border: "1px solid #2a2d35",
              borderRadius: "6px",
              color: "#e8eaf0",
              fontSize: "13px",
            }}
          >
            <option value="NORMAL">Normal</option>
            <option value="LOW">Low</option>
            <option value="HIGH">High</option>
            <option value="CRITICAL">Critical</option>
          </select>
        </div>

        {error && (
          <div style={{ fontSize: "13px", color: "#ef4444" }}>{error}</div>
        )}

        {/* Actions */}
        <div
          style={{
            display: "flex",
            gap: "8px",
            borderTop: "1px solid #2a2d35",
            paddingTop: "16px",
          }}
        >
          <button
            type="button"
            onClick={handleSubmit}
            disabled={loading}
            style={{
              height: "34px",
              padding: "0 16px",
              background: "#3b82f6",
              color: "#ffffff",
              border: "none",
              borderRadius: "4px",
              fontSize: "14px",
              fontWeight: 500,
              cursor: loading ? "not-allowed" : "pointer",
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? "Creating…" : "Create Case"}
          </button>
          <button
            type="button"
            onClick={onClose}
            style={{
              height: "34px",
              padding: "0 14px",
              background: "transparent",
              border: "1px solid #2a2d35",
              borderRadius: "4px",
              color: "#8b8fa8",
              fontSize: "14px",
              cursor: "pointer",
            }}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
