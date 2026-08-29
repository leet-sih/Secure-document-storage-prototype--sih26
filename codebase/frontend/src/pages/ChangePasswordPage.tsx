/**
 * ChangePasswordPage.tsx — /change-password (auth; forced on first login)
 *
 * Verifies the current (temporary) password and sets a new one meeting the API policy.
 * On success the user is refreshed (isFirstLogin=false) and sent to "/"; ProtectedRoute
 * then forwards to /mfa-setup if TOTP is not yet enrolled.
 */
import { useState } from "react";
import type { CSSProperties, FormEvent, ReactNode } from "react";
import { useNavigate } from "react-router-dom";

import { useAuthActions } from "../hooks/useAuth";
import { useAuth } from "../store/AuthContext";

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

/** Mirrors backend PasswordChangeSchema so the user sees the rule before submitting. */
function policyError(pw: string): string | null {
  if (pw.length < 12) return "Password must be at least 12 characters.";
  if (new TextEncoder().encode(pw).length > 72) return "Password must be at most 72 bytes.";
  if (!/[A-Z]/.test(pw)) return "Must contain an uppercase letter.";
  if (!/[a-z]/.test(pw)) return "Must contain a lowercase letter.";
  if (!/\d/.test(pw)) return "Must contain a digit.";
  if (!/[!@#$%^&*(),.?":{}|<>]/.test(pw)) return "Must contain a special character.";
  return null;
}

export default function ChangePasswordPage() {
  const navigate = useNavigate();
  const { changePassword } = useAuthActions();
  const { user } = useAuth();

  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const policy = policyError(next);
    if (policy) return setError(policy);
    if (next !== confirm) return setError("New passwords do not match.");

    setError(null);
    setBusy(true);
    try {
      await changePassword(current, next);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not change password");
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
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
      }}
    >
      <form
        onSubmit={submit}
        style={{
          width: 420,
          maxWidth: "100%",
          background: "#111318",
          border: "1px solid #2a2d35",
          borderRadius: 8,
          padding: 24,
          display: "flex",
          flexDirection: "column",
          gap: 16,
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ fontSize: 20, fontWeight: 600, color: "#e8eaf0" }}>Change Password</div>
          {user?.isFirstLogin && (
            <div style={{ fontSize: 13, color: "#8b8fa8" }}>
              You must replace your temporary password before continuing.
            </div>
          )}
        </div>

        {/* Hidden username so password managers associate the new password with this
            account and offer to save/update it. */}
        <input
          type="text"
          name="username"
          autoComplete="username"
          value={user?.email ?? ""}
          readOnly
          hidden
        />
        <Field id="cp-cur" text="Current password">
          <input
            id="cp-cur"
            name="current-password"
            type="password"
            autoComplete="current-password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            style={input}
          />
        </Field>
        <Field id="cp-new" text="New password">
          <input
            id="cp-new"
            name="new-password"
            type="password"
            autoComplete="new-password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            style={input}
          />
        </Field>
        <Field id="cp-cf" text="Confirm new password">
          <input
            id="cp-cf"
            name="confirm-password"
            type="password"
            autoComplete="new-password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            style={input}
          />
        </Field>

        <div style={{ fontSize: 11, color: "#555869", lineHeight: 1.6 }}>
          At least 12 characters with upper &amp; lower case, a digit, and a special character.
        </div>

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
          disabled={busy}
          style={{
            height: 34,
            background: "#3b82f6",
            color: "#fff",
            border: "none",
            borderRadius: 4,
            fontSize: 14,
            fontWeight: 500,
            cursor: "pointer",
            opacity: busy ? 0.6 : 1,
          }}
        >
          {busy ? "Saving…" : "Update Password"}
        </button>
      </form>
    </div>
  );
}

function Field({ id, text, children }: { id: string; text: string; children: ReactNode }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <label htmlFor={id} style={label}>
        {text}
      </label>
      {children}
    </div>
  );
}
