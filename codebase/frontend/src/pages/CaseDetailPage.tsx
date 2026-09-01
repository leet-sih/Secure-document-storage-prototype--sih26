import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeftRight,
  BadgeCheck,
  Clock,
  Download,
  FileText,
  LayoutDashboard,
  MoreVertical,
  PenLine,
  Plus,
  ShieldCheck,
  Trash2,
  Users,
} from "lucide-react";
import type { ReactNode } from "react";

import AddMemberModal from "../components/AddMemberModal";
import ConfirmModal from "../components/ConfirmModal";
import DocumentDetailPanel from "../components/DocumentDetailPanel";
import DocumentUploader from "../components/DocumentUploader";
import OcrApprovalModal from "../components/OcrApprovalModal";
import TransferCaseModal from "../components/TransferCaseModal";
import { getCase, getTimeline, patchCase, removeMember } from "../lib/caseApi";
import { deleteDocument, downloadDocument, fetchCaseDocs, generateOcr } from "../lib/documentApi";
import { useAuth } from "../store/AuthContext";
import type {
  CaseDetail,
  CaseMember,
  CaseMemberRole,
  CasePriority,
  CaseStatus,
  DocumentMeta,
  TimelineEvent,
} from "../types";

// ── OCR helpers ───────────────────────────────────────────────────────────────

const OCR_EXT = new Set([".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif"]);

function isOcrSupported(filename: string): boolean {
  const dot = filename.lastIndexOf(".");
  return dot >= 0 && OCR_EXT.has(filename.slice(dot).toLowerCase());
}

function OcrStatusBadge({ doc }: { doc: Pick<DocumentMeta, "ocrStatus" | "ocrConfidence" | "ocrDetail"> }) {
  const { ocrStatus, ocrConfidence, ocrDetail } = doc;
  if (!ocrStatus || ocrStatus === "NOT_APPLICABLE" || ocrStatus === "PENDING") return null;

  if (ocrStatus === "FAILED") {
    const pct = ocrConfidence != null ? Math.round(ocrConfidence * 100) : null;
    const label = pct != null ? `OCR Failed · ${pct}%` : "OCR Failed";
    return (
      <span
        title={ocrDetail ?? undefined}
        style={{
          display: "inline-block",
          marginLeft: "6px",
          fontSize: "10px",
          fontWeight: 500,
          padding: "1px 5px",
          borderRadius: "3px",
          color: "#ef4444",
          background: "#3d1010",
          verticalAlign: "middle",
          cursor: ocrDetail ? "help" : "default",
          textDecoration: ocrDetail ? "underline dotted" : "none",
        }}
      >
        {label}
      </span>
    );
  }

  if (ocrStatus === "AWAITING_APPROVAL") {
    const pct = ocrConfidence != null ? Math.round(ocrConfidence * 100) : null;
    const isLow = ocrConfidence != null && ocrConfidence < 0.6;
    const label = isLow && pct != null ? `Pending Review · ${pct}%` : "Pending Review";
    return (
      <span
        title={isLow ? (ocrDetail ?? "Low confidence — review carefully") : undefined}
        style={{
          display: "inline-block",
          marginLeft: "6px",
          fontSize: "10px",
          fontWeight: 500,
          padding: "1px 5px",
          borderRadius: "3px",
          color: isLow ? "#fb923c" : "#f59e0b",
          background: "#3d2c08",
          verticalAlign: "middle",
          cursor: isLow ? "help" : "default",
          textDecoration: isLow ? "underline dotted" : "none",
        }}
      >
        {label}
      </span>
    );
  }

  if (ocrStatus === "DONE") {
    return (
      <span
        style={{
          display: "inline-block",
          marginLeft: "6px",
          fontSize: "10px",
          fontWeight: 500,
          padding: "1px 5px",
          borderRadius: "3px",
          color: "#22c55e",
          background: "#14391f",
          verticalAlign: "middle",
        }}
      >
        OCR Done
      </span>
    );
  }

  return null;
}

// ── Design tokens ──────────────────────────────────────────────────────────────

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

const ROLE_BADGE: Record<CaseMemberRole, { color: string; bg: string; text: string }> = {
  CASE_OFFICER: { color: "#6366f1", bg: "#1e1e4a", text: "Case Officer" },
  INVESTIGATOR: { color: "#f59e0b", bg: "#3d2c08", text: "Investigator" },
  PROSECUTOR:   { color: "#22c55e", bg: "#14391f", text: "Prosecutor" },
  VIEWER:       { color: "#555869", bg: "#1e2028", text: "Viewer" },
};

const ROLE_LABEL: Record<string, string> = {
  SUPER_ADMIN: "System Admin", CASE_OFFICER: "Case Officer",
  INVESTIGATOR: "Investigator", PROSECUTOR: "Prosecutor",
  AUDITOR: "Auditor", VIEWER: "Viewer",
};

function eventColor(eventType: string): string {
  if (/CREATED|ADDED|VERIFIED|CONFIRMED/.test(eventType)) return "#22c55e";
  if (/DELETED|REMOVED|FAILED|LOCKED/.test(eventType)) return "#ef4444";
  if (/TRANSFERRED|CHANGED|SHARED|REVOKED/.test(eventType)) return "#fb923c";
  return "#f59e0b";
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-IN", {
      day: "numeric", month: "short", year: "numeric",
    });
  } catch { return iso; }
}

function formatTs(iso: string): string {
  try {
    return new Date(iso).toLocaleString("en-IN", {
      day: "numeric", month: "short", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  } catch { return iso; }
}

// ── Subcomponent: OverviewTab ──────────────────────────────────────────────────

interface OverviewTabProps {
  detail: CaseDetail;
  onSaved: (d: CaseDetail) => void;
}

function OverviewTab({ detail, onSaved }: OverviewTabProps) {
  const { user } = useAuth();
  const [status, setStatus] = useState(detail.status);
  const [priority, setPriority] = useState(detail.priority);
  const [description, setDescription] = useState(detail.description ?? "");
  const [savedAt, setSavedAt] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const canEdit =
    user?.role === "SUPER_ADMIN" || detail.leadOfficer?.id === user?.id;

  async function handleSave() {
    setLoading(true);
    setError("");
    setSavedAt("");
    try {
      const updated = await patchCase(detail.id, { status, priority, description });
      onSaved(updated);
      setSavedAt(`Saved at ${new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      style={{
        background: "#111318",
        border: "1px solid #2a2d35",
        borderRadius: "8px",
        padding: "20px",
        display: "flex",
        flexDirection: "column",
        gap: "18px",
        maxWidth: "720px",
      }}
    >
      <div
        className="overview-grid"
        style={{
          display: "grid",
          gridTemplateColumns: "160px 1fr",
          gap: "14px 20px",
          alignItems: "center",
        }}
      >
        <span style={{ fontSize: "13px", color: "#8b8fa8" }}>Case number</span>
        <span
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: "13px",
            color: "#e8eaf0",
          }}
        >
          {detail.caseNumber}
        </span>

        <span style={{ fontSize: "13px", color: "#8b8fa8" }}>Title</span>
        <span style={{ fontSize: "13px", color: "#e8eaf0" }}>{detail.title}</span>

        <span style={{ fontSize: "13px", color: "#8b8fa8" }}>Status</span>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value as CaseStatus)}
          disabled={!canEdit}
          aria-label="Case status"
          style={{
            height: "34px",
            padding: "0 8px",
            background: "#1e2028",
            border: "1px solid #2a2d35",
            borderRadius: "6px",
            color: "#e8eaf0",
            fontSize: "13px",
            maxWidth: "260px",
          }}
        >
          <option value="OPEN">Open</option>
          <option value="UNDER_INVESTIGATION">Under investigation</option>
          <option value="CLOSED">Closed</option>
          <option value="ARCHIVED">Archived</option>
        </select>

        <span style={{ fontSize: "13px", color: "#8b8fa8" }}>Priority</span>
        <select
          value={priority}
          onChange={(e) => setPriority(e.target.value as CasePriority)}
          disabled={!canEdit}
          aria-label="Case priority"
          style={{
            height: "34px",
            padding: "0 8px",
            background: "#1e2028",
            border: "1px solid #2a2d35",
            borderRadius: "6px",
            color: "#e8eaf0",
            fontSize: "13px",
            maxWidth: "260px",
          }}
        >
          <option value="LOW">Low</option>
          <option value="NORMAL">Normal</option>
          <option value="HIGH">High</option>
          <option value="CRITICAL">Critical</option>
        </select>

        <span
          style={{
            fontSize: "13px",
            color: "#8b8fa8",
            alignSelf: "flex-start",
            paddingTop: "8px",
          }}
        >
          Description
        </span>
        <textarea
          rows={4}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          disabled={!canEdit}
          style={{
            padding: "10px",
            background: "#1e2028",
            border: "1px solid #2a2d35",
            borderRadius: "6px",
            color: "#e8eaf0",
            fontSize: "13px",
            lineHeight: 1.55,
            resize: "vertical",
          }}
        />

        <span style={{ fontSize: "13px", color: "#8b8fa8" }}>Department</span>
        <span style={{ fontSize: "13px", color: "#e8eaf0" }}>
          {detail.department.name}
        </span>

        <span style={{ fontSize: "13px", color: "#8b8fa8" }}>Lead officer</span>
        <span style={{ fontSize: "13px", color: "#e8eaf0" }}>
          {detail.leadOfficer?.fullName ?? "—"}
        </span>

        <span style={{ fontSize: "13px", color: "#8b8fa8" }}>Created by</span>
        <span style={{ fontSize: "13px", color: "#e8eaf0" }}>
          {detail.createdBy.fullName}
        </span>

        <span style={{ fontSize: "13px", color: "#8b8fa8" }}>Created at</span>
        <span
          style={{ fontSize: "13px", color: "#8b8fa8" }}
          title={detail.createdAt}
        >
          {formatDate(detail.createdAt)}
        </span>
      </div>

      {error && <div style={{ fontSize: "13px", color: "#ef4444" }}>{error}</div>}

      {canEdit && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            borderTop: "1px solid #2a2d35",
            paddingTop: "16px",
          }}
        >
          <button
            type="button"
            onClick={handleSave}
            disabled={loading}
            style={{
              height: "34px",
              padding: "0 16px",
              background: "#3b82f6",
              color: "#ffffff",
              border: "none",
              borderRadius: "4px",
              fontSize: "14px",
              fontWeight: 500,
              cursor: loading ? "not-allowed" : "pointer",
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? "Saving…" : "Save Changes"}
          </button>
          {savedAt && (
            <span style={{ fontSize: "12px", color: "#22c55e" }}>{savedAt}</span>
          )}
        </div>
      )}
    </div>
  );
}

// ── Subcomponent: MembersTab ───────────────────────────────────────────────────

interface MembersTabProps {
  detail: CaseDetail;
  onMemberAdded: (m: CaseMember) => void;
  onMemberRemoved: (userId: string) => void;
}

function MembersTab({ detail, onMemberAdded, onMemberRemoved }: MembersTabProps) {
  const { user } = useAuth();
  const [showAdd, setShowAdd] = useState(false);
  const [confirmRemove, setConfirmRemove] = useState<CaseMember | null>(null);
  const [removing, setRemoving] = useState(false);

  const canManage =
    user?.role === "SUPER_ADMIN" || detail.leadOfficer?.id === user?.id;

  const existingIds = new Set(detail.members.map((m) => m.userId));

  async function handleRemove() {
    if (!confirmRemove) return;
    setRemoving(true);
    try {
      await removeMember(detail.id, confirmRemove.userId);
      onMemberRemoved(confirmRemove.userId);
    } catch {
      /* error silently ignored; could add toast */
    } finally {
      setRemoving(false);
      setConfirmRemove(null);
    }
  }

  return (
    <>
      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        {canManage && (
          <div style={{ display: "flex" }}>
            <button
              type="button"
              onClick={() => setShowAdd(true)}
              style={{
                marginLeft: "auto",
                height: "34px",
                padding: "0 14px",
                display: "flex",
                alignItems: "center",
                gap: "8px",
                background: "#1a1d24",
                border: "1px solid #2a2d35",
                borderRadius: "4px",
                color: "#e8eaf0",
                fontSize: "14px",
                whiteSpace: "nowrap",
                cursor: "pointer",
              }}
            >
              <Plus size={16} /> Add Member
            </button>
          </div>
        )}

        <div
          style={{
            background: "#111318",
            border: "1px solid #2a2d35",
            borderRadius: "8px",
            overflow: "hidden",
          }}
        >
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                minWidth: "700px",
                borderCollapse: "collapse",
              }}
            >
              <thead>
                <tr style={{ background: "#14161c" }}>
                  {["NAME", "ROLE", "DEPARTMENT", "ADDED", "ACTIONS"].map((h, i) => (
                    <th
                      key={h}
                      style={{
                        textAlign: i === 4 ? "right" : "left",
                        padding: i === 0 || i === 4 ? "10px 14px" : "10px 12px",
                        borderBottom: "1px solid #2a2d35",
                        fontSize: "12px",
                        fontWeight: 500,
                        color: "#8b8fa8",
                        letterSpacing: "0.04em",
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {detail.members.length === 0 && (
                  <tr>
                    <td
                      colSpan={5}
                      style={{
                        padding: "24px",
                        textAlign: "center",
                        fontSize: "13px",
                        color: "#555869",
                        borderBottom: "1px solid #1e2028",
                      }}
                    >
                      No members on this case yet.
                    </td>
                  </tr>
                )}
                {detail.members.map((m) => {
                  const rb = ROLE_BADGE[m.role] ?? { color: "#8b8fa8", bg: "#1e2028", text: m.role };
                  const isLead = detail.leadOfficer?.id === m.userId;
                  const isSelf = user?.id === m.userId;
                  const canRemove = canManage && !isLead && !isSelf;

                  return (
                    <tr key={m.userId}>
                      <td
                        style={{
                          padding: "12px 14px",
                          borderBottom: "1px solid #1e2028",
                          fontSize: "13px",
                          color: "#e8eaf0",
                        }}
                      >
                        {m.fullName}
                        {isLead && (
                          <span
                            style={{
                              marginLeft: "6px",
                              fontSize: "10px",
                              color: "#3b82f6",
                            }}
                          >
                            (lead)
                          </span>
                        )}
                      </td>
                      <td
                        style={{
                          padding: "12px",
                          borderBottom: "1px solid #1e2028",
                        }}
                      >
                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "5px",
                            fontSize: "11px",
                            fontWeight: 500,
                            letterSpacing: "0.05em",
                            padding: "3px 7px",
                            borderRadius: "4px",
                            color: rb.color,
                            background: rb.bg,
                          }}
                        >
                          <BadgeCheck size={14} /> {rb.text}
                        </span>
                      </td>
                      <td
                        style={{
                          padding: "12px",
                          borderBottom: "1px solid #1e2028",
                          fontSize: "13px",
                          color: "#8b8fa8",
                        }}
                      >
                        {m.department}
                      </td>
                      <td
                        style={{
                          padding: "12px",
                          borderBottom: "1px solid #1e2028",
                          fontSize: "13px",
                          color: "#8b8fa8",
                        }}
                      >
                        {formatDate(m.addedAt)}
                      </td>
                      <td
                        style={{
                          padding: "8px 14px",
                          borderBottom: "1px solid #1e2028",
                          textAlign: "right",
                        }}
                      >
                        {canRemove && (
                          <button
                            type="button"
                            onClick={() => setConfirmRemove(m)}
                            style={{
                              height: "28px",
                              padding: "0 10px",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "6px",
                              background: "transparent",
                              border: "1px solid #2a2d35",
                              borderRadius: "4px",
                              color: "#8b8fa8",
                              fontSize: "12px",
                              cursor: "pointer",
                            }}
                          >
                            <Trash2 size={14} /> Remove
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {showAdd && (
        <AddMemberModal
          caseId={detail.id}
          existingMemberIds={existingIds}
          onAdded={(m) => {
            onMemberAdded(m);
            setShowAdd(false);
          }}
          onClose={() => setShowAdd(false)}
        />
      )}

      {confirmRemove && (
        <ConfirmModal
          title="Remove member"
          body={`Remove ${confirmRemove.fullName} from this case? They will lose access immediately.`}
          confirmLabel={removing ? "Removing…" : "Remove"}
          onConfirm={handleRemove}
          onClose={() => setConfirmRemove(null)}
        />
      )}
    </>
  );
}

// ── Subcomponent: ActivityTab ──────────────────────────────────────────────────

interface ActivityTabProps {
  caseId: string;
}

function ActivityTab({ caseId }: ActivityTabProps) {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [nextBeforeId, setNextBeforeId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getTimeline(caseId)
      .then((res) => {
        setEvents(res.events);
        setNextBeforeId(res.nextBeforeId);
      })
      .catch(() => setEvents([]))
      .finally(() => setLoading(false));
  // Run once on mount.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function loadMore() {
    if (!nextBeforeId) return;
    getTimeline(caseId, 50, nextBeforeId).then((res) => {
      setEvents((prev) => [...prev, ...res.events]);
      setNextBeforeId(res.nextBeforeId);
    });
  }

  return (
    <div
      style={{
        background: "#111318",
        border: "1px solid #2a2d35",
        borderRadius: "8px",
        padding: "8px 4px",
      }}
    >
      {loading && (
        <div
          style={{
            padding: "24px",
            fontSize: "13px",
            color: "#555869",
            textAlign: "center",
          }}
        >
          Loading activity…
        </div>
      )}

      {!loading && events.length === 0 && (
        <div
          style={{
            padding: "24px",
            fontSize: "13px",
            color: "#555869",
            textAlign: "center",
          }}
        >
          No activity yet.
        </div>
      )}

      {[...events].reverse().map((e) => {
        const color = eventColor(e.eventType);
        const actor = e.actor;
        return (
          <div
            key={e.id}
            style={{
              display: "flex",
              gap: "12px",
              padding: "14px 16px",
              borderBottom: "1px solid #1e2028",
            }}
          >
            {/* Event icon chip */}
            <div
              style={{
                width: "26px",
                height: "26px",
                flex: "none",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                borderRadius: "6px",
                background: "rgba(255,255,255,0.04)",
                color,
              }}
            >
              <Clock size={14} />
            </div>

            {/* Text block */}
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "3px",
                minWidth: 0,
              }}
            >
              <div style={{ fontSize: "13px", color: "#e8eaf0" }}>
                {actor ? (
                  <>
                    {actor.fullName}{" "}
                    <span style={{ color: "#8b8fa8" }}>
                      ({ROLE_LABEL[actor.role] ?? actor.role})
                    </span>
                  </>
                ) : (
                  <span style={{ color: "#8b8fa8" }}>System</span>
                )}
              </div>
              <div style={{ fontSize: "12px", color: "#8b8fa8" }}>
                <span
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    color,
                  }}
                >
                  {e.eventType}
                </span>
                {e.targetType && ` · ${e.targetType}`}
              </div>
              <div
                style={{
                  fontSize: "11px",
                  fontFamily: "'JetBrains Mono', monospace",
                  color: "#555869",
                }}
              >
                {formatTs(e.createdAt)}
              </div>
            </div>
          </div>
        );
      })}

      {nextBeforeId && (
        <div style={{ display: "flex", justifyContent: "center", padding: "14px" }}>
          <button
            type="button"
            onClick={loadMore}
            style={{
              height: "30px",
              padding: "0 14px",
              background: "#1a1d24",
              border: "1px solid #2a2d35",
              borderRadius: "4px",
              color: "#8b8fa8",
              fontSize: "13px",
              cursor: "pointer",
            }}
          >
            Load more
          </button>
        </div>
      )}
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────

type Tab = "overview" | "documents" | "members" | "activity";

export default function CaseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<Tab>("documents");
  const [showTransfer, setShowTransfer] = useState(false);
  const [docs, setDocs] = useState<DocumentMeta[]>([]);
  const [docsLoading, setDocsLoading] = useState(false);
  const [ocrDoc, setOcrDoc] = useState<DocumentMeta | null>(null);
  const [ocrGenerating, setOcrGenerating] = useState<string | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<DocumentMeta | null>(null);
  const [openSignForm, setOpenSignForm] = useState(false);
  const [menuDocId, setMenuDocId] = useState<string | null>(null);
  const [confirmDeleteDoc, setConfirmDeleteDoc] = useState<DocumentMeta | null>(null);

  useEffect(() => {
    if (!id) return;
    getCase(id)
      .then(setDetail)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load case."))
      .finally(() => setLoading(false));
    fetchDocs();
  // Run once when id changes.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  function fetchDocs() {
    if (!id) return;
    setDocsLoading(true);
    fetchCaseDocs(id)
      .then(setDocs)
      .catch(() => {/* non-fatal; docs list stays empty */})
      .finally(() => setDocsLoading(false));
  }

  function updateDoc(updated: DocumentMeta) {
    setDocs((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
  }

  async function handleGenerateOcr(doc: DocumentMeta, force = false) {
    setOcrGenerating(doc.id);
    try {
      const updated = await generateOcr(doc.id, force);
      updateDoc(updated);
      if (updated.ocrStatus === "AWAITING_APPROVAL") setOcrDoc(updated);
    } catch {
      /* non-fatal — status unchanged in UI */
    } finally {
      setOcrGenerating(null);
    }
  }

  async function handleDeleteDoc(doc: DocumentMeta) {
    try {
      await deleteDocument(doc.id);
      setDocs((prev) => prev.filter((d) => d.id !== doc.id));
      if (selectedDoc?.id === doc.id) setSelectedDoc(null);
    } catch {
      /* non-fatal — show no toast in prototype */
    }
  }

  if (loading) {
    return (
      <div style={{ padding: "40px", fontSize: "13px", color: "#555869" }}>
        Loading case…
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div style={{ padding: "40px", fontSize: "13px", color: "#ef4444" }}>
        {error || "Case not found."}
      </div>
    );
  }

  const st = STATUS_BADGE[detail.status];
  const pr = PRIORITY_BADGE[detail.priority];

  const canTransfer =
    user?.role === "SUPER_ADMIN" || detail.leadOfficer?.id === user?.id;

  type TabSpec = { id: Tab; label: string; icon: ReactNode };

  const tabs: TabSpec[] = [
    { id: "documents",  label: "Documents",  icon: <FileText size={15} /> },
    { id: "members",    label: "Members",    icon: <Users size={15} /> },
    { id: "overview",   label: "Overview",   icon: <LayoutDashboard size={15} /> },
    { id: "activity",   label: "Activity",   icon: <Clock size={15} /> },
  ];

  function handleMemberAdded(m: CaseMember) {
    setDetail((prev) =>
      prev ? { ...prev, members: [...prev.members, m] } : prev
    );
  }

  function handleMemberRemoved(userId: string) {
    setDetail((prev) =>
      prev
        ? { ...prev, members: prev.members.filter((m) => m.userId !== userId) }
        : prev
    );
  }

  return (
    <>
      <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
        {/* Breadcrumb */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            fontSize: "12px",
            color: "#8b8fa8",
          }}
        >
          <button
            type="button"
            onClick={() => navigate("/cases")}
            style={{
              background: "none",
              border: "none",
              padding: 0,
              color: "#8b8fa8",
              fontSize: "12px",
              cursor: "pointer",
            }}
          >
            Cases
          </button>
          <span style={{ color: "#555869" }}>/</span>
          <span
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              color: "#e8eaf0",
            }}
          >
            {detail.caseNumber}
          </span>
        </div>

        {/* Case header */}
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          <h1
            style={{
              margin: 0,
              fontSize: "24px",
              fontWeight: 600,
              color: "#e8eaf0",
              lineHeight: 1.35,
              maxWidth: "780px",
            }}
          >
            {detail.title}
          </h1>

          <div
            style={{
              display: "flex",
              gap: "8px",
              alignItems: "center",
              flexWrap: "wrap",
            }}
          >
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
            <span style={{ fontSize: "12px", color: "#8b8fa8" }}>
              {detail.documentSummary.total} document
              {detail.documentSummary.total !== 1 ? "s" : ""} ·{" "}
              {detail.members.length} member
              {detail.members.length !== 1 ? "s" : ""} · created{" "}
              {formatDate(detail.createdAt)}
            </span>
            {canTransfer && detail.status !== "ARCHIVED" && detail.status !== "CLOSED" && (
              <button
                type="button"
                onClick={() => setShowTransfer(true)}
                style={{
                  marginLeft: "auto",
                  height: "30px",
                  padding: "0 12px",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  background: "#1a1d24",
                  border: "1px solid #2a2d35",
                  borderRadius: "4px",
                  color: "#8b8fa8",
                  fontSize: "12px",
                  whiteSpace: "nowrap",
                  cursor: "pointer",
                  flex: "none",
                }}
              >
                <ArrowLeftRight size={13} /> Transfer
              </button>
            )}
          </div>
        </div>

        {/* Tab bar */}
        <div
          className="no-scrollbar"
          style={{
            display: "flex",
            gap: "4px",
            borderBottom: "1px solid #2a2d35",
            overflowX: "auto",
          }}
        >
          {tabs.map((t) => {
            const active = activeTab === t.id;
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => {
                  setActiveTab(t.id);
                  if (t.id === "documents") fetchDocs();
                }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  height: "38px",
                  padding: "0 12px",
                  background: "transparent",
                  border: "none",
                  borderBottom: `2px solid ${active ? "#3b82f6" : "transparent"}`,
                  color: active ? "#e8eaf0" : "#8b8fa8",
                  fontSize: "14px",
                  cursor: "pointer",
                }}
              >
                {t.icon} {t.label}
              </button>
            );
          })}
        </div>

        {/* Tab content */}
        {activeTab === "overview" && (
          <OverviewTab detail={detail} onSaved={setDetail} />
        )}

        {activeTab === "documents" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {(user?.role === "SUPER_ADMIN" || user?.role === "CASE_OFFICER") && (
              <DocumentUploader
                caseId={detail.id}
                onUploaded={(doc) => {
                  setDocs((prev) => [doc, ...prev]);
                }}
              />
            )}
            <div
              style={{
                background: "#111318",
                border: "1px solid #2a2d35",
                borderRadius: "8px",
                overflow: "hidden",
              }}
            >
              {docsLoading ? (
                <div style={{ padding: "24px", fontSize: "13px", color: "#555869" }}>
                  Loading…
                </div>
              ) : docs.length === 0 ? (
                <div
                  style={{
                    padding: "40px 24px",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: "10px",
                    color: "#555869",
                  }}
                >
                  <FileText size={32} />
                  <div style={{ fontSize: "13px", color: "#8b8fa8" }}>No documents yet.</div>
                </div>
              ) : (
                <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", minWidth: "640px", borderCollapse: "collapse", fontSize: "13px" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid #2a2d35" }}>
                      {["Filename", "Type", "Size", "Uploaded", ""].map((h, i) => (
                        <th
                          key={i}
                          style={{
                            padding: "10px 16px",
                            textAlign: i === 4 ? "right" : "left",
                            color: "#555869",
                            fontWeight: 500,
                          }}
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {docs.map((d) => (
                      <tr
                        key={d.id}
                        style={{ borderBottom: "1px solid #1e2028" }}
                      >
                        <td style={{ padding: "10px 16px", color: "#e8eaf0", fontFamily: "monospace", fontSize: "12px" }}>
                          {d.filename}
                          <OcrStatusBadge doc={d} />
                        </td>
                        <td style={{ padding: "10px 16px", color: "#8b8fa8" }}>
                          {d.docType.replace(/_/g, " ")}
                        </td>
                        <td style={{ padding: "10px 16px", color: "#8b8fa8" }}>
                          {d.fileSizeBytes < 1024 * 1024
                            ? `${(d.fileSizeBytes / 1024).toFixed(1)} KB`
                            : `${(d.fileSizeBytes / 1024 / 1024).toFixed(1)} MB`}
                        </td>
                        <td style={{ padding: "10px 16px", color: "#555869" }}>
                          {new Date(d.createdAt).toLocaleDateString()}
                        </td>
                        <td style={{ padding: "6px 16px", textAlign: "right" }}>
                          <div style={{ display: "inline-flex", alignItems: "center", gap: "6px", flexWrap: "wrap", justifyContent: "flex-end" }}>
                            {/* Generate OCR — first-time scan */}
                            {d.ocrStatus === "NOT_APPLICABLE" && isOcrSupported(d.filename) && (
                              <button
                                type="button"
                                disabled={ocrGenerating === d.id}
                                onClick={() => handleGenerateOcr(d)}
                                style={{
                                  height: "28px",
                                  padding: "0 10px",
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: "5px",
                                  background: "transparent",
                                  border: "1px solid #2a2d35",
                                  borderRadius: "4px",
                                  color: "#8b8fa8",
                                  fontSize: "12px",
                                  cursor: ocrGenerating === d.id ? "not-allowed" : "pointer",
                                  opacity: ocrGenerating === d.id ? 0.6 : 1,
                                }}
                              >
                                {ocrGenerating === d.id ? "Scanning…" : "Generate OCR"}
                              </button>
                            )}
                            {/* Review OCR — awaiting approval */}
                            {d.ocrStatus === "AWAITING_APPROVAL" && (
                              <button
                                type="button"
                                onClick={() => setOcrDoc(d)}
                                style={{
                                  height: "28px",
                                  padding: "0 10px",
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: "5px",
                                  background: "#3d2c08",
                                  border: "1px solid #f59e0b",
                                  borderRadius: "4px",
                                  color: "#f59e0b",
                                  fontSize: "12px",
                                  cursor: "pointer",
                                }}
                              >
                                Review OCR
                              </button>
                            )}
                            {/* View OCR — approved */}
                            {d.ocrStatus === "DONE" && (
                              <button
                                type="button"
                                onClick={() => setOcrDoc(d)}
                                style={{
                                  height: "28px",
                                  padding: "0 10px",
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: "5px",
                                  background: "#14391f",
                                  border: "1px solid #22c55e",
                                  borderRadius: "4px",
                                  color: "#22c55e",
                                  fontSize: "12px",
                                  cursor: "pointer",
                                }}
                              >
                                View OCR
                              </button>
                            )}
                            {/* Re-OCR — for failed / done / pending-review docs */}
                            {(d.ocrStatus === "FAILED" || d.ocrStatus === "DONE" || d.ocrStatus === "AWAITING_APPROVAL") && isOcrSupported(d.filename) && (
                              <button
                                type="button"
                                disabled={ocrGenerating === d.id}
                                onClick={() => handleGenerateOcr(d, true)}
                                style={{
                                  height: "28px",
                                  padding: "0 10px",
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: "5px",
                                  background: "transparent",
                                  border: "1px solid #2a2d35",
                                  borderRadius: "4px",
                                  color: "#555869",
                                  fontSize: "12px",
                                  cursor: ocrGenerating === d.id ? "not-allowed" : "pointer",
                                  opacity: ocrGenerating === d.id ? 0.6 : 1,
                                }}
                              >
                                {ocrGenerating === d.id ? "Scanning…" : "Re-OCR"}
                              </button>
                            )}
                            <button
                              type="button"
                              onClick={() => void downloadDocument(d.id, d.filename)}
                              title="Download"
                              style={{ height: "28px", width: "28px", display: "inline-flex", alignItems: "center", justifyContent: "center", background: "transparent", border: "1px solid #2a2d35", borderRadius: "4px", color: "#8b8fa8", cursor: "pointer" }}
                            >
                              <Download size={13} />
                            </button>
                            <button
                              type="button"
                              onClick={(e) => { e.stopPropagation(); setSelectedDoc(d); setOpenSignForm(true); }}
                              title="Sign document"
                              style={{ height: "28px", width: "28px", display: "inline-flex", alignItems: "center", justifyContent: "center", background: "transparent", border: "1px solid #2a2d35", borderRadius: "4px", color: "#8b8fa8", cursor: "pointer" }}
                            >
                              <PenLine size={13} />
                            </button>
                            {/* Three-dot expandable menu */}
                            <div style={{ position: "relative" }}>
                              <button
                                type="button"
                                onClick={(e) => { e.stopPropagation(); setMenuDocId(menuDocId === d.id ? null : d.id); }}
                                title="More actions"
                                style={{ height: "28px", width: "28px", display: "inline-flex", alignItems: "center", justifyContent: "center", background: menuDocId === d.id ? "#1e2028" : "transparent", border: "1px solid #2a2d35", borderRadius: "4px", color: "#8b8fa8", cursor: "pointer" }}
                              >
                                <MoreVertical size={13} />
                              </button>
                              {menuDocId === d.id && (
                                <>
                                  <div style={{ position: "fixed", inset: 0, zIndex: 49 }} onClick={() => setMenuDocId(null)} />
                                  <div style={{ position: "absolute", right: 0, top: 32, zIndex: 50, background: "#1a1d24", border: "1px solid #2a2d35", borderRadius: "6px", minWidth: "168px", padding: "4px 0", boxShadow: "0 8px 24px rgba(0,0,0,0.5)" }}>
                                    <button
                                      type="button"
                                      onClick={() => { setMenuDocId(null); setSelectedDoc(d); setOpenSignForm(false); }}
                                      style={{ width: "100%", padding: "8px 14px", display: "flex", alignItems: "center", gap: "8px", background: "transparent", border: "none", color: "#e8eaf0", fontSize: "13px", cursor: "pointer", textAlign: "left" }}
                                    >
                                      <ShieldCheck size={14} style={{ color: "#8b8fa8" }} /> View signatures
                                    </button>
                                    {(user?.role === "SUPER_ADMIN" || user?.role === "CASE_OFFICER") && (
                                      <button
                                        type="button"
                                        onClick={() => { setMenuDocId(null); setConfirmDeleteDoc(d); }}
                                        style={{ width: "100%", padding: "8px 14px", display: "flex", alignItems: "center", gap: "8px", background: "transparent", border: "none", color: "#ef4444", fontSize: "13px", cursor: "pointer", textAlign: "left" }}
                                      >
                                        <Trash2 size={14} /> Delete document
                                      </button>
                                    )}
                                  </div>
                                </>
                              )}
                            </div>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === "members" && (
          <MembersTab
            detail={detail}
            onMemberAdded={handleMemberAdded}
            onMemberRemoved={handleMemberRemoved}
          />
        )}

        {activeTab === "activity" && <ActivityTab caseId={detail.id} />}
      </div>

      {showTransfer && (
        <TransferCaseModal
          caseId={detail.id}
          onTransferred={(updated) => {
            setDetail(updated);
            setShowTransfer(false);
          }}
          onClose={() => setShowTransfer(false)}
        />
      )}

      {ocrDoc && (
        <OcrApprovalModal
          doc={ocrDoc}
          onUpdated={updateDoc}
          onClose={() => setOcrDoc(null)}
        />
      )}

      {selectedDoc && (
        <DocumentDetailPanel
          doc={selectedDoc}
          currentUser={user}
          onClose={() => setSelectedDoc(null)}
          initialSignFormOpen={openSignForm}
          onDownload={() => downloadDocument(selectedDoc.id, selectedDoc.filename)}
        />
      )}

      {confirmDeleteDoc && (
        <ConfirmModal
          title="Delete document"
          body={`Permanently delete "${confirmDeleteDoc.filename}"? The action is logged to the audit trail.`}
          confirmLabel="Delete"
          onConfirm={() => { void handleDeleteDoc(confirmDeleteDoc); setConfirmDeleteDoc(null); }}
          onClose={() => setConfirmDeleteDoc(null)}
        />
      )}
    </>
  );
}
