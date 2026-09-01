// DESIGN REFERENCE — match this layout exactly when building src/pages/CaseDetailPage.tsx (Documents tab)

import {
  Upload, Search, Download, PenLine, Share2, MoreVertical,
  ArrowUpDown, FileText, XCircle, CheckCircle2, RefreshCw, X
} from 'lucide-react';

/**
 * Props:
 *   showUpload      {boolean}  — upload panel is expanded
 *   uploading       {boolean}  — upload in progress
 *   uploadPctLabel  {string}   — e.g. "37%"
 *   uploadWidth     {string}   — CSS width for progress bar, e.g. "37%"
 *   uploadDone      {boolean}  — success state
 *   docsView        {array}    — [{ icon (JSX), iconColor, rowBg, filename, typeLabel, size, ocr {icon,color,label}, created, open (fn), download (fn), sign (fn), share (fn), more (fn) }]
 *   noDocs          {boolean}
 *   onToggleUpload  {fn}
 *   onSetDocSearch  {fn}
 *   onSetDocType    {fn}
 *   onSetUploadType {fn}
 *   onStartUpload   {fn}
 *   onCancelUpload  {fn}
 *   onRetryUpload   {fn}
 *   onSortName      {fn}
 *   onSortSize      {fn}
 *   onSortDate      {fn}
 */
export default function DocumentsTab({
  showUpload = false,
  uploading = false,
  uploadPctLabel = "0%",
  uploadWidth = "0%",
  uploadDone = false,
  docsView = [],
  noDocs = false,
  onToggleUpload,
  onSetDocSearch,
  onSetDocType,
  onSetUploadType,
  onStartUpload,
  onCancelUpload,
  onRetryUpload,
  onSortName,
  onSortSize,
  onSortDate,
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>

      {/* Toolbar */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center" }}>
        <button
          type="button"
          onClick={onToggleUpload}
          style={{
            height: "34px", padding: "0 14px",
            display: "flex", alignItems: "center", gap: "8px",
            background: "#3b82f6", color: "#ffffff",
            border: "none", borderRadius: "4px", fontSize: "14px", fontWeight: 500, cursor: "pointer"
          }}
          /* hover: background #2563eb */
        >
          <Upload size={16} /> Upload Document
        </button>

        <div style={{ width: "1px", height: "22px", background: "#2a2d35", margin: "0 4px" }} />

        <div style={{
          display: "flex", alignItems: "center", gap: "8px",
          height: "34px", padding: "0 10px",
          background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px",
          minWidth: "220px", color: "#555869"
        }}>
          <Search size={16} />
          <input
            placeholder="Search documents…"
            onChange={onSetDocSearch}
            style={{ flex: 1, height: "32px", background: "transparent", border: "none", color: "#e8eaf0", fontSize: "14px" }}
          />
        </div>

        <select
          onChange={onSetDocType}
          aria-label="Document type filter"
          style={{
            height: "34px", padding: "0 8px",
            background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px",
            color: "#e8eaf0", fontSize: "13px"
          }}
        >
          <option value="All">Type — all</option>
          <option value="FIR">FIR</option>
          <option value="EVIDENCE_RECORD">Evidence record</option>
          <option value="FORENSIC_REPORT">Forensic report</option>
          <option value="WITNESS_STATEMENT">Witness statement</option>
          <option value="INVESTIGATION_RECORD">Investigation record</option>
          <option value="CHARGE_SHEET">Charge sheet</option>
          <option value="COURT_FILING">Court filing</option>
        </select>
      </div>

      {/* Upload panel */}
      {showUpload && (
        <div style={{
          background: "#111318", border: "1px solid #2a2d35", borderRadius: "8px",
          padding: "20px", display: "flex", flexDirection: "column", gap: "16px",
          animation: "rise 180ms ease-out"
        }}>
          {/* Drop zone */}
          <div style={{
            border: "1px dashed #3a3d47", borderRadius: "8px", padding: "28px",
            display: "flex", flexDirection: "column", alignItems: "center", gap: "8px",
            textAlign: "center", background: "#14161c"
          }}>
            <div style={{ color: "#3b82f6", display: "flex" }}><Upload size={36} /></div>
            <div style={{ fontSize: "14px", color: "#e8eaf0" }}>Drag &amp; drop files here, or click to browse</div>
            <div style={{ fontSize: "12px", color: "#8b8fa8" }}>PDF, DOCX, XLSX, JPG, PNG, TIFF, MP4, WAV</div>
            <div style={{ fontSize: "11px", color: "#555869" }}>Maximum 500 MB per file</div>
          </div>

          {/* Upload options row */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: "10px", alignItems: "flex-end" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <label htmlFor="up-type" style={{ fontSize: "12px", color: "#8b8fa8" }}>
                Document type <span style={{ color: "#ef4444" }}>*</span>
              </label>
              <select
                id="up-type"
                onChange={onSetUploadType}
                style={{
                  height: "34px", padding: "0 8px",
                  background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px",
                  color: "#e8eaf0", fontSize: "13px", minWidth: "190px"
                }}
              >
                <option value="EVIDENCE_RECORD">Evidence record</option>
                <option value="FIR">FIR</option>
                <option value="FORENSIC_REPORT">Forensic report</option>
                <option value="WITNESS_STATEMENT">Witness statement</option>
                <option value="CHARGE_SHEET">Charge sheet</option>
                <option value="COURT_FILING">Court filing</option>
              </select>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "6px", flex: 1, minWidth: "200px" }}>
              <label htmlFor="up-tags" style={{ fontSize: "12px", color: "#8b8fa8" }}>
                Tags <span style={{ color: "#555869" }}>(optional)</span>
              </label>
              <input
                id="up-tags"
                placeholder="seizure, devices"
                style={{
                  height: "34px", padding: "0 10px",
                  background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px",
                  color: "#e8eaf0", fontSize: "13px"
                }}
              />
            </div>
            <button
              type="button"
              onClick={onStartUpload}
              style={{
                height: "34px", padding: "0 14px",
                background: "#3b82f6", color: "#ffffff",
                border: "none", borderRadius: "4px", fontSize: "14px", fontWeight: 500, cursor: "pointer"
              }}
              /* hover: background #2563eb */
            >
              Upload
            </button>
          </div>

          {/* Upload progress */}
          {uploading && (
            <div style={{
              display: "flex", flexDirection: "column", gap: "8px",
              background: "#1a1d24", border: "1px solid #2a2d35", borderRadius: "6px", padding: "12px"
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", color: "#e8eaf0" }}>
                <span style={{ color: "#3b82f6", display: "flex" }}><FileText size={14} /></span>
                <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "12px" }}>seizure_annexure_B.pdf</span>
                <span style={{ marginLeft: "auto", color: "#8b8fa8", fontSize: "12px" }}>{uploadPctLabel}</span>
                <button
                  type="button"
                  title="Cancel upload"
                  aria-label="Cancel upload"
                  onClick={onCancelUpload}
                  style={{
                    width: "24px", height: "24px", display: "flex", alignItems: "center", justifyContent: "center",
                    background: "transparent", border: "none", borderRadius: "4px", color: "#8b8fa8", cursor: "pointer"
                  }}
                  /* hover: color #e8eaf0; background #1e2028 */
                >
                  <X size={14} />
                </button>
              </div>
              <div style={{ height: "4px", background: "#2a2d35", borderRadius: "2px", overflow: "hidden" }}>
                <div style={{ height: "4px", width: uploadWidth, background: "#3b82f6", transition: "width 160ms linear" }} />
              </div>
            </div>
          )}

          {/* Upload success */}
          {uploadDone && (
            <div style={{
              display: "flex", alignItems: "center", gap: "8px",
              background: "#14391f", border: "1px solid #22c55e", borderRadius: "6px",
              padding: "10px 12px", fontSize: "13px", color: "#e8eaf0"
            }}>
              <span style={{ color: "#22c55e", display: "flex" }}><CheckCircle2 size={16} /></span>
              seizure_annexure_B.pdf uploaded · 3 chunks · SHA-256 recorded
            </div>
          )}

          {/* Upload error example — always visible in prototype for reference */}
          <div style={{
            display: "flex", alignItems: "center", gap: "10px",
            background: "#3d1010", border: "1px solid #ef4444", borderRadius: "6px", padding: "10px 12px"
          }}>
            <span style={{ color: "#ef4444", display: "flex" }}><XCircle size={16} /></span>
            <div style={{ display: "flex", flexDirection: "column", gap: "2px", minWidth: 0 }}>
              <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "12px", color: "#e8eaf0" }}>cctv_bundle_04.mp4</span>
              <span style={{ fontSize: "12px", color: "#8b8fa8" }}>Upload failed — chunk 3 checksum mismatch</span>
            </div>
            <button
              type="button"
              onClick={onRetryUpload}
              style={{
                marginLeft: "auto", height: "28px", padding: "0 10px",
                display: "flex", alignItems: "center", gap: "6px",
                background: "#1a1d24", border: "1px solid #2a2d35", borderRadius: "4px",
                color: "#e8eaf0", fontSize: "12px", cursor: "pointer"
              }}
              /* hover: background #1e2028 */
            >
              <RefreshCw size={14} /> Retry
            </button>
          </div>
        </div>
      )}

      {/* Documents table */}
      <div style={{ background: "#111318", border: "1px solid #2a2d35", borderRadius: "8px", overflow: "hidden" }}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", minWidth: "900px", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#14161c" }}>
                <th style={{ width: "40px", padding: "10px 0 10px 14px", borderBottom: "1px solid #2a2d35" }} />
                <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2d35" }}>
                  <button type="button" onClick={onSortName} style={{ display: "flex", alignItems: "center", gap: "6px", background: "none", border: "none", padding: 0, color: "#8b8fa8", fontSize: "12px", fontWeight: 500, letterSpacing: "0.04em", cursor: "pointer" }}
                    /* hover: color #e8eaf0 */>
                    FILENAME <ArrowUpDown size={14} />
                  </button>
                </th>
                <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>TYPE</th>
                <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2d35" }}>
                  <button type="button" onClick={onSortSize} style={{ display: "flex", alignItems: "center", gap: "6px", background: "none", border: "none", padding: 0, color: "#8b8fa8", fontSize: "12px", fontWeight: 500, letterSpacing: "0.04em", cursor: "pointer" }}
                    /* hover: color #e8eaf0 */>
                    SIZE <ArrowUpDown size={14} />
                  </button>
                </th>
                <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>OCR</th>
                <th style={{ textAlign: "left", padding: "10px 12px", borderBottom: "1px solid #2a2d35" }}>
                  <button type="button" onClick={onSortDate} style={{ display: "flex", alignItems: "center", gap: "6px", background: "none", border: "none", padding: 0, color: "#8b8fa8", fontSize: "12px", fontWeight: 500, letterSpacing: "0.04em", cursor: "pointer" }}
                    /* hover: color #e8eaf0 */>
                    UPLOADED <ArrowUpDown size={14} />
                  </button>
                </th>
                <th style={{ textAlign: "right", padding: "10px 14px 10px 12px", borderBottom: "1px solid #2a2d35", fontSize: "12px", fontWeight: 500, color: "#8b8fa8", letterSpacing: "0.04em" }}>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              {docsView.map((d, i) => (
                <tr
                  key={i}
                  onClick={d.open}
                  style={{ background: d.rowBg, cursor: "pointer" }}
                  /* hover: background #1a1d24 */
                >
                  <td style={{ padding: "12px 0 12px 14px", borderBottom: "1px solid #1e2028", color: d.iconColor }}>{d.icon}</td>
                  <td style={{ padding: "12px", borderBottom: "1px solid #1e2028", maxWidth: "300px" }}>
                    <span title={d.filename} style={{ display: "block", fontSize: "13px", color: "#e8eaf0", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {d.filename}
                    </span>
                  </td>
                  <td style={{ padding: "12px", borderBottom: "1px solid #1e2028" }}>
                    <span style={{ fontSize: "11px", letterSpacing: "0.05em", color: "#8b8fa8", textTransform: "uppercase" }}>{d.typeLabel}</span>
                  </td>
                  <td style={{ padding: "12px", borderBottom: "1px solid #1e2028", fontSize: "13px", color: "#8b8fa8", whiteSpace: "nowrap" }}>{d.size}</td>
                  <td style={{ padding: "12px", borderBottom: "1px solid #1e2028" }}>
                    <span style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: d.ocr.color, whiteSpace: "nowrap" }}>
                      {d.ocr.icon} {d.ocr.label}
                    </span>
                  </td>
                  <td style={{ padding: "12px", borderBottom: "1px solid #1e2028", fontSize: "13px", color: "#8b8fa8", whiteSpace: "nowrap" }}>{d.created}</td>
                  <td style={{ padding: "8px 14px 8px 12px", borderBottom: "1px solid #1e2028", position: "relative" }}>
                    <div style={{ display: "flex", gap: "2px", justifyContent: "flex-end" }}>
                      <button type="button" title="Download" aria-label="Download" onClick={d.download} style={{ width: "32px", height: "32px", display: "flex", alignItems: "center", justifyContent: "center", background: "transparent", border: "none", borderRadius: "4px", color: "#8b8fa8", cursor: "pointer" }} /* hover: color #e8eaf0; background #1e2028 */>
                        <Download size={16} />
                      </button>
                      <button type="button" title="Sign document" aria-label="Sign document" onClick={d.sign} style={{ width: "32px", height: "32px", display: "flex", alignItems: "center", justifyContent: "center", background: "transparent", border: "none", borderRadius: "4px", color: "#8b8fa8", cursor: "pointer" }} /* hover: color #e8eaf0; background #1e2028 */>
                        <PenLine size={16} />
                      </button>
                      <button type="button" title="Share" aria-label="Share" onClick={d.share} style={{ width: "32px", height: "32px", display: "flex", alignItems: "center", justifyContent: "center", background: "transparent", border: "none", borderRadius: "4px", color: "#8b8fa8", cursor: "pointer" }} /* hover: color #e8eaf0; background #1e2028 */>
                        <Share2 size={16} />
                      </button>
                      <button type="button" title="More actions" aria-label="More actions" onClick={d.more} style={{ width: "32px", height: "32px", display: "flex", alignItems: "center", justifyContent: "center", background: "transparent", border: "none", borderRadius: "4px", color: "#8b8fa8", cursor: "pointer" }} /* hover: color #e8eaf0; background #1e2028 */>
                        <MoreVertical size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {noDocs && (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "10px", padding: "48px 24px", color: "#555869" }}>
            <FileText size={36} />
            <div style={{ fontSize: "14px", color: "#8b8fa8" }}>No documents match these filters.</div>
          </div>
        )}
      </div>
    </div>
  );
}
