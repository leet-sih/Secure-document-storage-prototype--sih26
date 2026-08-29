/**
 * LoginPage.tsx — /login (public)
 *
 * FLOW:
 *   1. Email + password -> useAuthActions.login().
 *   2. If mfaRequired    -> render the 6-digit TOTP step -> verifyMfa().
 *   3. Otherwise a session is established -> navigate("/"); ProtectedRoute forwards a
 *      first-login / not-yet-enrolled user to /change-password or /mfa-setup.
 *
 * UX: generic error text on failure; locked-out message surfaced from the API (423).
 */
import { useState } from "react";
import type { CSSProperties, FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { useAuthActions } from "../hooks/useAuth";

const card: CSSProperties = {
  width: 380,
  maxWidth: "100%",
  background: "#111318",
  border: "1px solid #2a2d35",
  borderRadius: 8,
  padding: 24,
  display: "flex",
  flexDirection: "column",
  gap: 16,
};
const label: CSSProperties = { fontSize: 13, fontWeight: 500, color: "#e8eaf0" };
const input: CSSProperties = {
  height: 36,
  padding: "0 10px",
  fontSize: 14,
  color: "#e8eaf0",
  background: "#1e2028",
  border: "1px solid #2a2d35",
  borderRadius: 6,
};
const primaryBtn: CSSProperties = {
  height: 34,
  background: "#3b82f6",
  color: "#fff",
  border: "none",
  borderRadius: 4,
  fontSize: 14,
  fontWeight: 500,
  cursor: "pointer",
};

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, verifyMfa } = useAuthActions();

  const [step, setStep] = useState<"credentials" | "mfa">("credentials");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [tempToken, setTempToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submitCredentials(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const res = await login(email.trim(), password);
      if (res.mfaRequired && res.tempToken) {
        setTempToken(res.tempToken);
        setStep("mfa");
      } else {
        navigate("/", { replace: true });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid credentials");
    } finally {
      setBusy(false);
    }
  }

  async function submitOtp(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await verifyMfa(tempToken, otp);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid code");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#0a0c10",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 20,
        padding: 24,
      }}
    >
      <div style={{ textAlign: "center" }}>
        <div style={{ fontSize: 24, fontWeight: 700, letterSpacing: "0.18em", color: "#e8eaf0" }}>
          PRAMAAN
        </div>
        <div style={{ fontSize: 13, color: "#8b8fa8" }}>Secure Evidence Vault</div>
      </div>

      {step === "credentials" ? (
        <form style={card} onSubmit={submitCredentials}>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label htmlFor="lg-email" style={label}>
              Email
            </label>
            <input
              id="lg-email"
              name="email"
              type="email"
              autoComplete="username"
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              style={input}
            />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <label htmlFor="lg-pw" style={label}>
              Password
            </label>
            <input
              id="lg-pw"
              name="password"
              type="password"
              autoComplete="current-password"
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={input}
            />
          </div>

          {error && <ErrorBox message={error} />}

          <button type="submit" disabled={busy} style={{ ...primaryBtn, opacity: busy ? 0.6 : 1 }}>
            {busy ? "Signing in…" : "Sign In"}
          </button>
        </form>
      ) : (
        <form style={{ ...card, gap: 8 }} onSubmit={submitOtp}>
          <div style={{ fontSize: 17, fontWeight: 600, color: "#e8eaf0" }}>
            Two-Factor Authentication
          </div>
          <div style={{ fontSize: 13, color: "#8b8fa8", lineHeight: 1.5 }}>
            Enter the 6-digit code from your authenticator app.
          </div>
          <input
            name="otp"
            inputMode="numeric"
            autoComplete="one-time-code"
            autoFocus
            maxLength={6}
            placeholder="––––––"
            value={otp}
            onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
            style={{
              marginTop: 12,
              height: 52,
              textAlign: "center",
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 24,
              letterSpacing: "0.42em",
              textIndent: "0.42em",
              color: "#e8eaf0",
              background: "#1e2028",
              border: "1px solid #2a2d35",
              borderRadius: 6,
            }}
          />
          <div style={{ fontSize: 11, color: "#555869", textAlign: "center", marginTop: 2 }}>
            Code refreshes every 30 seconds
          </div>

          {error && <ErrorBox message={error} />}

          <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            <button
              type="submit"
              disabled={busy || otp.length !== 6}
              style={{ ...primaryBtn, flex: 1, opacity: busy || otp.length !== 6 ? 0.6 : 1 }}
            >
              Verify
            </button>
            <button
              type="button"
              onClick={() => {
                setStep("credentials");
                setOtp("");
                setError(null);
              }}
              style={{
                height: 34,
                padding: "0 14px",
                background: "transparent",
                color: "#8b8fa8",
                border: "none",
                borderRadius: 4,
                fontSize: 14,
                cursor: "pointer",
              }}
            >
              Back
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div
      style={{
        display: "flex",
        gap: 8,
        alignItems: "flex-start",
        background: "#3d1010",
        border: "1px solid #ef4444",
        borderRadius: 6,
        padding: "10px 12px",
      }}
    >
      <div style={{ fontSize: 13, color: "#e8eaf0", lineHeight: 1.45 }}>{message}</div>
    </div>
  );
}
