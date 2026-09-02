/**
 * ShareModal — create share links for a document, all case documents, or the full case.
 *
 * Usage (document scope):
 *   <ShareModal scope="DOCUMENT" documentId={doc.id} filename={doc.filename} onClose={...} />
 *
 * Usage (case scope):
 *   <ShareModal scope="CASE_DOCUMENTS" caseId={case.id} caseTitle={case.title} onClose={...} />
 *   <ShareModal scope="CASE_FULL" caseId={case.id} caseTitle={case.title} onClose={...} />
 *
 * Requires TOTP step-up for every link creation.
 * Matches design/screens/ShareModal.jsx (colours, spacing, component structure).
 */

import { useState } from "react";
import { AlertTriangle, Copy, Share2, X } from "lucide-react";
import { createDocumentShare, createCaseShare } from "../lib/shareApi";
import { ApiError } from "../lib/apiClient";
import type { ShareScope } from "../types";

interface Props {
  scope: ShareScope;
  documentId?: string;
  filename?: string;
  caseId?: string;
  caseTitle?: string;
  onClose: () => void;
}

const SCOPE_LABELS: Record<ShareScope, string> = {
  DOCUMENT: "Share document",
  CASE_DOCUMENTS: "Share all case documents",
  CASE_FULL: "Share full case",
};

const SCOPE_DESC: Record<ShareScope, string> = {
  DOCUMENT: "Recipient can download this file.",
  CASE_DOCUMENTS: "Recipient can see and download all documents in this case.",
  CASE_FULL: "Recipient can see case metadata, members, and all documents.",
};

const EXPIRY_OPTIONS = [
  { label: "1 hour", value: 1 },
  { label: "6 hours", value: 6 },
  { label: "12 hours", value: 12 },
  { label: "24 hours", value: 24 },
  { label: "48 hours", value: 48 },
];

const MAX_USES_OPTIONS = [1, 3, 5, 10];

export default function ShareModal({ scope, documentId, filename, caseId, caseTitle, onClose }: Props) {
  const [email, setEmail] = useState("");
  const [expiresIn, setExpiresIn] = useState(24);
  const [maxUses, setMaxUses] = useState(3);
  const [note, setNote] = useState("");
  const [totp, setTotp] = useState("");
  const [allowDownload, setAllowDownload] = useState(true);
  const [shareUrl, setShareUrl] = useState("");
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const hasShareUrl = shareUrl !== "";
  const subjectLabel = scope === "DOCUMENT" ? filename : caseTitle;

  async function handleCreate() {
    setError("");
    if (!email.trim()) { setError("Recipient email is required."); return; }
    if (!totp.trim()) { setError("TOTP code is required to create a share link."); return; }

    setLoading(true);
    try {
      let result;
      if (scope === "DOCUMENT" && documentId) {
        result = await createDocumentShare(documentId, {
          expiresInHours: expiresIn,
          maxUses,
          allowedEmail: email.trim(),
          note: note.trim() || undefined,
          totpCode: totp.trim(),
          allowDownload,
        });
      } else if (caseId) {
        result = await createCaseShare(caseId, {
          shareScope: scope as "CASE_DOCUMENTS" | "CASE_FULL",
          expiresInHours: expiresIn,
          maxUses,
          allowedEmail: email.trim(),
          note: note.trim() || undefined,
          totpCode: totp.trim(),
          allowDownload,
        });
      } else {
        setError("Missing ID for share creation.");
        return;
      }
      setShareUrl(result.shareUrl);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to create share link.");
      }
    } finally {
      setLoading(false);
    }
  }

  function handleCopy() {
    void navigator.clipboard.writeText(shareUrl).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 90,
      background: "rgba(0,0,0,0.6)",
      display: "flex", alignItems: "center", justifyContent: "center",
      padding: "24px",
    }}>
      <div style={{
        width: "512px", maxWidth: "100%",
        background: "#1a1d24", border: "1px solid #2a2d35", borderRadius: "8px",
        boxShadow: "0 28px 60px rgba(0,0,0,0.6)",
        padding: "22px", display: "flex", flexDirection: "column", gap: "16px",
        maxHeight: "90vh", overflowY: "auto",
      }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ color: "#3b82f6", display: "flex" }}><Share2 size={18} /></span>
          <span style={{ fontSize: "17px", fontWeight: 600, color: "#e8eaf0" }}>
            {SCOPE_LABELS[scope]}
          </span>
          <button
            type="button"
            aria-label="Close"
            onClick={onClose}
            style={{
              marginLeft: "auto", width: "28px", height: "28px",
              display: "flex", alignItems: "center", justifyContent: "center",
              background: "transparent", border: "none", borderRadius: "4px",
              color: "#8b8fa8", cursor: "pointer",
            }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Subject */}
        <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "12px", color: "#8b8fa8", wordBreak: "break-all" }}>
          {subjectLabel}
        </div>

        {/* Scope description */}
        <div style={{
          background: "#111318", border: "1px solid #2a2d35", borderRadius: "6px",
          padding: "9px 12px", fontSize: "12px", color: "#8b8fa8",
        }}>
          {SCOPE_DESC[scope]}
        </div>

        {/* Recipient email */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <label htmlFor="sm-email" style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>
            Recipient email <span style={{ color: "#ef4444" }}>*</span>
          </label>
          <input
            id="sm-email"
            type="email"
            placeholder="prosecutor@court.gov.in"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={hasShareUrl}
            style={{
              height: "34px", padding: "0 10px",
              background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px",
              color: "#e8eaf0", fontSize: "13px",
            }}
          />
        </div>

        {/* Expiry + max uses */}
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px", flex: 1, minWidth: "140px" }}>
            <label htmlFor="sm-exp" style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>Expires in</label>
            <select
              id="sm-exp"
              value={expiresIn}
              onChange={(e) => setExpiresIn(Number(e.target.value))}
              disabled={hasShareUrl}
              style={{ height: "34px", padding: "0 8px", background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px", color: "#e8eaf0", fontSize: "13px" }}
            >
              {EXPIRY_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px", flex: 1, minWidth: "140px" }}>
            <label htmlFor="sm-uses" style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>Maximum uses</label>
            <select
              id="sm-uses"
              value={maxUses}
              onChange={(e) => setMaxUses(Number(e.target.value))}
              disabled={hasShareUrl}
              style={{ height: "34px", padding: "0 8px", background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px", color: "#e8eaf0", fontSize: "13px" }}
            >
              {MAX_USES_OPTIONS.map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
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
            placeholder="For remand hearing on 2 Sep."
            value={note}
            onChange={(e) => setNote(e.target.value)}
            disabled={hasShareUrl}
            style={{
              padding: "8px 10px",
              background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px",
              color: "#e8eaf0", fontSize: "13px", resize: "vertical",
            }}
          />
        </div>

        {/* Allow download toggle */}
        {!hasShareUrl && (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 12px", background: "#111318", border: "1px solid #2a2d35", borderRadius: "6px" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "3px" }}>
              <span style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>Allow download</span>
              <span style={{ fontSize: "11px", color: "#555869" }}>
                {allowDownload ? "Recipient can download the file" : "Recipient can only view — download is blocked"}
              </span>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={allowDownload}
              onClick={() => setAllowDownload(v => !v)}
              style={{
                width: "40px", height: "22px", borderRadius: "11px", border: "none",
                background: allowDownload ? "#3b82f6" : "#2a2d35",
                cursor: "pointer", position: "relative", transition: "background 0.2s", flexShrink: 0,
              }}
            >
              <span style={{
                position: "absolute", top: "3px",
                left: allowDownload ? "21px" : "3px",
                width: "16px", height: "16px", borderRadius: "50%", background: "#e8eaf0",
                transition: "left 0.2s",
              }} />
            </button>
          </div>
        )}

        {/* TOTP */}
        {!hasShareUrl && (
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <label htmlFor="sm-totp" style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>
              Authenticator code <span style={{ color: "#ef4444" }}>*</span>
            </label>
            <input
              id="sm-totp"
              type="text"
              inputMode="numeric"
              placeholder="6-digit code"
              maxLength={6}
              value={totp}
              onChange={(e) => setTotp(e.target.value.replace(/\D/g, ""))}
              style={{
                height: "34px", padding: "0 10px", width: "160px",
                background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px",
                color: "#e8eaf0", fontSize: "13px", fontFamily: "'JetBrains Mono', monospace",
                letterSpacing: "0.2em",
              }}
            />
            <span style={{ fontSize: "11px", color: "#555869" }}>
              Sharing requires MFA verification.
            </span>
          </div>
        )}

        {/* Error */}
        {error && (
          <div style={{
            background: "#3d1010", border: "1px solid #ef4444",
            borderRadius: "6px", padding: "9px 11px", fontSize: "12px", color: "#ef4444",
          }}>
            {error}
          </div>
        )}

        {/* Generated URL */}
        {hasShareUrl && (
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <div style={{
              display: "flex", alignItems: "center", gap: "8px",
              background: "#1e2028", border: "1px solid #2a2d35",
              borderRadius: "6px", padding: "10px",
            }}>
              <code style={{ flex: 1, fontFamily: "'JetBrains Mono', monospace", fontSize: "11px", color: "#e8eaf0", wordBreak: "break-all" }}>
                {shareUrl}
              </code>
              <button
                type="button"
                onClick={handleCopy}
                style={{
                  height: "28px", padding: "0 10px", flexShrink: 0,
                  display: "flex", alignItems: "center", gap: "6px",
                  background: "#1a1d24", border: "1px solid #2a2d35", borderRadius: "4px",
                  color: "#e8eaf0", fontSize: "12px", cursor: "pointer",
                }}
              >
                <Copy size={14} /> {copied ? "Copied!" : "Copy"}
              </button>
            </div>
            <div style={{
              display: "flex", alignItems: "center", gap: "8px",
              background: "#3d2c08", border: "1px solid #f59e0b",
              borderRadius: "6px", padding: "9px 11px", fontSize: "12px", color: "#e8eaf0",
            }}>
              <span style={{ color: "#f59e0b", display: "flex" }}><AlertTriangle size={14} /></span>
              This URL will not be shown again. The link is restricted to {email}.
            </div>
          </div>
        )}

        {/* Footer */}
        <div style={{ display: "flex", gap: "8px", borderTop: "1px solid #2a2d35", paddingTop: "16px" }}>
          {!hasShareUrl && (
            <button
              type="button"
              onClick={() => void handleCreate()}
              disabled={loading}
              style={{
                height: "34px", padding: "0 16px",
                background: loading ? "#1e3a5f" : "#3b82f6", color: "#ffffff",
                border: "none", borderRadius: "4px",
                fontSize: "14px", fontWeight: 500, cursor: loading ? "not-allowed" : "pointer",
              }}
            >
              {loading ? "Creating…" : "Create Link"}
            </button>
          )}
          <button
            type="button"
            onClick={onClose}
            style={{
              height: "34px", padding: "0 14px",
              background: "transparent", border: "1px solid #2a2d35", borderRadius: "4px",
              color: "#8b8fa8", fontSize: "14px", cursor: "pointer",
            }}
          >
            {hasShareUrl ? "Done" : "Cancel"}
          </button>
        </div>
      </div>
    </div>
  );
}
