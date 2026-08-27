// DESIGN REFERENCE — match this layout exactly when building src/pages/MfaSetupPage.tsx

import { Shield, KeyRound, Copy } from 'lucide-react';

/**
 * Props:
 *   mfaOtpValue   {string}   — controlled value for the OTP input
 *   onSetMfaOtp   {fn}
 *   onCopy        {fn}       — copy the manual key to clipboard
 *   onActivateMfa {fn}       — submit the confirmation code
 */
export default function MfaSetupPage({
  mfaOtpValue = "",
  onSetMfaOtp,
  onCopy,
  onActivateMfa,
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

      {/* Setup card */}
      <div style={{
        width: "520px", maxWidth: "100%",
        background: "#111318", border: "1px solid #2a2d35", borderRadius: "8px",
        padding: "24px", display: "flex", flexDirection: "column", gap: "20px"
      }}>

        {/* Header */}
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <div style={{ color: "#3b82f6", display: "flex" }}><KeyRound size={20} /></div>
          <div style={{ fontSize: "20px", fontWeight: 600, color: "#e8eaf0" }}>
            Set Up Two-Factor Authentication
          </div>
          <div style={{ fontSize: "13px", color: "#8b8fa8" }}>Required before accessing the system.</div>
        </div>

        {/* Step 1 — QR + manual key */}
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <div style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>
            Step 1 — Scan this QR code
          </div>
          <div style={{ display: "flex", gap: "20px", alignItems: "flex-start", flexWrap: "wrap" }}>

            {/* QR placeholder */}
            <div style={{
              width: "152px", height: "152px", flex: "none",
              border: "1px dashed #3a3d47", borderRadius: "6px",
              background: "repeating-linear-gradient(45deg, #14161c 0 6px, #1a1d24 6px 12px)",
              display: "flex", alignItems: "center", justifyContent: "center",
              textAlign: "center",
              fontFamily: "'JetBrains Mono', monospace", fontSize: "10px",
              color: "#555869", lineHeight: 1.6, padding: "12px"
            }}>
              QR CODE<br />otpauth://
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "8px", minWidth: "200px" }}>
              <div style={{ fontSize: "13px", color: "#8b8fa8" }}>Or enter this key manually:</div>

              {/* Manual key row */}
              <div style={{
                display: "flex", alignItems: "center", gap: "8px",
                background: "#1e2028", border: "1px solid #2a2d35",
                borderRadius: "6px", padding: "8px 10px"
              }}>
                <code style={{
                  fontFamily: "'JetBrains Mono', monospace", fontSize: "12px",
                  color: "#e8eaf0", letterSpacing: "0.04em"
                }}>
                  JBSWY3DPEHPK3PXP
                </code>
                <button
                  type="button"
                  title="Copy key"
                  aria-label="Copy key"
                  onClick={onCopy}
                  style={{
                    marginLeft: "auto", width: "24px", height: "24px", flex: "none",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    background: "transparent", border: "none", borderRadius: "4px",
                    color: "#8b8fa8", cursor: "pointer"
                  }}
                  /* hover: color #e8eaf0; background #1a1d24 */
                >
                  <Copy size={14} />
                </button>
              </div>

              <div style={{ fontSize: "11px", color: "#555869", lineHeight: 1.6 }}>
                Issuer PRAMAAN · Algorithm SHA-1 · 6 digits · 30s period
              </div>
            </div>
          </div>
        </div>

        {/* Step 2 — confirm code */}
        <div style={{
          display: "flex", flexDirection: "column", gap: "10px",
          borderTop: "1px solid #2a2d35", paddingTop: "20px"
        }}>
          <div style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>
            Step 2 — Enter the 6-digit code to confirm setup
          </div>
          <input
            inputMode="numeric"
            maxLength={6}
            placeholder="––––––"
            value={mfaOtpValue}
            onChange={onSetMfaOtp}
            style={{
              width: "220px", height: "48px", textAlign: "center",
              fontFamily: "'JetBrains Mono', monospace", fontSize: "22px",
              letterSpacing: "0.4em", textIndent: "0.4em",
              color: "#e8eaf0", background: "#1e2028",
              border: "1px solid #2a2d35", borderRadius: "6px"
            }}
          />
          <button
            type="button"
            onClick={onActivateMfa}
            style={{
              alignSelf: "flex-start", marginTop: "4px",
              height: "34px", padding: "0 16px",
              background: "#3b82f6", color: "#ffffff",
              border: "none", borderRadius: "4px",
              fontSize: "14px", fontWeight: 500, cursor: "pointer"
            }}
            /* hover: background #2563eb */
          >
            Activate MFA
          </button>
        </div>
      </div>
    </div>
  );
}
