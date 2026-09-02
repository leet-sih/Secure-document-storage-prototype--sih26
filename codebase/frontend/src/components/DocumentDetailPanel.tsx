/**
 * DocumentDetailPanel — slide-in right panel showing doc metadata, signatures, and actions.
 * Matches design/screens/DocumentDetailPanel.jsx exactly.
 */

import { useEffect, useState } from "react";
import { BadgeCheck, CheckCircle2, Download, PenLine, RefreshCw, Share2, Shield, ShieldAlert, ShieldCheck, X, XCircle } from "lucide-react";
import { checkDocumentIntegrity } from "../lib/documentApi";

import type { CurrentUser, DocumentMeta } from "../types";
import { useSignatures } from "../hooks/useSignatures";
import type { Signature } from "../hooks/useSignatures";

interface Props {
  doc: DocumentMeta;
  currentUser: CurrentUser | null;
  onClose: () => void;
  onDownload: () => Promise<void>;
  initialSignFormOpen?: boolean;
}

const TYPE_LABEL: Record<string, string> = {
  EVIDENCE_RECORD: "Evidence record", FIR: "FIR", FORENSIC_REPORT: "Forensic report",
  WITNESS_STATEMENT: "Witness statement", CHARGE_SHEET: "Charge sheet",
  COURT_FILING: "Court filing", INVESTIGATION_RECORD: "Investigation record",
  POLICE_REPORT: "Police report", LEGAL_NOTICE: "Legal notice",
  JUDGMENT: "Judgment", OTHER: "Other",
};

const ROLE_LABEL: Record<string, string> = {
  SUPER_ADMIN: "System Admin", CASE_OFFICER: "Case Officer", INVESTIGATOR: "Investigator",
  PROSECUTOR: "Prosecutor", AUDITOR: "Auditor", VIEWER: "Viewer",
};

const ROLE_COLOR: Record<string, string> = {
  SUPER_ADMIN: "#3b82f6", CASE_OFFICER: "#6366f1", INVESTIGATOR: "#f59e0b",
  PROSECUTOR: "#22c55e", AUDITOR: "#8b8fa8", VIEWER: "#555869",
};

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1048576) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1048576).toFixed(1)} MB`;
}

function formatDateTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" }) +
      " · " + d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
  } catch { return iso; }
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
  } catch { return iso; }
}

function SigStatusBadge({ sig }: { sig: Signature }) {
  if (sig.revoked_at) {
    return <span style={{ fontSize: 10, padding: "2px 6px", borderRadius: 4, color: "#8b8fa8", background: "#1a1d24", border: "1px solid #2a2d35" }}>REVOKED</span>;
  }
  if (sig.is_valid === true) {
    return <span style={{ fontSize: 10, padding: "2px 6px", borderRadius: 4, color: "#22c55e", background: "#14391f" }}>VALID</span>;
  }
  if (sig.is_valid === false) {
    return <span style={{ fontSize: 10, padding: "2px 6px", borderRadius: 4, color: "#ef4444", background: "#3d1010" }}>INVALID</span>;
  }
  return <span style={{ fontSize: 10, padding: "2px 6px", borderRadius: 4, color: "#555869", background: "#1a1d24" }}>UNVERIFIED</span>;
}

function OcrStatusRow({ doc }: { doc: DocumentMeta }) {
  const { ocrStatus, ocrConfidence } = doc;
  if (!ocrStatus || ocrStatus === "NOT_APPLICABLE" || ocrStatus === "PENDING") return null;

  const pct = ocrConfidence != null ? Math.round(ocrConfidence * 100) : null;

  if (ocrStatus === "DONE") {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "#22c55e" }}>
        <CheckCircle2 size={14} />
        Verified{pct != null ? ` (${pct}%)` : ""}
      </div>
    );
  }
  if (ocrStatus === "AWAITING_APPROVAL") {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "#f59e0b" }}>
        <CheckCircle2 size={14} />
        Pending review{pct != null ? ` · ${pct}%` : ""}
      </div>
    );
  }
  if (ocrStatus === "FAILED") {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "#ef4444" }}>
        <XCircle size={14} />
        Failed{pct != null ? ` · ${pct}%` : ""}
      </div>
    );
  }
  return null;
}

export default function DocumentDetailPanel({ doc, currentUser, onClose, onDownload, initialSignFormOpen = false }: Props) {
  const { signatures, loading: sigLoading, error: sigError, listSignatures, sign, verifySignatures, revokeSignature } = useSignatures(doc.id);

  const [showSignForm, setShowSignForm] = useState(initialSignFormOpen);
  const [comment, setComment] = useState("");
  const [signing, setSigning] = useState(false);
  const [signError, setSignError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [ocrTab, setOcrTab] = useState<"formatted" | "raw">("formatted");
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [integrityState, setIntegrityState] = useState<"idle" | "checking" | "ok" | "violated">("idle");

  const canSign = currentUser?.role === "SUPER_ADMIN" || currentUser?.role === "CASE_OFFICER" || currentUser?.role === "INVESTIGATOR";
  const alreadySigned = signatures.some(s => s.signer.id === currentUser?.id && !s.revoked_at);

  useEffect(() => {
    void listSignatures();
  }, [listSignatures]);

  useEffect(() => {
    setShowSignForm(initialSignFormOpen);
    setComment("");
    setSignError(null);
    setDownloadError(null);
    setIntegrityState("idle");
  }, [initialSignFormOpen, doc.id]);

  const handleSign = async () => {
    setSigning(true);
    setSignError(null);
    const result = await sign(comment.trim() || undefined);
    if (result) {
      setShowSignForm(false);
      setComment("");
    } else {
      setSignError("Failed to sign. You may have already signed this document.");
    }
    setSigning(false);
  };

  const handleVerify = async () => {
    setVerifying(true);
    await verifySignatures();
    setVerifying(false);
  };

  const handleRevoke = async (sigId: string) => {
    if (!confirm("Revoke this signature? The record is kept for audit purposes.")) return;
    await revokeSignature(sigId);
  };

  const handleDownload = async () => {
    setDownloadError(null);
    try {
      await onDownload();
    } catch (err) {
      setDownloadError(err instanceof Error ? err.message : "Download failed");
    }
  };

  const handleCheckIntegrity = async () => {
    setIntegrityState("checking");
    try {
      await checkDocumentIntegrity(doc.id);
      setIntegrityState("ok");
    } catch (err) {
      setIntegrityState("violated");
    }
  };

  const truncatedHash = doc.integrityHash
    ? doc.integrityHash.slice(0, 32) + "…"
    : null;

  const showOcrSection = doc.ocrStatus && doc.ocrStatus !== "NOT_APPLICABLE" && doc.ocrStatus !== "PENDING";

  return (
    <div style={{
      position: "fixed", right: 0, top: 56, bottom: 0,
      width: 400, maxWidth: "100%", zIndex: 45,
      background: "#111318", borderLeft: "1px solid #2a2d35",
      boxShadow: "-18px 0 40px rgba(0,0,0,0.45)",
      padding: "18px 20px", overflowY: "auto",
      display: "flex", flexDirection: "column", gap: 18,
    }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
        <PenLine size={16} style={{ color: "#3b82f6", marginTop: 2, flexShrink: 0 }} />
        <div style={{ fontSize: 14, fontWeight: 500, color: "#e8eaf0", wordBreak: "break-all", lineHeight: 1.4, flex: 1 }}>
          {doc.filename}
        </div>
        <button
          type="button"
          title="Close panel"
          aria-label="Close panel"
          onClick={onClose}
          style={{ width: 28, height: 28, flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", background: "transparent", border: "none", borderRadius: 4, color: "#8b8fa8", cursor: "pointer" }}
        >
          <X size={16} />
        </button>
      </div>

      {/* Metadata grid */}
      <div style={{ display: "grid", gridTemplateColumns: "84px 1fr", gap: "10px 12px", fontSize: 13 }}>
        <span style={{ color: "#8b8fa8" }}>Type</span>
        <span style={{ color: "#e8eaf0" }}>{TYPE_LABEL[doc.docType] ?? doc.docType}</span>
        <span style={{ color: "#8b8fa8" }}>Size</span>
        <span style={{ color: "#e8eaf0" }}>{formatBytes(doc.fileSizeBytes)}</span>
        {doc.totalChunks != null && (
          <>
            <span style={{ color: "#8b8fa8" }}>Chunks</span>
            <span style={{ color: "#e8eaf0" }}>{doc.totalChunks}</span>
          </>
        )}
        <span style={{ color: "#8b8fa8" }}>Status</span>
        <span style={{ color: "#22c55e" }}>{doc.status}</span>
        {truncatedHash && (
          <>
            <span style={{ color: "#8b8fa8" }}>SHA-256</span>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#555869", wordBreak: "break-all" }}>{truncatedHash}</span>
          </>
        )}
      </div>

      {/* OCR Status */}
      {showOcrSection && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8, borderTop: "1px solid #2a2d35", paddingTop: 14 }}>
          <div style={{ fontSize: 11, letterSpacing: "0.06em", color: "#555869", fontFamily: "JetBrains Mono, monospace" }}>OCR STATUS</div>
          <OcrStatusRow doc={doc} />
        </div>
      )}

      {/* OCR Text */}
      {(doc.ocrFormattedText || doc.ocrRawText) && (doc.ocrStatus === "DONE" || doc.ocrStatus === "AWAITING_APPROVAL") && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8, borderTop: "1px solid #2a2d35", paddingTop: 14 }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ fontSize: 11, letterSpacing: "0.06em", color: "#555869", fontFamily: "JetBrains Mono, monospace" }}>OCR TEXT</div>
            <div style={{ display: "flex", gap: 4 }}>
              {doc.ocrFormattedText && (
                <button
                  type="button"
                  onClick={() => setOcrTab("formatted")}
                  style={{ height: 22, padding: "0 8px", fontSize: 11, background: ocrTab === "formatted" ? "#1e2028" : "transparent", border: `1px solid ${ocrTab === "formatted" ? "#3b82f6" : "#2a2d35"}`, borderRadius: 4, color: ocrTab === "formatted" ? "#3b82f6" : "#555869", cursor: "pointer" }}
                >
                  Formatted
                </button>
              )}
              {doc.ocrRawText && (
                <button
                  type="button"
                  onClick={() => setOcrTab("raw")}
                  style={{ height: 22, padding: "0 8px", fontSize: 11, background: ocrTab === "raw" ? "#1e2028" : "transparent", border: `1px solid ${ocrTab === "raw" ? "#3b82f6" : "#2a2d35"}`, borderRadius: 4, color: ocrTab === "raw" ? "#3b82f6" : "#555869", cursor: "pointer" }}
                >
                  Raw
                </button>
              )}
            </div>
          </div>
          <pre style={{
            margin: 0, maxHeight: 200, overflowY: "auto", padding: "10px 12px",
            background: "#0a0c10", border: "1px solid #2a2d35", borderRadius: 6,
            fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#8b8fa8",
            whiteSpace: "pre-wrap", wordBreak: "break-word", lineHeight: 1.6,
          }}>
            {ocrTab === "formatted" && doc.ocrFormattedText
              ? doc.ocrFormattedText
              : doc.ocrRawText ?? ""}
          </pre>
          {doc.ocrPageCount != null && (
            <div style={{ fontSize: 11, color: "#555869" }}>{doc.ocrPageCount} page{doc.ocrPageCount !== 1 ? "s" : ""} extracted</div>
          )}
        </div>
      )}

      {/* Signatures */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10, borderTop: "1px solid #2a2d35", paddingTop: 16 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span style={{ fontSize: 11, letterSpacing: "0.06em", color: "#555869", fontFamily: "JetBrains Mono, monospace" }}>
            SIGNATURES
          </span>
          <button
            type="button"
            onClick={() => void handleVerify()}
            disabled={verifying || signatures.length === 0}
            title="Re-verify all signatures cryptographically"
            style={{
              height: 26, padding: "0 10px", display: "flex", alignItems: "center", gap: 4,
              background: "#1a1d24", border: "1px solid #2a2d35", borderRadius: 4,
              color: verifying || signatures.length === 0 ? "#555869" : "#8b8fa8",
              fontSize: 12, cursor: signatures.length > 0 && !verifying ? "pointer" : "default",
            }}
          >
            <RefreshCw size={12} /> {verifying ? "Verifying…" : "Verify all"}
          </button>
        </div>

        {sigLoading && <div style={{ fontSize: 13, color: "#555869" }}>Loading signatures…</div>}
        {sigError && <div style={{ fontSize: 13, color: "#ef4444" }}>{sigError}</div>}
        {!sigLoading && signatures.length === 0 && (
          <div style={{ fontSize: 13, color: "#555869" }}>Not signed yet.</div>
        )}

        {signatures.map(sig => (
          <div key={sig.id} style={{ background: "#1a1d24", borderRadius: 6, padding: "10px 12px", display: "flex", flexDirection: "column", gap: 6 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
              <BadgeCheck
                size={14}
                style={{ color: sig.revoked_at ? "#555869" : sig.is_valid === true ? "#22c55e" : sig.is_valid === false ? "#ef4444" : "#8b8fa8", flexShrink: 0 }}
              />
              <span style={{ fontSize: 13, color: "#e8eaf0", flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {sig.signer.full_name ?? sig.signer.email}
              </span>
              <span style={{ fontSize: 10, letterSpacing: "0.05em", padding: "2px 6px", borderRadius: 4, color: ROLE_COLOR[sig.signer.role] ?? "#8b8fa8", background: "#0a0c10", flexShrink: 0 }}>
                {ROLE_LABEL[sig.signer.role] ?? sig.signer.role}
              </span>
              <SigStatusBadge sig={sig} />
            </div>

            <div style={{ fontSize: 11, color: "#555869" }}>
              Signed {formatDateTime(sig.signed_at)}
              {sig.last_verified_at && ` · verified ${formatDateTime(sig.last_verified_at)}`}
            </div>

            {sig.comment && (
              <div style={{ fontSize: 12, color: "#8b8fa8", fontStyle: "italic", borderTop: "1px solid #2a2d35", paddingTop: 6 }}>
                "{sig.comment}"
              </div>
            )}

            {!sig.revoked_at && (sig.signer.id === currentUser?.id || currentUser?.role === "SUPER_ADMIN") && (
              <button
                type="button"
                onClick={() => void handleRevoke(sig.id)}
                style={{ alignSelf: "flex-start", height: 24, padding: "0 8px", background: "transparent", border: "1px solid #2a2d35", borderRadius: 4, color: "#555869", fontSize: 11, cursor: "pointer" }}
              >
                Revoke
              </button>
            )}
          </div>
        ))}

        {/* Sign form / trigger */}
        {canSign && (
          alreadySigned ? (
            <div style={{ fontSize: 12, color: "#22c55e", display: "flex", alignItems: "center", gap: 6 }}>
              <BadgeCheck size={14} /> You have signed this document
            </div>
          ) : showSignForm ? (
            <div style={{ background: "#1a1d24", border: "1px solid #2a2d35", borderRadius: 6, padding: 12 }}>
              <div style={{ fontSize: 12, color: "#8b8fa8", marginBottom: 8 }}>
                Comment <span style={{ color: "#555869" }}>(optional · max 500 chars)</span>
              </div>
              <textarea
                value={comment}
                onChange={e => setComment(e.target.value)}
                maxLength={500}
                placeholder="e.g. Reviewed and confirmed evidence chain"
                style={{ width: "100%", height: 72, padding: "8px 10px", background: "#1e2028", border: "1px solid #2a2d35", borderRadius: 4, color: "#e8eaf0", fontSize: 13, resize: "none", boxSizing: "border-box", outline: "none" }}
              />
              {signError && <div style={{ fontSize: 12, color: "#ef4444", marginTop: 6 }}>{signError}</div>}
              <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
                <button
                  type="button"
                  onClick={() => void handleSign()}
                  disabled={signing}
                  style={{ height: 32, padding: "0 14px", background: "#3b82f6", color: "#fff", border: "none", borderRadius: 4, fontSize: 13, fontWeight: 500, cursor: signing ? "default" : "pointer" }}
                >
                  {signing ? "Signing…" : "Confirm Sign"}
                </button>
                <button
                  type="button"
                  onClick={() => { setShowSignForm(false); setComment(""); setSignError(null); }}
                  style={{ height: 32, padding: "0 12px", background: "transparent", border: "1px solid #2a2d35", borderRadius: 4, color: "#8b8fa8", fontSize: 13, cursor: "pointer" }}
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setShowSignForm(true)}
              style={{ alignSelf: "flex-start", height: 32, padding: "0 12px", display: "flex", alignItems: "center", gap: 6, background: "#1a1d24", border: "1px solid #3b82f6", borderRadius: 4, color: "#3b82f6", fontSize: 13, cursor: "pointer" }}
            >
              <PenLine size={14} /> Sign this document
            </button>
          )
        )}
      </div>

      {/* Tags */}
      {doc.tags.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8, borderTop: "1px solid #2a2d35", paddingTop: 16 }}>
          <div style={{ fontSize: 11, letterSpacing: "0.06em", color: "#555869", fontFamily: "JetBrains Mono, monospace" }}>TAGS</div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {doc.tags.map((t, i) => (
              <span key={i} style={{ fontSize: 11, padding: "3px 8px", borderRadius: 6, background: "#1e2028", border: "1px solid #2a2d35", color: "#8b8fa8" }}>{t}</span>
            ))}
          </div>
        </div>
      )}

      {/* Uploaded by + date */}
      <div style={{ display: "grid", gridTemplateColumns: "84px 1fr", gap: "10px 12px", fontSize: 13, borderTop: "1px solid #2a2d35", paddingTop: 16 }}>
        {doc.uploadedByName && (
          <>
            <span style={{ color: "#8b8fa8" }}>Uploaded by</span>
            <span style={{ color: "#e8eaf0", fontWeight: 500 }}>{doc.uploadedByName}</span>
          </>
        )}
        <span style={{ color: "#8b8fa8" }}>Uploaded</span>
        <span style={{ color: "#8b8fa8" }}>{formatDate(doc.createdAt)}</span>
      </div>

      {/* Action buttons */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: "auto", paddingTop: 16, borderTop: "1px solid #2a2d35" }}>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            type="button"
            onClick={() => void handleDownload()}
            style={{ flex: 1, height: 34, display: "flex", alignItems: "center", justifyContent: "center", gap: 6, background: "#3b82f6", color: "#fff", border: "none", borderRadius: 4, fontSize: 13, fontWeight: 500, cursor: "pointer" }}
          >
            <Download size={14} /> Download
          </button>
          {canSign && !alreadySigned && (
            <button
              type="button"
              onClick={() => setShowSignForm(v => !v)}
              style={{ height: 34, padding: "0 12px", display: "flex", alignItems: "center", gap: 6, background: "#1a1d24", border: "1px solid #2a2d35", borderRadius: 4, color: "#e8eaf0", fontSize: 13, cursor: "pointer" }}
            >
              <PenLine size={14} /> Sign
            </button>
          )}
          <button
            type="button"
            style={{ height: 34, padding: "0 12px", display: "flex", alignItems: "center", gap: 6, background: "#1a1d24", border: "1px solid #2a2d35", borderRadius: 4, color: "#e8eaf0", fontSize: 13, cursor: "pointer" }}
          >
            <Share2 size={14} /> Share
          </button>
        </div>

        {/* Download error banner */}
        {downloadError && (
          <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 10px", background: "#3d1010", border: "1px solid #7f1d1d", borderRadius: 4, fontSize: 12, color: "#ef4444" }}>
            <XCircle size={14} style={{ flexShrink: 0 }} />
            {downloadError}
          </div>
        )}

        {/* Integrity check button + result */}
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <button
            type="button"
            onClick={() => void handleCheckIntegrity()}
            disabled={integrityState === "checking"}
            style={{
              height: 28, padding: "0 10px", display: "flex", alignItems: "center", gap: 5,
              background: "#1a1d24", border: `1px solid ${integrityState === "ok" ? "#22c55e" : integrityState === "violated" ? "#ef4444" : "#2a2d35"}`,
              borderRadius: 4, fontSize: 12,
              color: integrityState === "ok" ? "#22c55e" : integrityState === "violated" ? "#ef4444" : "#8b8fa8",
              cursor: integrityState === "checking" ? "default" : "pointer",
            }}
          >
            {integrityState === "ok"
              ? <><ShieldCheck size={13} /> Integrity OK</>
              : integrityState === "violated"
              ? <><ShieldAlert size={13} /> Integrity FAILED</>
              : integrityState === "checking"
              ? <><Shield size={13} /> Checking…</>
              : <><Shield size={13} /> Check Integrity</>
            }
          </button>
        </div>
      </div>
    </div>
  );
}
