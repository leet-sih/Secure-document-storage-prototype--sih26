/**
 * PersonalVaultPage — /my-documents
 * Encrypted personal document store for the logged-in user.
 * Uploads go to POST /api/v1/me/documents; listing from GET /api/v1/me/documents.
 * No case association — access is owner-only (enforced server-side).
 */

import { useEffect, useState } from "react";
import { Download, FileText } from "lucide-react";

import DocumentUploader from "../components/DocumentUploader";
import OcrApprovalModal from "../components/OcrApprovalModal";
import { downloadDocument, fetchPersonalDocs, generateOcr } from "../lib/documentApi";
import type { DocumentMeta } from "../types";

const OCR_EXT = new Set([".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif"]);

function isOcrSupported(filename: string): boolean {
  const dot = filename.lastIndexOf(".");
  return dot >= 0 && OCR_EXT.has(filename.slice(dot).toLowerCase());
}

function OcrStatusBadge({ doc }: { doc: Pick<DocumentMeta, "ocrStatus" | "ocrConfidence" | "ocrDetail"> }) {
  const { ocrStatus, ocrConfidence, ocrDetail } = doc;
  if (!ocrStatus || ocrStatus === "NOT_APPLICABLE" || ocrStatus === "PENDING") return null;

  if (ocrStatus === "FAILED") {
    const pct = ocrConfidence != null ? Math.round(ocrConfidence * 100) : null;
    const label = pct != null ? `OCR Failed · ${pct}%` : "OCR Failed";
    return (
      <span
        title={ocrDetail ?? undefined}
        style={{
          display: "inline-block",
          marginLeft: "6px",
          fontSize: "10px",
          fontWeight: 500,
          padding: "1px 5px",
          borderRadius: "3px",
          color: "#ef4444",
          background: "#3d1010",
          verticalAlign: "middle",
          cursor: ocrDetail ? "help" : "default",
          textDecoration: ocrDetail ? "underline dotted" : "none",
        }}
      >
        {label}
      </span>
    );
  }

  if (ocrStatus === "AWAITING_APPROVAL") {
    const pct = ocrConfidence != null ? Math.round(ocrConfidence * 100) : null;
    const isLow = ocrConfidence != null && ocrConfidence < 0.6;
    const label = isLow && pct != null ? `Pending Review · ${pct}%` : "Pending Review";
    return (
      <span
        title={isLow ? (ocrDetail ?? "Low confidence — review carefully") : undefined}
        style={{
          display: "inline-block",
          marginLeft: "6px",
          fontSize: "10px",
          fontWeight: 500,
          padding: "1px 5px",
          borderRadius: "3px",
          color: isLow ? "#fb923c" : "#f59e0b",
          background: "#3d2c08",
          verticalAlign: "middle",
          cursor: isLow ? "help" : "default",
          textDecoration: isLow ? "underline dotted" : "none",
        }}
      >
        {label}
      </span>
    );
  }

  if (ocrStatus === "DONE") {
    return (
      <span
        style={{
          display: "inline-block",
          marginLeft: "6px",
          fontSize: "10px",
          fontWeight: 500,
          padding: "1px 5px",
          borderRadius: "3px",
          color: "#22c55e",
          background: "#14391f",
          verticalAlign: "middle",
        }}
      >
        OCR Done
      </span>
    );
  }

  return null;
}

export default function PersonalVaultPage() {
  const [docs, setDocs] = useState<DocumentMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [ocrDoc, setOcrDoc] = useState<DocumentMeta | null>(null);
  const [ocrGenerating, setOcrGenerating] = useState<string | null>(null);

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

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
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

      <DocumentUploader
        uploadUrl="/api/v1/me/documents"
        onUploaded={(doc) => setDocs((prev) => [doc, ...prev])}
      />

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
        ) : docs.length === 0 ? (
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
              No personal documents yet.
            </div>
            <div style={{ fontSize: "12px", color: "#555869" }}>
              Upload a file above — it will be encrypted at rest.
            </div>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", minWidth: "620px", borderCollapse: "collapse", fontSize: "13px" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #2a2d35" }}>
                {["Filename", "Type", "Size", "Uploaded", ""].map((h, i) => (
                  <th
                    key={i}
                    style={{
                      padding: "10px 16px",
                      textAlign: i === 4 ? "right" : "left",
                      color: "#555869",
                      fontWeight: 500,
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id} style={{ borderBottom: "1px solid #1e2028" }}>
                  <td
                    style={{
                      padding: "10px 16px",
                      color: "#e8eaf0",
                      fontFamily: "monospace",
                      fontSize: "12px",
                    }}
                  >
                    {d.filename}
                    <OcrStatusBadge doc={d} />
                  </td>
                  <td style={{ padding: "10px 16px", color: "#8b8fa8" }}>
                    {d.docType.replace(/_/g, " ")}
                  </td>
                  <td style={{ padding: "10px 16px", color: "#8b8fa8" }}>
                    {d.fileSizeBytes < 1024 * 1024
                      ? `${(d.fileSizeBytes / 1024).toFixed(1)} KB`
                      : `${(d.fileSizeBytes / 1024 / 1024).toFixed(1)} MB`}
                  </td>
                  <td style={{ padding: "10px 16px", color: "#555869" }}>
                    {new Date(d.createdAt).toLocaleDateString()}
                  </td>
                  <td style={{ padding: "6px 16px", textAlign: "right" }}>
                    <div style={{ display: "inline-flex", alignItems: "center", gap: "6px", flexWrap: "wrap", justifyContent: "flex-end" }}>
                      {d.ocrStatus === "NOT_APPLICABLE" && isOcrSupported(d.filename) && (
                        <button
                          type="button"
                          disabled={ocrGenerating === d.id}
                          onClick={() => handleGenerateOcr(d)}
                          style={{
                            height: "28px",
                            padding: "0 10px",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "5px",
                            background: "transparent",
                            border: "1px solid #2a2d35",
                            borderRadius: "4px",
                            color: "#8b8fa8",
                            fontSize: "12px",
                            cursor: ocrGenerating === d.id ? "not-allowed" : "pointer",
                            opacity: ocrGenerating === d.id ? 0.6 : 1,
                          }}
                        >
                          {ocrGenerating === d.id ? "Scanning…" : "Generate OCR"}
                        </button>
                      )}
                      {d.ocrStatus === "AWAITING_APPROVAL" && (
                        <button
                          type="button"
                          onClick={() => setOcrDoc(d)}
                          style={{
                            height: "28px",
                            padding: "0 10px",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "5px",
                            background: "#3d2c08",
                            border: "1px solid #f59e0b",
                            borderRadius: "4px",
                            color: "#f59e0b",
                            fontSize: "12px",
                            cursor: "pointer",
                          }}
                        >
                          Review OCR
                        </button>
                      )}
                      {d.ocrStatus === "DONE" && (
                        <button
                          type="button"
                          onClick={() => setOcrDoc(d)}
                          style={{
                            height: "28px",
                            padding: "0 10px",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "5px",
                            background: "#14391f",
                            border: "1px solid #22c55e",
                            borderRadius: "4px",
                            color: "#22c55e",
                            fontSize: "12px",
                            cursor: "pointer",
                          }}
                        >
                          View OCR
                        </button>
                      )}
                      {(d.ocrStatus === "FAILED" || d.ocrStatus === "DONE" || d.ocrStatus === "AWAITING_APPROVAL") && isOcrSupported(d.filename) && (
                        <button
                          type="button"
                          disabled={ocrGenerating === d.id}
                          onClick={() => handleGenerateOcr(d, true)}
                          style={{
                            height: "28px",
                            padding: "0 10px",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "5px",
                            background: "transparent",
                            border: "1px solid #2a2d35",
                            borderRadius: "4px",
                            color: "#555869",
                            fontSize: "12px",
                            cursor: ocrGenerating === d.id ? "not-allowed" : "pointer",
                            opacity: ocrGenerating === d.id ? 0.6 : 1,
                          }}
                        >
                          {ocrGenerating === d.id ? "Scanning…" : "Re-OCR"}
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => downloadDocument(d.id, d.filename)}
                        style={{
                          height: "28px",
                          padding: "0 10px",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "5px",
                          background: "#3b82f6",
                          border: "none",
                          borderRadius: "4px",
                          color: "#ffffff",
                          fontSize: "12px",
                          fontWeight: 500,
                          cursor: "pointer",
                        }}
                      >
                        <Download size={12} /> Download
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </div>

      {ocrDoc && (
        <OcrApprovalModal
          doc={ocrDoc}
          onUpdated={updateDoc}
          onClose={() => setOcrDoc(null)}
        />
      )}
    </div>
  );
}
