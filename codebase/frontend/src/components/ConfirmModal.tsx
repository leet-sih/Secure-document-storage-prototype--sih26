import { AlertTriangle } from "lucide-react";

interface Props {
  title?: string;
  body: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onClose: () => void;
}

export default function ConfirmModal({
  title = "Are you sure?",
  body,
  confirmLabel = "Confirm",
  onConfirm,
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
          width: "420px",
          maxWidth: "100%",
          background: "#1a1d24",
          border: "1px solid #2a2d35",
          borderRadius: "8px",
          boxShadow: "0 28px 60px rgba(0,0,0,0.6)",
          padding: "22px",
          display: "flex",
          flexDirection: "column",
          gap: "12px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ color: "#ef4444", display: "flex" }}>
            <AlertTriangle size={18} />
          </span>
          <span style={{ fontSize: "17px", fontWeight: 600, color: "#e8eaf0" }}>
            {title}
          </span>
        </div>

        <div style={{ fontSize: "13px", color: "#8b8fa8", lineHeight: 1.6 }}>
          {body}
        </div>

        <div style={{ display: "flex", gap: "8px", marginTop: "6px" }}>
          <button
            type="button"
            onClick={onConfirm}
            style={{
              height: "34px",
              padding: "0 16px",
              background: "#ef4444",
              color: "#ffffff",
              border: "none",
              borderRadius: "4px",
              fontSize: "14px",
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            {confirmLabel}
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
