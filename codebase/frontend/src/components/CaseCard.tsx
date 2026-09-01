import { FolderOpen, ArrowRight } from "lucide-react";

interface BadgeSpec {
  color: string;
  bg: string;
  text: string;
}

interface Props {
  number: string;
  title: string;
  st: BadgeSpec;
  pr: BadgeSpec;
  meta: string;
  created: string;
  open: () => void;
}

export default function CaseCard({ number, title, st, pr, meta, created, open }: Props) {
  return (
    <div
      style={{
        background: "#111318",
        border: "1px solid #2a2d35",
        borderRadius: "8px",
        padding: "16px",
        display: "flex",
        flexDirection: "column",
        gap: "12px",
        transition: "transform 140ms ease, box-shadow 140ms ease",
      }}
    >
      {/* Icon + case number */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <FolderOpen size={16} color="#8b8fa8" />
        <span
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: "13px",
            color: "#8b8fa8",
          }}
        >
          {number}
        </span>
      </div>

      {/* Title */}
      <div
        style={{
          fontSize: "15px",
          fontWeight: 500,
          color: "#e8eaf0",
          lineHeight: 1.45,
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
          overflow: "hidden",
        }}
      >
        {title}
      </div>

      {/* Badges */}
      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
        <span
          style={{
            fontSize: "11px",
            fontWeight: 500,
            letterSpacing: "0.05em",
            textTransform: "uppercase",
            padding: "3px 7px",
            borderRadius: "4px",
            color: st.color,
            background: st.bg,
          }}
        >
          {st.text}
        </span>
        <span
          style={{
            fontSize: "11px",
            fontWeight: 500,
            letterSpacing: "0.05em",
            textTransform: "uppercase",
            padding: "3px 7px",
            borderRadius: "4px",
            color: pr.color,
            background: pr.bg,
          }}
        >
          {pr.text}
        </span>
      </div>

      {/* Meta */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "3px",
          fontSize: "12px",
          color: "#8b8fa8",
        }}
      >
        <span>{meta}</span>
        <span style={{ color: "#555869" }}>{created}</span>
      </div>

      {/* View link */}
      <button
        type="button"
        onClick={open}
        style={{
          alignSelf: "flex-start",
          marginTop: "2px",
          display: "flex",
          alignItems: "center",
          gap: "6px",
          background: "none",
          border: "none",
          padding: 0,
          color: "#3b82f6",
          fontSize: "13px",
          fontWeight: 500,
          cursor: "pointer",
        }}
      >
        View Case <ArrowRight size={14} />
      </button>
    </div>
  );
}
