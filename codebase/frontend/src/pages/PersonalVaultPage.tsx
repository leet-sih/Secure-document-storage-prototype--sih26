/**
 * PersonalVaultPage — /my-documents
 * Encrypted personal document store for the logged-in user.
 * Uploads go to POST /api/v1/me/documents; listing from GET /api/v1/me/documents.
 * No case association — access is owner-only (enforced server-side).
 */

import { useEffect, useState } from "react";
import { FileText } from "lucide-react";

import DocumentUploader from "../components/DocumentUploader";
import { fetchPersonalDocs } from "../lib/documentApi";
import type { DocumentMeta } from "../types";

export default function PersonalVaultPage() {
  const [docs, setDocs] = useState<DocumentMeta[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPersonalDocs()
      .then(setDocs)
      .catch(() => {})
      .finally(() => setLoading(false));
    // Run once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #2a2d35" }}>
                {["Filename", "Type", "Size", "Uploaded"].map((h) => (
                  <th
                    key={h}
                    style={{
                      padding: "10px 16px",
                      textAlign: "left",
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
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
