import { useEffect, useState } from "react";
import { X } from "lucide-react";
import ReactMarkdown from "react-markdown";

import { approveOcr } from "../lib/documentApi";
import type { DocumentMeta } from "../types";

interface OcrApprovalModalProps {
  doc: DocumentMeta;
  onUpdated: (doc: DocumentMeta) => void;
  onClose: () => void;
}

type Phase = "review" | "formatting" | "comparison";

const SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];

export default function OcrApprovalModal({ doc, onUpdated, onClose }: OcrApprovalModalProps) {
  const isPendingReview = doc.ocrStatus === "AWAITING_APPROVAL";

  const [phase, setPhase] = useState<Phase>(isPendingReview ? "review" : "comparison");
  const [activeTab, setActiveTab] = useState<"raw" | "formatted">(isPendingReview ? "raw" : "formatted");
  const [rawText] = useState<string>(doc.ocrRawText ?? "");
  const [formattedText, setFormattedText] = useState<string>(doc.ocrFormattedText ?? "");
  const [error, setError] = useState("");
  const [spinnerIdx, setSpinnerIdx] = useState(0);

  const confidencePct = doc.ocrConfidence != null ? Math.round(doc.ocrConfidence * 100) : null;

  useEffect(() => {
    if (phase !== "formatting") return;
    const id = setInterval(() => setSpinnerIdx((i) => (i + 1) % SPINNER.length), 80);
    return () => clearInterval(id);
  }, [phase]);

  async function handleApprove() {
    setError("");
    setPhase("formatting");
    try {
      const updated = await approveOcr(doc.id, "approve");
      onUpdated(updated);
      setFormattedText(updated.ocrFormattedText ?? rawText);
      setPhase("comparison");
      setActiveTab("formatted");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Formatting failed");
      setPhase("review");
    }
  }

  async function handleDismiss() {
    setError("");
    try {
      const updated = await approveOcr(doc.id, "dismiss");
      onUpdated(updated);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    }
  }

  const displayText = activeTab === "raw" ? rawText : formattedText;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.72)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 50,
        padding: "16px",
      }}
      onClick={(e) => { if (phase !== "formatting" && e.target === e.currentTarget) onClose(); }}
    >
      <div
        style={{
          background: "#111318",
          border: "1px solid #2a2d35",
          borderRadius: "10px",
          width: "100%",
          maxWidth: "720px",
          maxHeight: "88vh",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        {/* ── Header ─────────────────────────────────────────────── */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            padding: "16px 20px",
            borderBottom: "1px solid #2a2d35",
            flexShrink: 0,
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: "15px", fontWeight: 600, color: "#e8eaf0" }}>
              {phase === "review" && "Review OCR Text"}
              {phase === "formatting" && "Formatting with AI…"}
              {phase === "comparison" && "OCR Result"}
            </div>
            <div
              style={{
                fontSize: "12px",
                color: "#8b8fa8",
                marginTop: "2px",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {doc.filename}
              {confidencePct != null && (
                <span style={{ marginLeft: "8px", color: confidencePct >= 80 ? "#22c55e" : "#f59e0b" }}>
                  · {confidencePct}% confidence
                </span>
              )}
              {doc.ocrPageCount != null && (
                <span style={{ marginLeft: "8px", color: "#555869" }}>
                  · {doc.ocrPageCount} page{doc.ocrPageCount !== 1 ? "s" : ""}
                </span>
              )}
            </div>
          </div>
          {phase !== "formatting" && (
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              style={{
                background: "none",
                border: "none",
                color: "#555869",
                cursor: "pointer",
                padding: "4px",
                display: "flex",
                alignItems: "center",
              }}
            >
              <X size={18} />
            </button>
          )}
        </div>

        {/* ── Formatting spinner ─────────────────────────────────── */}
        {phase === "formatting" && (
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: "16px",
              padding: "48px 24px",
            }}
          >
            <div
              style={{
                fontSize: "36px",
                fontFamily: "monospace",
                color: "#3b82f6",
                lineHeight: 1,
              }}
            >
              {SPINNER[spinnerIdx]}
            </div>
            <div style={{ fontSize: "14px", color: "#e8eaf0", fontWeight: 500 }}>
              Formatting with AI (orca-mini)…
            </div>
            <div style={{ fontSize: "12px", color: "#555869", textAlign: "center", maxWidth: "320px" }}>
              The local LLM is structuring the OCR text. This takes up to a minute
              and runs entirely offline.
            </div>
          </div>
        )}

        {/* ── Tabs (review + comparison) ─────────────────────────── */}
        {phase !== "formatting" && (
          <>
            {phase === "comparison" && (
              <div
                style={{
                  display: "flex",
                  gap: "2px",
                  borderBottom: "1px solid #2a2d35",
                  padding: "0 20px",
                  flexShrink: 0,
                }}
              >
                {(["raw", "formatted"] as const).map((tab) => {
                  const label = tab === "raw" ? "Raw OCR" : "AI Formatted";
                  const active = activeTab === tab;
                  return (
                    <button
                      key={tab}
                      type="button"
                      onClick={() => setActiveTab(tab)}
                      style={{
                        height: "36px",
                        padding: "0 12px",
                        background: "transparent",
                        border: "none",
                        borderBottom: `2px solid ${active ? "#3b82f6" : "transparent"}`,
                        color: active ? "#e8eaf0" : "#555869",
                        fontSize: "13px",
                        cursor: "pointer",
                      }}
                    >
                      {label}
                      {tab === "formatted" && !formattedText && (
                        <span style={{ marginLeft: "6px", fontSize: "10px", color: "#555869" }}>(unavailable)</span>
                      )}
                    </button>
                  );
                })}
              </div>
            )}

            {/* Low-confidence warning — review phase only */}
            {phase === "review" && doc.ocrConfidence != null && doc.ocrConfidence < 0.6 && (
              <div
                style={{
                  margin: "12px 20px 0",
                  padding: "10px 14px",
                  background: "#3d2008",
                  border: "1px solid #fb923c",
                  borderRadius: "6px",
                  fontSize: "12px",
                  color: "#fb923c",
                  lineHeight: 1.5,
                  flexShrink: 0,
                }}
              >
                <strong>Low confidence ({Math.round(doc.ocrConfidence * 100)}%)</strong>
                {" — "}the text below may contain errors. You can still approve it and correct it later, or dismiss and try Re-OCR.
              </div>
            )}

            {/* Text body */}
            <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>
              {displayText ? (
                activeTab === "formatted" ? (
                  <div className="ocr-md" style={{ color: "#e8eaf0", fontSize: "13px", lineHeight: 1.7 }}>
                    <ReactMarkdown>{displayText}</ReactMarkdown>
                  </div>
                ) : (
                  <pre
                    style={{
                      margin: 0,
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: "12px",
                      lineHeight: 1.65,
                      color: "#e8eaf0",
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                    }}
                  >
                    {displayText}
                  </pre>
                )
              ) : (
                <div style={{ fontSize: "13px", color: "#555869", textAlign: "center", paddingTop: "24px" }}>
                  {activeTab === "formatted"
                    ? "Formatted text not available — Ollama may have been unreachable."
                    : "No text available."}
                </div>
              )}
            </div>

            {/* Footer */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "10px",
                padding: "14px 20px",
                borderTop: "1px solid #2a2d35",
                flexShrink: 0,
              }}
            >
              {error && <span style={{ fontSize: "12px", color: "#ef4444", flex: 1 }}>{error}</span>}
              {!error && phase === "review" && (
                <span style={{ fontSize: "12px", color: "#8b8fa8", flex: 1 }}>
                  Approve to format with AI and store. Dismiss to discard OCR text.
                </span>
              )}
              {!error && phase === "comparison" && (
                <span style={{ fontSize: "12px", color: "#22c55e", flex: 1 }}>
                  Formatting complete — text has been stored and indexed.
                </span>
              )}

              {phase === "review" && (
                <>
                  <button
                    type="button"
                    onClick={handleDismiss}
                    style={{
                      height: "34px",
                      padding: "0 16px",
                      background: "transparent",
                      border: "1px solid #2a2d35",
                      borderRadius: "4px",
                      color: "#8b8fa8",
                      fontSize: "13px",
                      cursor: "pointer",
                    }}
                  >
                    Dismiss
                  </button>
                  <button
                    type="button"
                    onClick={handleApprove}
                    style={{
                      height: "34px",
                      padding: "0 16px",
                      background: "#3b82f6",
                      border: "none",
                      borderRadius: "4px",
                      color: "#ffffff",
                      fontSize: "13px",
                      fontWeight: 500,
                      cursor: "pointer",
                    }}
                  >
                    Approve & Format
                  </button>
                </>
              )}

              {phase === "comparison" && (
                <button
                  type="button"
                  onClick={onClose}
                  style={{
                    height: "34px",
                    padding: "0 16px",
                    background: "#3b82f6",
                    border: "none",
                    borderRadius: "4px",
                    color: "#ffffff",
                    fontSize: "13px",
                    fontWeight: 500,
                    cursor: "pointer",
                  }}
                >
                  Done
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
