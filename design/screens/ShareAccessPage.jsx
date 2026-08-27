// DESIGN REFERENCE — match this layout exactly when building src/pages/ShareAccessPage.tsx

import { Shield, FileText, Clock, Download, CheckCircle2, ShieldX } from 'lucide-react';

/**
 * Props:
 *   isValid         {boolean}  — show the valid share state
 *   isDead          {boolean}  — show the expired/revoked state
 *   shareDone       {boolean}  — download started success banner
 *   onSetShareEmail {fn}
 *   onShareDownload {fn}
 */
export default function ShareAccessPage({
  isValid = true,
  isDead = false,
  shareDone = false,
  onSetShareEmail,
  onShareDownload,
}) {
  return (
    <div style={{
      minHeight: "100vh", display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
      gap: "28px", padding: "48px 24px",
      background: "#0a0c10", color: "#e8eaf0"
    }}>

      {/* Logo */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "10px" }}>
        <div style={{ color: "#3b82f6", display: "flex" }}><Shield size={36} /></div>
        <div style={{ fontSize: "24px", fontWeight: 700, letterSpacing: "0.18em", color: "#e8eaf0" }}>PRAMAAN</div>
        <div style={{ fontSize: "13px", color: "#8b8fa8" }}>Secure Evidence Vault</div>
      </div>

      {/* ── Valid share link ── */}
      {isValid && (
        <div style={{
          width: "420px", maxWidth: "100%",
          background: "#111318", border: "1px solid #2a2d35", borderRadius: "8px",
          padding: "24px", display: "flex", flexDirection: "column", gap: "18px"
        }}>

          {/* Document header */}
          <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
            <div style={{ color: "#3b82f6", marginTop: "2px", display: "flex" }}><FileText size={20} /></div>
            <div style={{ display: "flex", flexDirection: "column", gap: "4px", minWidth: 0 }}>
              <div style={{ fontSize: "15px", fontWeight: 600, color: "#e8eaf0", wordBreak: "break-all" }}>
                forensic_wallet_trace_report.pdf
              </div>
              <div style={{ fontSize: "12px", color: "#8b8fa8" }}>FORENSIC REPORT · 8.7 MB</div>
              <div style={{ fontSize: "12px", color: "#f59e0b", display: "flex", alignItems: "center", gap: "6px", marginTop: "2px" }}>
                <Clock size={14} /> Expires in 18 hours
              </div>
            </div>
          </div>

          {/* Recipient restriction */}
          <div style={{
            background: "#1a1d24", border: "1px solid #2a2d35",
            borderRadius: "6px", padding: "12px"
          }}>
            <div style={{ fontSize: "12px", color: "#8b8fa8", marginBottom: "4px" }}>This link is restricted to</div>
            <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "12px", color: "#e8eaf0" }}>
              prosecutor@court.gov.in
            </div>
          </div>

          {/* Email field */}
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <label htmlFor="sh-email" style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>
              Email <span style={{ color: "#8b8fa8", fontWeight: 400 }}>(required)</span>
            </label>
            <input
              id="sh-email"
              type="email"
              placeholder="Enter your email to continue"
              onChange={onSetShareEmail}
              style={{
                height: "36px", padding: "0 10px", fontSize: "14px",
                color: "#e8eaf0", background: "#1e2028",
                border: "1px solid #2a2d35", borderRadius: "6px"
              }}
            />
          </div>

          {/* Download button */}
          <button
            type="button"
            onClick={onShareDownload}
            style={{
              height: "34px", display: "flex", alignItems: "center", justifyContent: "center",
              gap: "8px", background: "#3b82f6", color: "#ffffff",
              border: "none", borderRadius: "4px", fontSize: "14px", fontWeight: 500, cursor: "pointer"
            }}
            /* hover: background #2563eb */
          >
            <Download size={16} /> Download Document
          </button>

          {/* Success banner */}
          {shareDone && (
            <div style={{
              display: "flex", gap: "8px", alignItems: "center",
              background: "#14391f", border: "1px solid #22c55e",
              borderRadius: "6px", padding: "10px 12px",
              fontSize: "13px", color: "#e8eaf0"
            }}>
              <CheckCircle2 size={16} /> Download started. This access has been logged.
            </div>
          )}

          {/* Footer */}
          <div style={{
            fontSize: "11px", color: "#555869", textAlign: "center",
            display: "flex", alignItems: "center", justifyContent: "center", gap: "6px"
          }}>
            <Shield size={14} /> Accessed links are logged.
          </div>
        </div>
      )}

      {/* ── Dead / expired link ── */}
      {isDead && (
        <div style={{
          width: "420px", maxWidth: "100%",
          background: "#111318", border: "1px solid #2a2d35", borderRadius: "8px",
          padding: "28px 24px", display: "flex", flexDirection: "column",
          alignItems: "center", gap: "12px", textAlign: "center"
        }}>
          <div style={{ color: "#ef4444", display: "flex" }}><ShieldX size={36} /></div>
          <div style={{ fontSize: "17px", fontWeight: 600, color: "#e8eaf0" }}>
            This link is no longer valid.
          </div>
          <div style={{ fontSize: "13px", color: "#8b8fa8", lineHeight: 1.6, maxWidth: "300px" }}>
            It may have expired, been revoked, or reached its maximum number of uses.
          </div>
          <div style={{ fontSize: "13px", color: "#8b8fa8", lineHeight: 1.6 }}>
            Contact the issuing officer for a new link.
          </div>
        </div>
      )}
    </div>
  );
}
