/**
 * PersonalVaultPage — /my-documents
 * Encrypted personal document store for the logged-in user.
 * Uploads go to POST /api/v1/me/documents; listing from GET /api/v1/me/documents.
 * No case association — access is owner-only (enforced server-side).
 */

import { useEffect, useState } from "react";
import {
  AlertCircle,
  ArrowUpDown,
  CheckCircle2,
  Download,
  FileText,
  Loader2,
  MoreVertical,
  Plus,
  Search,
  Share2,
  Trash2,
  XCircle,
} from "lucide-react";

import DocumentUploader from "../components/DocumentUploader";
import OcrApprovalModal from "../components/OcrApprovalModal";
import ShareModal from "../components/ShareModal";
import StepUpMfaModal from "../components/StepUpMfaModal";
import {
  deleteDocument,
  downloadDocument,
  fetchPersonalDocs,
  generateOcr,
} from "../lib/documentApi";
import type { DocumentMeta } from "../types";

// ── Helpers ───────────────────────────────────────────────────────────────────

const OCR_EXT_SET = new Set([".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif"]);

function isOcrExt(filename: string): boolean {
  const dot = filename.lastIndexOf(".");
  return dot >= 0 && OCR_EXT_SET.has(filename.slice(dot).toLowerCase());
}

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

function fileIconColor(filename: string): string {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "";
  if (["pdf", "doc", "docx"].includes(ext)) return "#3b82f6";
  if (["jpg", "jpeg", "png", "tiff", "tif", "gif"].includes(ext)) return "#f59e0b";
  if (["xlsx", "xls", "csv"].includes(ext)) return "#22c55e";
  return "#555869";
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-IN", {
      day: "numeric", month: "short", year: "numeric",
    });
  } catch { return iso; }
}

function OcrChip({ doc, isGenerating }: { doc: Pick<DocumentMeta, "ocrStatus" | "ocrConfidence">; isGenerating?: boolean }) {
  const { ocrStatus, ocrConfidence } = doc;
  const pct = ocrConfidence != null ? Math.round(ocrConfidence * 100) : null;
  if (isGenerating || ocrStatus === "PENDING") return (
    <span style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12, color: "#555869" }}>
      <Loader2 size={12} style={{ animation: "spin 0.9s linear infinite" }} /> Processing…
    </span>
  );
  if (!ocrStatus || ocrStatus === "NOT_APPLICABLE") return <span style={{ color: "#555869" }}>—</span>;
  if (ocrStatus === "DONE") return (
    <span style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12, color: "#22c55e" }}>
      <CheckCircle2 size={12} /> Verified{pct != null ? ` (${pct}%)` : ""}
    </span>
  );
  if (ocrStatus === "AWAITING_APPROVAL") {
    const isLow = ocrConfidence != null && ocrConfidence < 0.65;
    return (
      <span style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12, color: isLow ? "#fb923c" : "#f59e0b" }}>
        <AlertCircle size={12} /> {isLow && pct != null ? `Low confidence (${pct}%)` : "Pending review"}
      </span>
    );
  }
  if (ocrStatus === "FAILED") return (
    <span style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12, color: "#ef4444" }}>
      <XCircle size={12} /> OCR failed
    </span>
  );
  return <span style={{ color: "#555869" }}>—</span>;
}

const DOC_TYPE_OPTIONS = [
  { value: "All", label: "Type — all" },
  { value: "FIR", label: "FIR" },
  { value: "EVIDENCE_RECORD", label: "Evidence record" },
  { value: "FORENSIC_REPORT", label: "Forensic report" },
  { value: "WITNESS_STATEMENT", label: "Witness statement" },
  { value: "INVESTIGATION_RECORD", label: "Investigation record" },
  { value: "CHARGE_SHEET", label: "Charge sheet" },
  { value: "COURT_FILING", label: "Court filing" },
  { value: "POLICE_REPORT", label: "Police report" },
  { value: "LEGAL_NOTICE", label: "Legal notice" },
  { value: "JUDGMENT", label: "Judgment" },
  { value: "OTHER", label: "Other" },
];

// ── Page ──────────────────────────────────────────────────────────────────────

export default function PersonalVaultPage() {
  const [docs, setDocs] = useState<DocumentMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [ocrDoc, setOcrDoc] = useState<DocumentMeta | null>(null);
  const [ocrGenerating, setOcrGenerating] = useState<string | null>(null);
  const [menuDocId, setMenuDocId] = useState<string | null>(null);
  const [pendingDeleteDoc, setPendingDeleteDoc] = useState<DocumentMeta | null>(null);
  const [deleteOtp, setDeleteOtp] = useState("");
  const [deleteOtpError, setDeleteOtpError] = useState("");
  const [docSearch, setDocSearch] = useState("");
  const [docTypeFilter, setDocTypeFilter] = useState("All");
  const [sortField, setSortField] = useState<"name" | "size" | "date">("date");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [showUploadPanel, setShowUploadPanel] = useState(false);
  const [shareDocTarget, setShareDocTarget] = useState<DocumentMeta | null>(null);

  useEffect(() => {
    fetchPersonalDocs()
      .then(setDocs)
      .catch(() => {})
      .finally(() => setLoading(false));
    // Run once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function updateDoc(updated: DocumentMeta) {
    setDocs((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
  }

  async function handleGenerateOcr(doc: DocumentMeta, force = false) {
    setOcrGenerating(doc.id);
    try {
      const updated = await generateOcr(doc.id, force);
      updateDoc(updated);
      if (updated.ocrStatus === "AWAITING_APPROVAL") setOcrDoc(updated);
    } catch {
      /* non-fatal */
    } finally {
      setOcrGenerating(null);
    }
  }

  async function handleDeleteDoc(doc: DocumentMeta, totpCode: string) {
    setDeleteOtpError("");
    try {
      await deleteDocument(doc.id, totpCode);
      setDocs((prev) => prev.filter((d) => d.id !== doc.id));
      setPendingDeleteDoc(null);
      setDeleteOtp("");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      if (msg.toLowerCase().includes("invalid") || msg.toLowerCase().includes("unauthorized")) {
        setDeleteOtpError("Invalid TOTP code — try again.");
      } else {
        setDeleteOtpError(msg);
      }
    }
  }

  function toggleSort(field: "name" | "size" | "date") {
    if (sortField === field) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortField(field); setSortDir("asc"); }
  }

  const filteredSortedDocs = docs
    .filter((d) => {
      const q = docSearch.toLowerCase();
      return (
        (q === "" || d.filename.toLowerCase().includes(q)) &&
        (docTypeFilter === "All" || d.docType === docTypeFilter)
      );
    })
    .sort((a, b) => {
      let cmp = 0;
      if (sortField === "name") cmp = a.filename.localeCompare(b.filename);
      else if (sortField === "size") cmp = a.fileSizeBytes - b.fileSizeBytes;
      else cmp = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
      return sortDir === "asc" ? cmp : -cmp;
    });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
      {/* Page header */}
      <div>
        <h1
          style={{
            margin: 0,
            fontSize: "22px",
            fontWeight: 600,
            color: "#e8eaf0",
            letterSpacing: "-0.01em",
          }}
        >
          My Vault
        </h1>
        <p style={{ margin: "6px 0 0", fontSize: "13px", color: "#8b8fa8" }}>
          Personal encrypted documents — only you can see these.
        </p>
      </div>

      {/* Toolbar */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center" }}>
        <button
          type="button"
          onClick={() => setShowUploadPanel((v) => !v)}
          style={{
            height: "34px", padding: "0 14px",
            display: "flex", alignItems: "center", gap: "8px",
            background: showUploadPanel ? "#2563eb" : "#3b82f6", color: "#ffffff",
            border: "none", borderRadius: "4px", fontSize: "14px", fontWeight: 500, cursor: "pointer",
          }}
        >
          <Plus size={16} /> Upload Document
        </button>
        <div style={{ width: "1px", height: "22px", background: "#2a2d35", margin: "0 4px" }} />
        <div style={{
          display: "flex", alignItems: "center", gap: "8px",
          height: "34px", padding: "0 10px",
          background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px",
          minWidth: "220px", color: "#555869",
        }}>
          <Search size={16} />
          <input
            placeholder="Search documents…"
            value={docSearch}
            onChange={(e) => setDocSearch(e.target.value)}
            style={{ flex: 1, background: "transparent", border: "none", color: "#e8eaf0", fontSize: "14px", outline: "none" }}
          />
        </div>
        <select
          value={docTypeFilter}
          onChange={(e) => setDocTypeFilter(e.target.value)}
          aria-label="Document type filter"
          style={{
            height: "34px", padding: "0 8px",
            background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px",
            color: "#e8eaf0", fontSize: "13px",
          }}
        >
          {DOC_TYPE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      {/* Upload panel */}
      {showUploadPanel && (
        <DocumentUploader
          uploadUrl="/api/v1/me/documents"
          onUploaded={(doc) => {
            setDocs((prev) => [doc, ...prev]);
            setShowUploadPanel(false);
          }}
        />
      )}

      {/* Documents table */}
      <div
        style={{
          background: "#111318",
          border: "1px solid #2a2d35",
          borderRadius: "8px",
          overflow: "hidden",
        }}
      >
        {loading ? (
          <div style={{ padding: "24px", fontSize: "13px", color: "#555869" }}>
            Loading…
          </div>
        ) : (
          <>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", minWidth: "760px", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ background: "#14161c" }}>
                    <th style={{ width: "40px", padding: "10px 0 10px 14px", borderBottom: "1px solid #2a2d35" }} />
                    <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2d35" }}>
                      <button type="button" onClick={() => toggleSort("name")} style={{ display: "flex", alignItems: "center", gap: "6px", background: "none", border: "none", padding: 0, color: "#8b8fa8", fontSize: "12px", fontWeight: 500, letterSpacing: "0.04em", cursor: "pointer" }}>
                        FILENAME <ArrowUpDown size={14} />
                      </button>
                    </th>
                    <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>TYPE</th>
                    <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2d35" }}>
                      <button type="button" onClick={() => toggleSort("size")} style={{ display: "flex", alignItems: "center", gap: "6px", background: "none", border: "none", padding: 0, color: "#8b8fa8", fontSize: "12px", fontWeight: 500, letterSpacing: "0.04em", cursor: "pointer" }}>
                        SIZE <ArrowUpDown size={14} />
                      </button>
                    </th>
                    <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>OCR</th>
                    <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2d35" }}>
                      <button type="button" onClick={() => toggleSort("date")} style={{ display: "flex", alignItems: "center", gap: "6px", background: "none", border: "none", padding: 0, color: "#8b8fa8", fontSize: "12px", fontWeight: 500, letterSpacing: "0.04em", cursor: "pointer" }}>
                        UPLOADED <ArrowUpDown size={14} />
                      </button>
                    </th>
                    <th style={{ textAlign: "right", padding: "10px 14px 10px 12px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>ACTIONS</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSortedDocs.map((d) => (
                    <tr key={d.id} style={{ cursor: "default" }}>
                      <td style={{ padding: "12px 0 12px 14px", borderBottom: "1px solid #1e2028", color: fileIconColor(d.filename) }}>
                        <FileText size={16} />
                      </td>
                      <td style={{ padding: "12px", borderBottom: "1px solid #1e2028", maxWidth: "300px" }}>
                        <span title={d.filename} style={{ display: "block", fontSize: "13px", color: "#e8eaf0", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", fontFamily: "'JetBrains Mono', monospace" }}>
                          {d.filename}
                        </span>
                      </td>
                      <td style={{ padding: "12px", borderBottom: "1px solid #1e2028" }}>
                        <span style={{ fontSize: "11px", letterSpacing: "0.05em", color: "#8b8fa8", textTransform: "uppercase" }}>
                          {d.docType.replace(/_/g, " ")}
                        </span>
                      </td>
                      <td style={{ padding: "12px", borderBottom: "1px solid #1e2028", fontSize: "13px", color: "#8b8fa8", whiteSpace: "nowrap" }}>
                        {fmtSize(d.fileSizeBytes)}
                      </td>
                      <td style={{ padding: "12px", borderBottom: "1px solid #1e2028" }}>
                        <OcrChip doc={d} isGenerating={ocrGenerating === d.id} />
                      </td>
                      <td style={{ padding: "12px", borderBottom: "1px solid #1e2028", fontSize: "13px", color: "#8b8fa8", whiteSpace: "nowrap" }}>
                        {formatDate(d.createdAt)}
                      </td>
                      <td style={{ padding: "8px 14px 8px 12px", borderBottom: "1px solid #1e2028" }}>
                        <div style={{ display: "flex", gap: "2px", justifyContent: "flex-end" }}>
                          <button type="button" title="Download" onClick={() => void downloadDocument(d.id, d.filename)} style={{ width: "32px", height: "32px", display: "flex", alignItems: "center", justifyContent: "center", background: "transparent", border: "none", borderRadius: "4px", color: "#8b8fa8", cursor: "pointer" }}>
                            <Download size={16} />
                          </button>
                          <button type="button" title="Share document" onClick={() => setShareDocTarget(d)} style={{ width: "32px", height: "32px", display: "flex", alignItems: "center", justifyContent: "center", background: "transparent", border: "none", borderRadius: "4px", color: "#8b8fa8", cursor: "pointer" }}>
                            <Share2 size={16} />
                          </button>
                          <div style={{ position: "relative" }}>
                            <button
                              type="button"
                              title="More actions"
                              onClick={() => setMenuDocId(menuDocId === d.id ? null : d.id)}
                              style={{ width: "32px", height: "32px", display: "flex", alignItems: "center", justifyContent: "center", background: menuDocId === d.id ? "#1e2028" : "transparent", border: "none", borderRadius: "4px", color: "#8b8fa8", cursor: "pointer" }}
                            >
                              <MoreVertical size={16} />
                            </button>
                            {menuDocId === d.id && (
                              <>
                                <div style={{ position: "fixed", inset: 0, zIndex: 49 }} onClick={() => setMenuDocId(null)} />
                                <div style={{ position: "absolute", right: 0, top: 36, zIndex: 50, background: "#1a1d24", border: "1px solid #2a2d35", borderRadius: "6px", minWidth: "180px", padding: "4px 0", boxShadow: "0 8px 24px rgba(0,0,0,0.5)" }}>
                                  {d.ocrStatus === "NOT_APPLICABLE" && isOcrExt(d.filename) && (
                                    <button type="button" disabled={ocrGenerating === d.id} onClick={() => { setMenuDocId(null); void handleGenerateOcr(d); }} style={{ width: "100%", padding: "8px 14px", display: "flex", alignItems: "center", gap: "8px", background: "transparent", border: "none", color: "#e8eaf0", fontSize: "13px", cursor: ocrGenerating === d.id ? "not-allowed" : "pointer", opacity: ocrGenerating === d.id ? 0.6 : 1, textAlign: "left" }}>
                                      <FileText size={14} style={{ color: "#8b8fa8" }} /> {ocrGenerating === d.id ? "Scanning…" : "Generate OCR"}
                                    </button>
                                  )}
                                  {(d.ocrStatus === "DONE" || d.ocrStatus === "AWAITING_APPROVAL") && (
                                    <button type="button" onClick={() => { setMenuDocId(null); setOcrDoc(d); }} style={{ width: "100%", padding: "8px 14px", display: "flex", alignItems: "center", gap: "8px", background: "transparent", border: "none", color: d.ocrStatus === "AWAITING_APPROVAL" ? "#f59e0b" : "#e8eaf0", fontSize: "13px", cursor: "pointer", textAlign: "left" }}>
                                      <FileText size={14} style={{ color: "#8b8fa8" }} /> {d.ocrStatus === "AWAITING_APPROVAL" ? "Review OCR" : "View OCR"}
                                    </button>
                                  )}
                                  {(d.ocrStatus === "FAILED" || d.ocrStatus === "DONE" || d.ocrStatus === "AWAITING_APPROVAL") && isOcrExt(d.filename) && (
                                    <button type="button" disabled={ocrGenerating === d.id} onClick={() => { setMenuDocId(null); void handleGenerateOcr(d, true); }} style={{ width: "100%", padding: "8px 14px", display: "flex", alignItems: "center", gap: "8px", background: "transparent", border: "none", color: "#e8eaf0", fontSize: "13px", cursor: ocrGenerating === d.id ? "not-allowed" : "pointer", opacity: ocrGenerating === d.id ? 0.6 : 1, textAlign: "left" }}>
                                      <FileText size={14} style={{ color: "#8b8fa8" }} /> {ocrGenerating === d.id ? "Scanning…" : "Re-OCR"}
                                    </button>
                                  )}
                                  <div style={{ height: "1px", background: "#2a2d35", margin: "4px 0" }} />
                                  <button type="button" onClick={() => { setMenuDocId(null); setPendingDeleteDoc(d); setDeleteOtp(""); setDeleteOtpError(""); }} style={{ width: "100%", padding: "8px 14px", display: "flex", alignItems: "center", gap: "8px", background: "transparent", border: "none", color: "#ef4444", fontSize: "13px", cursor: "pointer", textAlign: "left" }}>
                                    <Trash2 size={14} /> Delete document
                                  </button>
                                </div>
                              </>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {filteredSortedDocs.length === 0 && (
              <div
                style={{
                  padding: "48px 24px",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: "12px",
                  color: "#555869",
                }}
              >
                <FileText size={36} />
                <div style={{ fontSize: "14px", color: "#8b8fa8" }}>
                  {docs.length === 0 ? "No personal documents yet." : "No documents match these filters."}
                </div>
                {docs.length === 0 && (
                  <div style={{ fontSize: "12px", color: "#555869" }}>
                    Upload a file above — it will be encrypted at rest.
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>

      {ocrDoc && (
        <OcrApprovalModal
          doc={ocrDoc}
          onUpdated={updateDoc}
          onClose={() => setOcrDoc(null)}
        />
      )}

      {pendingDeleteDoc && (
        <StepUpMfaModal
          label={`Delete "${pendingDeleteDoc.filename}" — this is permanent and logged to the audit trail.`}
          otp={deleteOtp}
          error={deleteOtpError}
          onOtpChange={setDeleteOtp}
          onVerify={() => void handleDeleteDoc(pendingDeleteDoc, deleteOtp)}
          onClose={() => { setPendingDeleteDoc(null); setDeleteOtp(""); setDeleteOtpError(""); }}
        />
      )}

      {shareDocTarget && (
        <ShareModal
          scope="DOCUMENT"
          documentId={shareDocTarget.id}
          filename={shareDocTarget.filename}
          onClose={() => setShareDocTarget(null)}
        />
      )}
    </div>
  );
}
