import { ShieldAlert } from "lucide-react";

interface Props {
  label?: string;
  otp: string;
  error: string;
  onOtpChange: (v: string) => void;
  onVerify: () => void;
  onClose: () => void;
}

export default function StepUpMfaModal({
  label = "",
  otp,
  error,
  onOtpChange,
  onVerify,
  onClose,
}: Props) {
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 90,
        background: "rgba(0,0,0,0.6)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px",
        animation: "fadein 120ms ease-out",
      }}
    >
      <div
        style={{
          width: "400px",
          maxWidth: "100%",
          background: "#1a1d24",
          border: "1px solid #2a2d35",
          borderRadius: "8px",
          boxShadow: "0 28px 60px rgba(0,0,0,0.6)",
          padding: "22px",
          display: "flex",
          flexDirection: "column",
          gap: "10px",
        }}
      >
        <div style={{ color: "#f59e0b", display: "flex" }}>
          <ShieldAlert size={20} />
        </div>

        <div
          style={{
            fontSize: "17px",
            fontWeight: 600,
            color: "#e8eaf0",
            marginTop: "2px",
          }}
        >
          Identity Re-Verification Required
        </div>

        <div style={{ fontSize: "13px", color: "#8b8fa8", lineHeight: 1.55 }}>
          This action requires a fresh authentication code.
        </div>

        {label && (
          <div
            style={{
              fontSize: "12px",
              fontFamily: "'JetBrains Mono', monospace",
              color: "#555869",
              background: "#14161c",
              border: "1px solid #2a2d35",
              borderRadius: "6px",
              padding: "8px 10px",
              wordBreak: "break-word",
            }}
          >
            {label}
          </div>
        )}

        <input
          inputMode="numeric"
          maxLength={6}
          placeholder="––––––"
          value={otp}
          onChange={(e) => onOtpChange(e.target.value.replace(/\D/g, ""))}
          style={{
            marginTop: "6px",
            height: "48px",
            textAlign: "center",
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: "22px",
            letterSpacing: "0.4em",
            textIndent: "0.4em",
            color: "#e8eaf0",
            background: "#1e2028",
            border: "1px solid #2a2d35",
            borderRadius: "6px",
          }}
        />

        {error && (
          <div style={{ fontSize: "12px", color: "#ef4444" }}>{error}</div>
        )}

        <div style={{ display: "flex", gap: "8px", marginTop: "8px" }}>
          <button
            type="button"
            onClick={onVerify}
            style={{
              flex: 1,
              height: "34px",
              background: "#3b82f6",
              color: "#ffffff",
              border: "none",
              borderRadius: "4px",
              fontSize: "14px",
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            Verify
          </button>
          <button
            type="button"
            onClick={onClose}
            style={{
              height: "34px",
              padding: "0 14px",
              background: "transparent",
              border: "1px solid #2a2d35",
              borderRadius: "4px",
              color: "#8b8fa8",
              fontSize: "14px",
              cursor: "pointer",
            }}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
