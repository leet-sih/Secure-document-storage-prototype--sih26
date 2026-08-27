// DESIGN REFERENCE — match this layout exactly when building src/components/StepUpMfaModal.tsx

import { ShieldAlert } from 'lucide-react';

/**
 * Step-up MFA modal — appears before sensitive actions (download, sign, share).
 *
 * Props:
 *   modalLabel      {string}   — context string, e.g. "Download: forensic_report.pdf"
 *   stepUpOtpValue  {string}
 *   stepUpError     {string}   — non-empty shows the error line
 *   onSetStepUpOtp  {fn}
 *   onVerify        {fn}
 *   onClose         {fn}
 */
export default function StepUpMfaModal({
  modalLabel = "",
  stepUpOtpValue = "",
  stepUpError = "",
  onSetStepUpOtp,
  onVerify,
  onClose,
}) {
  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 90,
      background: "rgba(0,0,0,0.6)",
      display: "flex", alignItems: "center", justifyContent: "center",
      padding: "24px", animation: "fadein 120ms ease-out"
    }}>
      <div style={{
        width: "400px", maxWidth: "100%",
        background: "#1a1d24", border: "1px solid #2a2d35", borderRadius: "8px",
        boxShadow: "0 28px 60px rgba(0,0,0,0.6)",
        padding: "22px", display: "flex", flexDirection: "column", gap: "10px"
      }}>
        <div style={{ color: "#f59e0b", display: "flex" }}><ShieldAlert size={20} /></div>

        <div style={{ fontSize: "17px", fontWeight: 600, color: "#e8eaf0", marginTop: "2px" }}>
          Identity Re-Verification Required
        </div>

        <div style={{ fontSize: "13px", color: "#8b8fa8", lineHeight: 1.55 }}>
          This action requires a fresh authentication code.
        </div>

        {/* Context label */}
        <div style={{
          fontSize: "12px", fontFamily: "'JetBrains Mono', monospace", color: "#555869",
          background: "#14161c", border: "1px solid #2a2d35", borderRadius: "6px",
          padding: "8px 10px", wordBreak: "break-word"
        }}>
          {modalLabel}
        </div>

        {/* OTP input */}
        <input
          inputMode="numeric"
          maxLength={6}
          placeholder="––––––"
          value={stepUpOtpValue}
          onChange={onSetStepUpOtp}
          style={{
            marginTop: "6px", height: "48px", textAlign: "center",
            fontFamily: "'JetBrains Mono', monospace", fontSize: "22px",
            letterSpacing: "0.4em", textIndent: "0.4em",
            color: "#e8eaf0", background: "#1e2028",
            border: "1px solid #2a2d35", borderRadius: "6px"
          }}
        />

        {/* Error */}
        {stepUpError && (
          <div style={{ fontSize: "12px", color: "#ef4444" }}>{stepUpError}</div>
        )}

        {/* Actions */}
        <div style={{ display: "flex", gap: "8px", marginTop: "8px" }}>
          <button
            type="button"
            onClick={onVerify}
            style={{
              flex: 1, height: "34px",
              background: "#3b82f6", color: "#ffffff",
              border: "none", borderRadius: "4px",
              fontSize: "14px", fontWeight: 500, cursor: "pointer"
            }}
            /* hover: background #2563eb */
          >
            Verify
          </button>
          <button
            type="button"
            onClick={onClose}
            style={{
              height: "34px", padding: "0 14px",
              background: "transparent", border: "1px solid #2a2d35", borderRadius: "4px",
              color: "#8b8fa8", fontSize: "14px", cursor: "pointer"
            }}
            /* hover: color #e8eaf0 */
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
