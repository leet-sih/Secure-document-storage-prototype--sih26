// DESIGN REFERENCE — match this layout exactly when building src/pages/LoginPage.tsx

import { Shield, KeyRound, AlertCircle } from 'lucide-react';

/**
 * Props:
 *   showCreds       {boolean}  — show the credentials form (isLoginCreds)
 *   showMfa         {boolean}  — show the TOTP step (isLoginMfa)
 *   loginError      {string}   — non-empty string shows the error banner
 *   otpValue        {string}   — current value of the OTP input
 *   onSetEmail      {fn}
 *   onSetPassword   {fn}
 *   onSignIn        {fn}       — submit credentials
 *   onSetOtp        {fn}
 *   onVerifyMfa     {fn}       — submit TOTP code
 *   onBackToCreds   {fn}       — "Back" button in MFA step
 */
export default function LoginPage({
  showCreds = true,
  showMfa = false,
  loginError = "",
  otpValue = "",
  onSetEmail,
  onSetPassword,
  onSignIn,
  onSetOtp,
  onVerifyMfa,
  onBackToCreds,
}) {
  return (
    <div style={{
      minHeight: "100vh", display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
      gap: "28px", padding: "48px 24px",
      background: "#0a0c10", color: "#e8eaf0"
    }}>

      {/* Logo + wordmark */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "10px" }}>
        <div style={{ color: "#3b82f6", display: "flex" }}><Shield size={36} /></div>
        <div style={{ fontSize: "24px", fontWeight: 700, letterSpacing: "0.18em", color: "#e8eaf0" }}>PRAMAAN</div>
        <div style={{ fontSize: "13px", color: "#8b8fa8" }}>Secure Evidence Vault</div>
      </div>

      {/* ── Credentials form ── */}
      {showCreds && (
        <div style={{
          width: "380px", maxWidth: "100%",
          background: "#111318", border: "1px solid #2a2d35", borderRadius: "8px",
          padding: "24px", display: "flex", flexDirection: "column", gap: "16px"
        }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <label htmlFor="lg-email" style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>Email</label>
            <input
              id="lg-email"
              type="email"
              defaultValue="ravi.kumar@mah.police.gov.in"
              onChange={onSetEmail}
              style={{
                height: "36px", padding: "0 10px", fontSize: "14px",
                color: "#e8eaf0", background: "#1e2028",
                border: "1px solid #2a2d35", borderRadius: "6px"
              }}
            />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <label htmlFor="lg-pw" style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>Password</label>
            <input
              id="lg-pw"
              type="password"
              placeholder="••••••••••••"
              onChange={onSetPassword}
              style={{
                height: "36px", padding: "0 10px", fontSize: "14px",
                color: "#e8eaf0", background: "#1e2028",
                border: "1px solid #2a2d35", borderRadius: "6px"
              }}
            />
          </div>

          {/* Error banner */}
          {loginError && (
            <div style={{
              display: "flex", gap: "8px", alignItems: "flex-start",
              background: "#3d1010", border: "1px solid #ef4444",
              borderRadius: "6px", padding: "10px 12px"
            }}>
              <div style={{ color: "#ef4444", marginTop: "1px", display: "flex" }}>
                <AlertCircle size={16} />
              </div>
              <div style={{ fontSize: "13px", color: "#e8eaf0", lineHeight: 1.45 }}>{loginError}</div>
            </div>
          )}

          <button
            type="button"
            onClick={onSignIn}
            style={{
              height: "34px", background: "#3b82f6", color: "#ffffff",
              border: "none", borderRadius: "4px",
              fontSize: "14px", fontWeight: 500, cursor: "pointer"
            }}
            /* hover: background #2563eb */
          >
            Sign In
          </button>
        </div>
      )}

      {/* ── MFA step ── */}
      {showMfa && (
        <div style={{
          width: "380px", maxWidth: "100%",
          background: "#111318", border: "1px solid #2a2d35", borderRadius: "8px",
          padding: "24px", display: "flex", flexDirection: "column", gap: "8px",
          animation: "rise 200ms ease-out"
        }}>
          <div style={{ color: "#3b82f6", display: "flex" }}><KeyRound size={20} /></div>
          <div style={{ fontSize: "17px", fontWeight: 600, color: "#e8eaf0", marginTop: "4px" }}>
            Two-Factor Authentication
          </div>
          <div style={{ fontSize: "13px", color: "#8b8fa8", lineHeight: 1.5 }}>
            Enter the 6-digit code from your authenticator app.
          </div>

          <input
            inputMode="numeric"
            maxLength={6}
            placeholder="––––––"
            value={otpValue}
            onChange={onSetOtp}
            style={{
              marginTop: "12px", height: "52px", textAlign: "center",
              fontFamily: "'JetBrains Mono', monospace", fontSize: "24px",
              letterSpacing: "0.42em", textIndent: "0.42em",
              color: "#e8eaf0", background: "#1e2028",
              border: "1px solid #2a2d35", borderRadius: "6px"
            }}
          />
          <div style={{ fontSize: "11px", color: "#555869", textAlign: "center", marginTop: "2px" }}>
            Code refreshes every 30 seconds
          </div>

          <div style={{ display: "flex", gap: "8px", marginTop: "12px" }}>
            <button
              type="button"
              onClick={onVerifyMfa}
              style={{
                flex: 1, height: "34px", background: "#3b82f6", color: "#ffffff",
                border: "none", borderRadius: "4px", fontSize: "14px", fontWeight: 500, cursor: "pointer"
              }}
              /* hover: background #2563eb */
            >
              Verify
            </button>
            <button
              type="button"
              onClick={onBackToCreds}
              style={{
                height: "34px", padding: "0 14px",
                background: "transparent", color: "#8b8fa8",
                border: "none", borderRadius: "4px", fontSize: "14px", cursor: "pointer"
              }}
              /* hover: color #e8eaf0; background #1a1d24 */
            >
              Back
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
