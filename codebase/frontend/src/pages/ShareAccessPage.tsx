/**
 * ShareAccessPage — public page at /share/:token for external recipients.
 *
 * Three views driven by share scope:
 *   DOCUMENT       — enter email → download or preview (view-only) file
 *   CASE_DOCUMENTS — enter email → see list of docs → download or preview each
 *   CASE_FULL      — enter email → see case overview + members + docs → download or preview each
 *
 * allow_download=false hides/disables download; recipients can only preview via the
 * server-side PNG/text renderer. OCR formatted text rendered as markdown.
 * Preview supports fullscreen mode.
 *
 * Matches design/screens/ShareAccessPage.jsx (colours, spacing, structure).
 * No auth, no AppShell — fully self-contained.
 */

import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import {
  Briefcase,
  CheckCircle2,
  Clock,
  Download,
  Expand,
  Eye,
  FileText,
  Shield,
  ShieldX,
  Shrink,
  Users,
  X,
} from "lucide-react";
import {
  getShareInfo,
  downloadShareDocument,
  accessCaseDocuments,
  accessCaseFull,
  downloadShareFile,
  previewShareDocument,
  previewShareFile,
} from "../lib/shareApi";
import type { SharePreview } from "../lib/shareApi";
import type { ShareInfo, SharedCaseDetail, SharedDocMeta } from "../types";

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

function fmtExpiry(iso: string): string {
  try {
    const diff = new Date(iso).getTime() - Date.now();
    if (diff <= 0) return "Expired";
    const hours = Math.floor(diff / 3_600_000);
    const mins = Math.floor((diff % 3_600_000) / 60_000);
    if (hours > 0) return `Expires in ${hours}h ${mins}m`;
    return `Expires in ${mins} minutes`;
  } catch {
    return "";
  }
}

function triggerBlobDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 1000);
}

const OCR_LABEL: Record<string, string> = {
  NOT_APPLICABLE: "—",
  PENDING: "Processing",
  AWAITING_APPROVAL: "Pending review",
  DONE: "Verified",
  FAILED: "OCR failed",
};

const OCR_COLOR: Record<string, string> = {
  NOT_APPLICABLE: "#555869",
  PENDING: "#555869",
  AWAITING_APPROVAL: "#f59e0b",
  DONE: "#22c55e",
  FAILED: "#ef4444",
};

// ── Preview overlay ───────────────────────────────────────────────────────────────

interface PreviewOverlayProps {
  preview: SharePreview;
  filename: string;
  onClose: () => void;
}

function PreviewOverlay({ preview, filename, onClose }: PreviewOverlayProps) {
  const [fullscreen, setFullscreen] = useState(false);

  const containerStyle: React.CSSProperties = fullscreen
    ? { position: "fixed", inset: 0, zIndex: 200, background: "#0a0c10", overflowY: "auto", padding: "24px" }
    : { position: "fixed", inset: 0, zIndex: 200, background: "rgba(0,0,0,0.75)", display: "flex", alignItems: "flex-start", justifyContent: "center", padding: "32px 16px", overflowY: "auto" };

  const cardStyle: React.CSSProperties = fullscreen
    ? { maxWidth: 900, margin: "0 auto" }
    : { width: "720px", maxWidth: "100%", background: "#111318", border: "1px solid #2a2d35", borderRadius: "8px", overflow: "hidden" };

  return (
    <div style={containerStyle} onClick={fullscreen ? undefined : onClose}>
      <div style={cardStyle} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", padding: "14px 16px", borderBottom: "1px solid #2a2d35", background: "#1a1d24" }}>
          <FileText size={16} style={{ color: "#3b82f6", flexShrink: 0 }} />
          <span style={{ fontSize: "13px", color: "#e8eaf0", fontWeight: 500, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {filename}
          </span>
          <button
            type="button"
            title={fullscreen ? "Exit fullscreen" : "Fullscreen"}
            onClick={() => setFullscreen(v => !v)}
            style={{ height: 28, width: 28, display: "flex", alignItems: "center", justifyContent: "center", background: "transparent", border: "none", borderRadius: 4, color: "#8b8fa8", cursor: "pointer" }}
          >
            {fullscreen ? <Shrink size={14} /> : <Expand size={14} />}
          </button>
          <button
            type="button"
            title="Close preview"
            onClick={onClose}
            style={{ height: 28, width: 28, display: "flex", alignItems: "center", justifyContent: "center", background: "transparent", border: "none", borderRadius: 4, color: "#8b8fa8", cursor: "pointer" }}
          >
            <X size={14} />
          </button>
        </div>

        {/* Body */}
        <div style={{ padding: "16px" }}>
          {preview.mode === "text" && preview.text != null && (
            <div style={{ padding: "14px 18px", background: "#0a0c10", border: "1px solid #2a2d35", borderRadius: 6, fontSize: 13, color: "#e8eaf0", lineHeight: 1.75 }}>
              <ReactMarkdown>{preview.text}</ReactMarkdown>
            </div>
          )}

          {preview.mode === "pages" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {preview.pages_png_base64.map((b64, i) => (
                <img
                  key={i}
                  alt={`Page ${i + 1}`}
                  src={`data:image/png;base64,${b64}`}
                  style={{ width: "100%", borderRadius: 6, border: "1px solid #2a2d35", display: "block" }}
                />
              ))}
            </div>
          )}

          {preview.truncated && (
            <div style={{ marginTop: 10, fontSize: 11, color: "#555869" }}>
              Preview truncated — {preview.page_count} page{preview.page_count !== 1 ? "s" : ""} shown
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Root component ────────────────────────────────────────────────────────────────

export default function ShareAccessPage() {
  const { token } = useParams<{ token: string }>();
  const [info, setInfo] = useState<ShareInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [accessed, setAccessed] = useState(false);
  const [docList, setDocList] = useState<SharedDocMeta[]>([]);
  const [caseDetail, setCaseDetail] = useState<SharedCaseDetail | null>(null);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  // Preview state
  const [previewData, setPreviewData] = useState<SharePreview | null>(null);
  const [previewFilename, setPreviewFilename] = useState("");
  const [previewingId, setPreviewingId] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    void getShareInfo(token).then((i) => {
      setInfo(i);
      setLoading(false);
    }).catch(() => {
      setInfo({ scope: "DOCUMENT", filename: null, caseTitle: null, caseNumber: null, docCount: null, fileSizeBytes: null, expiresAt: "", requiresEmail: true, isValid: false, allowDownload: true });
      setLoading(false);
    });
  }, [token]);

  async function handleAccess() {
    if (!token || !info) return;
    setError("");

    if (info.scope === "DOCUMENT") {
      if (!info.allowDownload) {
        // View-only: open preview instead of downloading
        await handleDocumentPreview();
        return;
      }
      try {
        const blob = await downloadShareDocument(token, email);
        triggerBlobDownload(blob, info.filename ?? "document");
        setDone(true);
      } catch (err) {
        if (err instanceof Error && err.message === "EMAIL_MISMATCH") {
          setError("The email you entered does not match the link restriction.");
        } else if (err instanceof Error && err.message === "LINK_EXPIRED") {
          setInfo({ ...info, isValid: false });
        } else {
          setError("Download failed. Please try again.");
        }
      }
      return;
    }

    if (info.scope === "CASE_DOCUMENTS") {
      try {
        const { documents } = await accessCaseDocuments(token, email);
        setDocList(documents);
        setAccessed(true);
      } catch (err) {
        if (err instanceof Error && err.message === "EMAIL_MISMATCH") {
          setError("The email you entered does not match the link restriction.");
        } else if (err instanceof Error && err.message === "LINK_EXPIRED") {
          setInfo({ ...info, isValid: false });
        } else {
          setError("Access failed. Please try again.");
        }
      }
      return;
    }

    // CASE_FULL
    try {
      const result = await accessCaseFull(token, email);
      setCaseDetail(result.case);
      setDocList(result.documents);
      setAccessed(true);
    } catch (err) {
      if (err instanceof Error && err.message === "EMAIL_MISMATCH") {
        setError("The email you entered does not match the link restriction.");
      } else if (err instanceof Error && err.message === "LINK_EXPIRED") {
        setInfo({ ...info, isValid: false });
      } else {
        setError("Access failed. Please try again.");
      }
    }
  }

  async function handleDocumentPreview() {
    if (!token || !info) return;
    setError("");
    setPreviewingId("__doc__");
    try {
      const data = await previewShareDocument(token, email || null);
      setPreviewFilename(info.filename ?? "Document");
      setPreviewData(data);
    } catch (err) {
      if (err instanceof Error && err.message === "EMAIL_MISMATCH") {
        setError("The email you entered does not match the link restriction.");
      } else if (err instanceof Error && err.message === "LINK_EXPIRED") {
        if (info) setInfo({ ...info, isValid: false });
      } else {
        setError("Preview failed. Please try again.");
      }
    } finally {
      setPreviewingId(null);
    }
  }

  async function handleFileDownload(doc: SharedDocMeta) {
    if (!token) return;
    setDownloadingId(doc.id);
    setError("");
    try {
      const { blob, filename } = await downloadShareFile(token, doc.id, email);
      triggerBlobDownload(blob, filename);
    } catch (err) {
      if (err instanceof Error && err.message === "LINK_EXPIRED") {
        setError("The share link has expired.");
      } else {
        setError(`Download failed for ${doc.filename}.`);
      }
    } finally {
      setDownloadingId(null);
    }
  }

  async function handleFilePreview(doc: SharedDocMeta) {
    if (!token) return;
    setPreviewingId(doc.id);
    setError("");
    try {
      const data = await previewShareFile(token, doc.id, email || null);
      setPreviewFilename(doc.filename);
      setPreviewData(data);
    } catch (err) {
      if (err instanceof Error && err.message === "LINK_EXPIRED") {
        setError("The share link has expired.");
      } else {
        setError(`Preview failed for ${doc.filename}.`);
      }
    } finally {
      setPreviewingId(null);
    }
  }

  // ── Loading ───────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <PageShell>
        <div style={{ color: "#8b8fa8", fontSize: "14px" }}>Loading…</div>
      </PageShell>
    );
  }

  // ── Dead / expired ────────────────────────────────────────────────────────────

  if (!info || !info.isValid) {
    return (
      <PageShell>
        <div style={{
          width: "420px", maxWidth: "100%",
          background: "#111318", border: "1px solid #2a2d35", borderRadius: "8px",
          padding: "28px 24px", display: "flex", flexDirection: "column",
          alignItems: "center", gap: "12px", textAlign: "center",
        }}>
          <div style={{ color: "#ef4444" }}><ShieldX size={36} /></div>
          <div style={{ fontSize: "17px", fontWeight: 600, color: "#e8eaf0" }}>
            This link is no longer valid.
          </div>
          <div style={{ fontSize: "13px", color: "#8b8fa8", lineHeight: 1.6, maxWidth: "300px" }}>
            It may have expired, been revoked, or reached its maximum number of uses.
          </div>
          <div style={{ fontSize: "13px", color: "#8b8fa8" }}>
            Contact the issuing officer for a new link.
          </div>
        </div>
      </PageShell>
    );
  }

  const allowDownload = info.allowDownload;

  // ── Case accessed view ────────────────────────────────────────────────────────

  if (accessed) {
    return (
      <PageShell>
        {previewData && (
          <PreviewOverlay
            preview={previewData}
            filename={previewFilename}
            onClose={() => setPreviewData(null)}
          />
        )}
        <div style={{
          width: "680px", maxWidth: "100%",
          background: "#111318", border: "1px solid #2a2d35", borderRadius: "8px",
          padding: "24px", display: "flex", flexDirection: "column", gap: "20px",
        }}>
          {/* Case detail (CASE_FULL only) */}
          {caseDetail && (
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
                <div style={{ color: "#3b82f6", marginTop: "2px" }}><Briefcase size={20} /></div>
                <div>
                  <div style={{ fontSize: "16px", fontWeight: 600, color: "#e8eaf0" }}>{caseDetail.title}</div>
                  <div style={{ fontSize: "12px", color: "#8b8fa8", fontFamily: "'JetBrains Mono', monospace", marginTop: "2px" }}>{caseDetail.caseNumber}</div>
                  {caseDetail.description && (
                    <div style={{ fontSize: "13px", color: "#8b8fa8", marginTop: "8px", lineHeight: 1.5 }}>{caseDetail.description}</div>
                  )}
                  <div style={{ display: "flex", gap: "12px", marginTop: "8px", flexWrap: "wrap" }}>
                    <span style={{ fontSize: "12px", color: "#8b8fa8" }}>Status: <span style={{ color: "#e8eaf0" }}>{caseDetail.status}</span></span>
                    <span style={{ fontSize: "12px", color: "#8b8fa8" }}>Priority: <span style={{ color: "#e8eaf0" }}>{caseDetail.priority}</span></span>
                  </div>
                </div>
              </div>

              {/* Members */}
              <div style={{ background: "#1a1d24", border: "1px solid #2a2d35", borderRadius: "6px", padding: "12px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px" }}>
                  <Users size={14} style={{ color: "#8b8fa8" }} />
                  <span style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>Case Members ({caseDetail.memberCount})</span>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  {caseDetail.members.map((m, i) => (
                    <div key={i} style={{ display: "flex", justifyContent: "space-between", fontSize: "13px" }}>
                      <span style={{ color: "#e8eaf0" }}>{m.fullName}</span>
                      <span style={{ color: "#8b8fa8" }}>{m.role}{m.department ? ` · ${m.department}` : ""}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Document list */}
          <div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
              <div style={{ fontSize: "14px", fontWeight: 600, color: "#e8eaf0" }}>
                Documents ({docList.length})
              </div>
              {!allowDownload && (
                <span style={{ fontSize: "11px", color: "#f59e0b", padding: "2px 8px", background: "#3d2c08", border: "1px solid #f59e0b", borderRadius: 4 }}>
                  View only — download disabled
                </span>
              )}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {docList.map((doc) => (
                <div key={doc.id} style={{ display: "flex", flexDirection: "column", gap: 0 }}>
                  <div style={{
                    background: "#1a1d24", border: "1px solid #2a2d35", borderRadius: "6px",
                    padding: "12px", display: "flex", alignItems: "center", gap: "12px",
                  }}>
                    <FileText size={16} style={{ color: "#3b82f6", flexShrink: 0 }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0", wordBreak: "break-all" }}>{doc.filename}</div>
                      <div style={{ display: "flex", gap: "10px", marginTop: "4px", flexWrap: "wrap" }}>
                        <span style={{ fontSize: "11px", color: "#8b8fa8" }}>{doc.docType.replace(/_/g, " ")}</span>
                        <span style={{ fontSize: "11px", color: "#8b8fa8" }}>{fmtSize(doc.fileSizeBytes)}</span>
                        {doc.ocrStatus !== "NOT_APPLICABLE" && (
                          <span style={{ fontSize: "11px", color: OCR_COLOR[doc.ocrStatus] ?? "#555869" }}>
                            OCR: {OCR_LABEL[doc.ocrStatus] ?? doc.ocrStatus}
                            {doc.ocrStatus === "DONE" && doc.ocrConfidence != null ? ` (${Math.round(doc.ocrConfidence * 100)}%)` : ""}
                          </span>
                        )}
                      </div>
                    </div>
                    <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                      <button
                        type="button"
                        onClick={() => void handleFilePreview(doc)}
                        disabled={previewingId === doc.id}
                        style={{
                          height: "30px", padding: "0 10px",
                          display: "flex", alignItems: "center", gap: "5px",
                          background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "4px",
                          color: "#8b8fa8", fontSize: "12px", cursor: previewingId === doc.id ? "not-allowed" : "pointer",
                        }}
                      >
                        <Eye size={12} />
                        {previewingId === doc.id ? "…" : "View"}
                      </button>
                      {allowDownload && (
                        <button
                          type="button"
                          onClick={() => void handleFileDownload(doc)}
                          disabled={downloadingId === doc.id}
                          style={{
                            height: "30px", padding: "0 10px",
                            display: "flex", alignItems: "center", gap: "5px",
                            background: downloadingId === doc.id ? "#1e3a5f" : "#3b82f6",
                            color: "#fff", border: "none", borderRadius: "4px",
                            fontSize: "12px", cursor: downloadingId === doc.id ? "not-allowed" : "pointer",
                          }}
                        >
                          <Download size={12} />
                          {downloadingId === doc.id ? "…" : "Download"}
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Inline OCR formatted text (markdown) */}
                  {doc.ocrStatus === "DONE" && doc.ocrFormattedText && (
                    <div style={{
                      marginTop: 4, padding: "12px 16px",
                      background: "#0a0c10", border: "1px solid #2a2d35",
                      borderTop: "none", borderRadius: "0 0 6px 6px",
                      fontSize: 12, color: "#e8eaf0", lineHeight: 1.75,
                    }}>
                      <div style={{ fontSize: 10, letterSpacing: "0.06em", color: "#555869", fontFamily: "JetBrains Mono, monospace", marginBottom: 8 }}>
                        OCR TEXT (FORMATTED)
                      </div>
                      <ReactMarkdown>{doc.ocrFormattedText}</ReactMarkdown>
                    </div>
                  )}
                </div>
              ))}
              {docList.length === 0 && (
                <div style={{ fontSize: "13px", color: "#555869", padding: "12px 0" }}>No documents in this case.</div>
              )}
            </div>
          </div>

          {error && (
            <div style={{ background: "#3d1010", border: "1px solid #ef4444", borderRadius: "6px", padding: "9px 11px", fontSize: "12px", color: "#ef4444" }}>
              {error}
            </div>
          )}

          <footer style={{ fontSize: "11px", color: "#555869", textAlign: "center", display: "flex", alignItems: "center", justifyContent: "center", gap: "6px" }}>
            <Shield size={12} /> All access is logged and audited.
          </footer>
        </div>
      </PageShell>
    );
  }

  // ── Initial access form ───────────────────────────────────────────────────────

  const isDocScope = info.scope === "DOCUMENT";
  const viewOnly = isDocScope && !allowDownload;

  return (
    <PageShell>
      {previewData && (
        <PreviewOverlay
          preview={previewData}
          filename={previewFilename}
          onClose={() => setPreviewData(null)}
        />
      )}
      <div style={{
        width: "420px", maxWidth: "100%",
        background: "#111318", border: "1px solid #2a2d35", borderRadius: "8px",
        padding: "24px", display: "flex", flexDirection: "column", gap: "18px",
      }}>
        {/* Document / case header */}
        <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
          <div style={{ color: "#3b82f6", marginTop: "2px" }}>
            {isDocScope ? <FileText size={20} /> : <Briefcase size={20} />}
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "4px", minWidth: 0 }}>
            {isDocScope ? (
              <>
                <div style={{ fontSize: "15px", fontWeight: 600, color: "#e8eaf0", wordBreak: "break-all" }}>
                  {info.filename ?? "Document"}
                </div>
                <div style={{ fontSize: "12px", color: "#8b8fa8" }}>
                  {info.fileSizeBytes != null ? fmtSize(info.fileSizeBytes) : ""}
                </div>
                {viewOnly && (
                  <div style={{ fontSize: "11px", color: "#f59e0b", padding: "2px 6px", background: "#3d2c08", border: "1px solid #f59e0b", borderRadius: 4, alignSelf: "flex-start", marginTop: 2 }}>
                    View only — download disabled
                  </div>
                )}
              </>
            ) : (
              <>
                <div style={{ fontSize: "15px", fontWeight: 600, color: "#e8eaf0" }}>
                  {info.caseTitle ?? "Case"}
                </div>
                <div style={{ fontSize: "12px", color: "#8b8fa8", fontFamily: "'JetBrains Mono', monospace" }}>
                  {info.caseNumber ?? ""}
                </div>
                <div style={{ fontSize: "12px", color: "#8b8fa8", marginTop: "2px" }}>
                  {info.scope === "CASE_FULL" ? "Full case view" : "All case documents"} · {info.docCount ?? 0} document{info.docCount !== 1 ? "s" : ""}
                </div>
                {!allowDownload && (
                  <div style={{ fontSize: "11px", color: "#f59e0b", padding: "2px 6px", background: "#3d2c08", border: "1px solid #f59e0b", borderRadius: 4, alignSelf: "flex-start", marginTop: 2 }}>
                    View only — download disabled
                  </div>
                )}
              </>
            )}
            {info.expiresAt && (
              <div style={{ fontSize: "12px", color: "#f59e0b", display: "flex", alignItems: "center", gap: "6px", marginTop: "2px" }}>
                <Clock size={14} /> {fmtExpiry(info.expiresAt)}
              </div>
            )}
          </div>
        </div>

        {/* Email restriction banner */}
        {info.requiresEmail && (
          <div style={{
            background: "#1a1d24", border: "1px solid #2a2d35",
            borderRadius: "6px", padding: "12px",
          }}>
            <div style={{ fontSize: "12px", color: "#8b8fa8", marginBottom: "4px" }}>This link is restricted to a named recipient.</div>
            <div style={{ fontSize: "12px", color: "#8b8fa8" }}>Enter your email to verify access.</div>
          </div>
        )}

        {/* Email field */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <label htmlFor="sh-email" style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>
            Email <span style={{ color: "#8b8fa8", fontWeight: 400 }}>(required)</span>
          </label>
          <input
            id="sh-email"
            type="email"
            placeholder="Enter your email to continue"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={{
              height: "36px", padding: "0 10px", fontSize: "14px",
              color: "#e8eaf0", background: "#1e2028",
              border: "1px solid #2a2d35", borderRadius: "6px",
            }}
          />
        </div>

        {/* Error */}
        {error && (
          <div style={{ background: "#3d1010", border: "1px solid #ef4444", borderRadius: "6px", padding: "9px 11px", fontSize: "12px", color: "#ef4444" }}>
            {error}
          </div>
        )}

        {/* Action button */}
        <button
          type="button"
          onClick={() => void handleAccess()}
          disabled={previewingId === "__doc__"}
          style={{
            height: "34px", display: "flex", alignItems: "center", justifyContent: "center",
            gap: "8px", background: "#3b82f6", color: "#ffffff",
            border: "none", borderRadius: "4px", fontSize: "14px", fontWeight: 500,
            cursor: previewingId === "__doc__" ? "not-allowed" : "pointer",
          }}
        >
          {isDocScope
            ? viewOnly
              ? <><Eye size={16} /> {previewingId === "__doc__" ? "Loading preview…" : "View Document"}</>
              : <><Download size={16} /> Download Document</>
            : <><Briefcase size={16} /> Access {info.scope === "CASE_FULL" ? "Full Case" : "Documents"}</>}
        </button>

        {/* Success banner (document scope download) */}
        {done && (
          <div style={{
            display: "flex", gap: "8px", alignItems: "center",
            background: "#14391f", border: "1px solid #22c55e",
            borderRadius: "6px", padding: "10px 12px",
            fontSize: "13px", color: "#e8eaf0",
          }}>
            <CheckCircle2 size={16} /> Download started. This access has been logged.
          </div>
        )}

        <footer style={{ fontSize: "11px", color: "#555869", textAlign: "center", display: "flex", alignItems: "center", justifyContent: "center", gap: "6px" }}>
          <Shield size={14} /> Accessed links are logged.
        </footer>
      </div>
    </PageShell>
  );
}

// ── Layout shell ──────────────────────────────────────────────────────────────────

function PageShell({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      minHeight: "100vh", display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
      gap: "28px", padding: "48px 24px",
      background: "#0a0c10", color: "#e8eaf0",
    }}>
      {/* Logo */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "10px" }}>
        <div style={{ color: "#3b82f6" }}><Shield size={36} /></div>
        <div style={{ fontSize: "24px", fontWeight: 700, letterSpacing: "0.18em", color: "#e8eaf0" }}>PRAMAAN</div>
        <div style={{ fontSize: "13px", color: "#8b8fa8" }}>Secure Evidence Vault</div>
      </div>
      {children}
    </div>
  );
}
