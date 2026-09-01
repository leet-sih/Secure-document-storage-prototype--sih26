import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Search } from "lucide-react";

import CaseCard from "../components/CaseCard";
import CreateCaseModal from "../components/CreateCaseModal";
import { listCases } from "../lib/caseApi";
import { useAuth } from "../store/AuthContext";
import type { CaseDetail, CasePriority, CaseStatus, CaseSummary } from "../types";

const STATUS_BADGE: Record<CaseStatus, { color: string; bg: string; text: string }> = {
  OPEN:                { color: "#6366f1", bg: "#1e1e4a", text: "Open" },
  UNDER_INVESTIGATION: { color: "#f59e0b", bg: "#3d2c08", text: "Under Investigation" },
  CLOSED:              { color: "#22c55e", bg: "#14391f", text: "Closed" },
  ARCHIVED:            { color: "#555869", bg: "#1e2028", text: "Archived" },
};

const PRIORITY_BADGE: Record<CasePriority, { color: string; bg: string; text: string }> = {
  LOW:      { color: "#555869", bg: "#1e2028", text: "Low" },
  NORMAL:   { color: "#6366f1", bg: "#1e1e4a", text: "Normal" },
  HIGH:     { color: "#f59e0b", bg: "#3d2c08", text: "High" },
  CRITICAL: { color: "#ef4444", bg: "#3d1010", text: "Critical" },
};

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-IN", {
      day: "numeric", month: "short", year: "numeric",
    });
  } catch { return iso; }
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  // Filters
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [page, setPage] = useState(1);
  const LIMIT = 20;

  const canCreate = user?.role === "SUPER_ADMIN" || user?.role === "CASE_OFFICER";

  function load(opts?: { page?: number }) {
    setLoading(true);
    setError("");
    listCases({
      search: search || undefined,
      status: statusFilter || undefined,
      priority: priorityFilter || undefined,
      page: opts?.page ?? page,
      limit: LIMIT,
    })
      .then((res) => {
        setCases(res.items);
        setTotal(res.total);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load cases."))
      .finally(() => setLoading(false));
  }

  // Load on mount and when filters change (debounce search)
  useEffect(() => {
    const t = setTimeout(() => { setPage(1); load({ page: 1 }); }, search ? 350 : 0);
    return () => clearTimeout(t);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, statusFilter, priorityFilter]);

  function handleCreated(c: CaseDetail) {
    setShowCreate(false);
    navigate(`/cases/${c.id}`);
  }

  const totalPages = Math.ceil(total / LIMIT);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Header row */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap" }}>
        <div>
          <h1
            style={{
              margin: 0,
              fontSize: "20px",
              fontWeight: 600,
              color: "#e8eaf0",
            }}
          >
            Cases
          </h1>
          <div style={{ fontSize: "13px", color: "#8b8fa8", marginTop: "2px" }}>
            {loading ? "Loading…" : `${total} case${total !== 1 ? "s" : ""} accessible`}
          </div>
        </div>

        {canCreate && (
          <button
            type="button"
            onClick={() => setShowCreate(true)}
            style={{
              marginLeft: "auto",
              height: "34px",
              padding: "0 14px",
              display: "flex",
              alignItems: "center",
              gap: "8px",
              background: "#3b82f6",
              color: "#fff",
              border: "none",
              borderRadius: "4px",
              fontSize: "14px",
              fontWeight: 500,
              cursor: "pointer",
              flex: "none",
            }}
          >
            <Plus size={16} /> New Case
          </button>
        )}
      </div>

      {/* Filter bar */}
      <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
        <div
          style={{
            flex: 1,
            minWidth: "200px",
            maxWidth: "340px",
            position: "relative",
          }}
        >
          <Search
            size={14}
            color="#555869"
            style={{ position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)" }}
          />
          <input
            placeholder="Search cases…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              width: "100%",
              height: "34px",
              paddingLeft: "32px",
              paddingRight: "10px",
              background: "#1e2028",
              border: "1px solid #2a2d35",
              borderRadius: "6px",
              color: "#e8eaf0",
              fontSize: "13px",
              boxSizing: "border-box",
            }}
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          aria-label="Filter by status"
          style={{
            height: "34px",
            padding: "0 8px",
            background: "#1e2028",
            border: "1px solid #2a2d35",
            borderRadius: "6px",
            color: statusFilter ? "#e8eaf0" : "#8b8fa8",
            fontSize: "13px",
          }}
        >
          <option value="">All statuses</option>
          <option value="OPEN">Open</option>
          <option value="UNDER_INVESTIGATION">Under Investigation</option>
          <option value="CLOSED">Closed</option>
          <option value="ARCHIVED">Archived</option>
        </select>

        <select
          value={priorityFilter}
          onChange={(e) => { setPriorityFilter(e.target.value); setPage(1); }}
          aria-label="Filter by priority"
          style={{
            height: "34px",
            padding: "0 8px",
            background: "#1e2028",
            border: "1px solid #2a2d35",
            borderRadius: "6px",
            color: priorityFilter ? "#e8eaf0" : "#8b8fa8",
            fontSize: "13px",
          }}
        >
          <option value="">All priorities</option>
          <option value="LOW">Low</option>
          <option value="NORMAL">Normal</option>
          <option value="HIGH">High</option>
          <option value="CRITICAL">Critical</option>
        </select>
      </div>

      {/* Error state */}
      {error && (
        <div style={{ fontSize: "13px", color: "#ef4444", padding: "12px 0" }}>{error}</div>
      )}

      {/* Empty state */}
      {!loading && !error && cases.length === 0 && (
        <div
          style={{
            padding: "60px 24px",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "10px",
            color: "#555869",
          }}
        >
          <div style={{ fontSize: "14px", color: "#8b8fa8" }}>
            {search || statusFilter || priorityFilter
              ? "No cases match the current filters."
              : "No cases yet."}
          </div>
          {canCreate && !search && !statusFilter && !priorityFilter && (
            <button
              type="button"
              onClick={() => setShowCreate(true)}
              style={{
                marginTop: "8px",
                height: "34px",
                padding: "0 16px",
                background: "#3b82f6",
                color: "#fff",
                border: "none",
                borderRadius: "4px",
                fontSize: "14px",
                fontWeight: 500,
                cursor: "pointer",
              }}
            >
              Create the first case
            </button>
          )}
        </div>
      )}

      {/* Case grid */}
      {cases.length > 0 && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
            gap: "14px",
          }}
        >
          {cases.map((c) => (
            <CaseCard
              key={c.id}
              number={c.caseNumber}
              title={c.title}
              st={STATUS_BADGE[c.status]}
              pr={PRIORITY_BADGE[c.priority]}
              meta={`${c.documentCount} doc${c.documentCount !== 1 ? "s" : ""} · ${c.memberCount} member${c.memberCount !== 1 ? "s" : ""}`}
              created={formatDate(c.createdAt)}
              open={() => navigate(`/cases/${c.id}`)}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            justifyContent: "center",
            paddingTop: "8px",
          }}
        >
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => { const p = page - 1; setPage(p); load({ page: p }); }}
            style={{
              height: "30px",
              padding: "0 12px",
              background: "#1a1d24",
              border: "1px solid #2a2d35",
              borderRadius: "4px",
              color: page <= 1 ? "#555869" : "#e8eaf0",
              fontSize: "13px",
              cursor: page <= 1 ? "not-allowed" : "pointer",
            }}
          >
            Prev
          </button>
          <span style={{ fontSize: "13px", color: "#8b8fa8" }}>
            {page} / {totalPages}
          </span>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => { const p = page + 1; setPage(p); load({ page: p }); }}
            style={{
              height: "30px",
              padding: "0 12px",
              background: "#1a1d24",
              border: "1px solid #2a2d35",
              borderRadius: "4px",
              color: page >= totalPages ? "#555869" : "#e8eaf0",
              fontSize: "13px",
              cursor: page >= totalPages ? "not-allowed" : "pointer",
            }}
          >
            Next
          </button>
        </div>
      )}

      {showCreate && (
        <CreateCaseModal onCreated={handleCreated} onClose={() => setShowCreate(false)} />
      )}
    </div>
  );
}
