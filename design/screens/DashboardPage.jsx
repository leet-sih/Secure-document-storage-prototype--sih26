// DESIGN REFERENCE — match this layout exactly when building src/pages/DashboardPage.tsx

import { Plus, Search, Filter, FolderOpen, ArrowRight } from 'lucide-react';

/**
 * Props:
 *   canCreateCase   {boolean}  — show the "New Case" button
 *   casesView       {array}    — [{ icon (JSX), number, title, st {color,bg,text}, pr {color,bg,text}, meta, created, open (fn) }]
 *   noCases         {boolean}  — show empty state
 *   mineLabel       {string}   — e.g. "My cases" or "All cases"
 *   mineBg          {string}   — background for the mine toggle button (active: "#1e3a5f", inactive: "transparent")
 *   mineColor       {string}   — color for mine toggle button
 *   onNewCase       {fn}
 *   onSetCaseSearch {fn}
 *   onSetStatusFilter  {fn}
 *   onSetPriorityFilter {fn}
 *   onToggleMine    {fn}
 */
export default function DashboardPage({
  canCreateCase = true,
  casesView = [],
  noCases = false,
  mineLabel = "My cases",
  mineBg = "transparent",
  mineColor = "#8b8fa8",
  onNewCase,
  onSetCaseSearch,
  onSetStatusFilter,
  onSetPriorityFilter,
  onToggleMine,
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>

      {/* Page header */}
      <div style={{ display: "flex", alignItems: "center", gap: "16px", flexWrap: "wrap" }}>
        <h1 style={{ margin: 0, fontSize: "30px", fontWeight: 700, color: "#e8eaf0" }}>Cases</h1>
        {canCreateCase && (
          <button
            type="button"
            onClick={onNewCase}
            style={{
              marginLeft: "auto", height: "34px", padding: "0 14px",
              display: "flex", alignItems: "center", gap: "8px",
              background: "#3b82f6", color: "#ffffff",
              border: "none", borderRadius: "4px",
              fontSize: "14px", fontWeight: 500, cursor: "pointer"
            }}
            /* hover: background #2563eb */
          >
            <Plus size={16} /> New Case
          </button>
        )}
      </div>

      {/* Filters row */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", alignItems: "center" }}>
        {/* Search */}
        <div style={{
          display: "flex", alignItems: "center", gap: "8px",
          height: "34px", padding: "0 10px",
          background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px",
          minWidth: "260px", color: "#555869"
        }}>
          <Search size={16} />
          <input
            placeholder="Search cases…"
            onChange={onSetCaseSearch}
            style={{
              flex: 1, height: "32px", background: "transparent",
              border: "none", color: "#e8eaf0", fontSize: "14px"
            }}
          />
        </div>

        {/* Status filter */}
        <select
          onChange={onSetStatusFilter}
          aria-label="Status filter"
          style={{
            height: "34px", padding: "0 8px",
            background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px",
            color: "#e8eaf0", fontSize: "13px"
          }}
        >
          <option value="All">Status — all</option>
          <option value="OPEN">Open</option>
          <option value="UNDER_INVESTIGATION">Under investigation</option>
          <option value="CLOSED">Closed</option>
          <option value="ARCHIVED">Archived</option>
        </select>

        {/* Priority filter */}
        <select
          onChange={onSetPriorityFilter}
          aria-label="Priority filter"
          style={{
            height: "34px", padding: "0 8px",
            background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px",
            color: "#e8eaf0", fontSize: "13px"
          }}
        >
          <option value="All">Priority — all</option>
          <option value="CRITICAL">Critical</option>
          <option value="HIGH">High</option>
          <option value="NORMAL">Normal</option>
          <option value="LOW">Low</option>
        </select>

        {/* Mine toggle */}
        <button
          type="button"
          onClick={onToggleMine}
          style={{
            height: "34px", padding: "0 12px",
            display: "flex", alignItems: "center", gap: "8px",
            background: mineBg, border: "1px solid #2a2d35", borderRadius: "6px",
            color: mineColor, fontSize: "13px", whiteSpace: "nowrap", cursor: "pointer"
          }}
        >
          <Filter size={14} /> {mineLabel}
        </button>
      </div>

      {/* Case grid */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
        gap: "16px"
      }}>
        {casesView.map((c, i) => (
          <CaseCard key={i} {...c} />
        ))}
      </div>

      {/* Empty state */}
      {noCases && (
        <div style={{
          display: "flex", flexDirection: "column", alignItems: "center",
          gap: "10px", padding: "56px 24px", color: "#555869"
        }}>
          <FolderOpen size={36} />
          <div style={{ fontSize: "14px", color: "#8b8fa8" }}>No cases match these filters.</div>
        </div>
      )}
    </div>
  );
}

/**
 * CaseCard — individual case tile inside the grid.
 *
 * Props match a single entry from casesView:
 *   icon    {JSX}    — category icon
 *   number  {string} — e.g. "CR-2026-0042"
 *   title   {string}
 *   st      {object} — { color, bg, text } for status badge
 *   pr      {object} — { color, bg, text } for priority badge
 *   meta    {string} — short metadata line
 *   created {string} — date string
 *   open    {fn}
 */
export function CaseCard({ icon, number, title, st, pr, meta, created, open }) {
  return (
    <div
      style={{
        background: "#111318", border: "1px solid #2a2d35", borderRadius: "8px",
        padding: "16px", display: "flex", flexDirection: "column", gap: "12px",
        transition: "transform 140ms ease, box-shadow 140ms ease"
      }}
      /* hover: transform translateY(-2px); box-shadow 0 12px 28px rgba(0,0,0,0.45) */
    >
      {/* Icon + case number */}
      <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#8b8fa8" }}>
        {icon}
        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: "13px", color: "#8b8fa8" }}>
          {number}
        </span>
      </div>

      {/* Title */}
      <div style={{
        fontSize: "15px", fontWeight: 500, color: "#e8eaf0",
        lineHeight: 1.45,
        display: "-webkit-box", WebkitLineClamp: 2,
        WebkitBoxOrient: "vertical", overflow: "hidden"
      }}>
        {title}
      </div>

      {/* Badges */}
      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
        <span style={{
          fontSize: "11px", fontWeight: 500, letterSpacing: "0.05em",
          textTransform: "uppercase", padding: "3px 7px", borderRadius: "4px",
          color: st.color, background: st.bg
        }}>{st.text}</span>
        <span style={{
          fontSize: "11px", fontWeight: 500, letterSpacing: "0.05em",
          textTransform: "uppercase", padding: "3px 7px", borderRadius: "4px",
          color: pr.color, background: pr.bg
        }}>{pr.text}</span>
      </div>

      {/* Meta */}
      <div style={{ display: "flex", flexDirection: "column", gap: "3px", fontSize: "12px", color: "#8b8fa8" }}>
        <span>{meta}</span>
        <span style={{ color: "#555869" }}>{created}</span>
      </div>

      {/* View link */}
      <button
        type="button"
        onClick={open}
        style={{
          alignSelf: "flex-start", marginTop: "2px",
          display: "flex", alignItems: "center", gap: "6px",
          background: "none", border: "none", padding: 0,
          color: "#3b82f6", fontSize: "13px", fontWeight: 500, cursor: "pointer"
        }}
        /* hover: color #60a5fa */
      >
        View Case <ArrowRight size={14} />
      </button>
    </div>
  );
}
