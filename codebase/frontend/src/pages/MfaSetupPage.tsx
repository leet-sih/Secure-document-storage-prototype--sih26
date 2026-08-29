/**
 * MfaSetupPage.tsx — /mfa-setup (auth, forced when MFA not yet enabled)
 *
 * Loads a pending TOTP secret (GET /auth/mfa/setup), shows the QR + manual key, then
 * confirms a 6-digit code (POST /auth/mfa/confirm). On success the user is refreshed
 * (mfaEnabled=true) and sent to "/".
 */
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { useAuthActions } from "../hooks/useAuth";
import type { MfaSetupResult } from "../types";

function extractSecret(otpauthUri: string): string {
  const match = otpauthUri.match(/[?&]secret=([^&]+)/i);
  return match ? decodeURIComponent(match[1]) : "";
}

export default function MfaSetupPage() {
  const navigate = useNavigate();
  const { setupMfa, confirmMfa } = useAuthActions();

  const [setup, setSetup] = useState<MfaSetupResult | null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setupMfa()
      .then((res) => {
        if (!cancelled) setSetup(res);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not start MFA setup");
      });
    return () => {
      cancelled = true;
    };
    // setupMfa is stable enough for the prototype; run once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function activate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await confirmMfa(code);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invalid code");
    } finally {
      setBusy(false);
    }
  }

  const secret = setup ? extractSecret(setup.otpauthUri) : "";

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#0a0c10",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
      }}
    >
      <div
        style={{
          width: 520,
          maxWidth: "100%",
          background: "#111318",
          border: "1px solid #2a2d35",
          borderRadius: 8,
          padding: 24,
          display: "flex",
          flexDirection: "column",
          gap: 20,
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ fontSize: 20, fontWeight: 600, color: "#e8eaf0" }}>
            Set Up Two-Factor Authentication
          </div>
          <div style={{ fontSize: 13, color: "#8b8fa8" }}>Required before accessing the system.</div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ fontSize: 13, fontWeight: 500, color: "#e8eaf0" }}>
            Step 1 — Scan this QR code
          </div>
          <div style={{ display: "flex", gap: 20, alignItems: "flex-start", flexWrap: "wrap" }}>
            <div
              style={{
                width: 152,
                height: 152,
                flex: "none",
                border: "1px solid #2a2d35",
                borderRadius: 6,
                background: "#fff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                overflow: "hidden",
              }}
            >
              {setup ? (
                <img
                  src={`data:image/png;base64,${setup.qrCodeBase64}`}
                  alt="TOTP QR code"
                  width={152}
                  height={152}
                />
              ) : (
                <span style={{ fontSize: 11, color: "#555869" }}>Loading…</span>
              )}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, minWidth: 200 }}>
              <div style={{ fontSize: 13, color: "#8b8fa8" }}>Or enter this key manually:</div>
              <div
                style={{
                  background: "#1e2028",
                  border: "1px solid #2a2d35",
                  borderRadius: 6,
                  padding: "8px 10px",
                }}
              >
                <code
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 12,
                    color: "#e8eaf0",
                    letterSpacing: "0.04em",
                    wordBreak: "break-all",
                  }}
                >
                  {secret || "…"}
                </code>
              </div>
              <div style={{ fontSize: 11, color: "#555869", lineHeight: 1.6 }}>
                Issuer PRAMAAN · Algorithm SHA-1 · 6 digits · 30s period
              </div>
            </div>
          </div>
        </div>

        <form
          onSubmit={activate}
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 10,
            borderTop: "1px solid #2a2d35",
            paddingTop: 20,
          }}
        >
          <div style={{ fontSize: 13, fontWeight: 500, color: "#e8eaf0" }}>
            Step 2 — Enter the 6-digit code to confirm setup
          </div>
          <input
            name="otp"
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
            placeholder="––––––"
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
            style={{
              width: 220,
              height: 48,
              textAlign: "center",
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 22,
              letterSpacing: "0.4em",
              textIndent: "0.4em",
              color: "#e8eaf0",
              background: "#1e2028",
              border: "1px solid #2a2d35",
              borderRadius: 6,
            }}
          />

          {error && (
            <div
              style={{
                background: "#3d1010",
                border: "1px solid #ef4444",
                borderRadius: 6,
                padding: "10px 12px",
                fontSize: 13,
                color: "#e8eaf0",
              }}
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={busy || code.length !== 6 || !setup}
            style={{
              alignSelf: "flex-start",
              marginTop: 4,
              height: 34,
              padding: "0 16px",
              background: "#3b82f6",
              color: "#fff",
              border: "none",
              borderRadius: 4,
              fontSize: 14,
              fontWeight: 500,
              cursor: "pointer",
              opacity: busy || code.length !== 6 || !setup ? 0.6 : 1,
            }}
          >
            Activate MFA
          </button>
        </form>
      </div>
    </div>
  );
}
