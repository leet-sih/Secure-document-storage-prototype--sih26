import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { apiFetch } from "../lib/apiClient";
import { addMember } from "../lib/caseApi";
import type { CaseMember } from "../types";

interface UserOption {
  id: string;
  fullName: string;
  email: string;
}

interface Props {
  caseId: string;
  existingMemberIds: Set<string>;
  onAdded: (m: CaseMember) => void;
  onClose: () => void;
}

const ASSIGNABLE_ROLES = [
  { value: "INVESTIGATOR", label: "Investigator" },
  { value: "PROSECUTOR", label: "Prosecutor" },
  { value: "CASE_OFFICER", label: "Case Officer" },
  { value: "VIEWER", label: "Viewer" },
];

export default function AddMemberModal({
  caseId,
  existingMemberIds,
  onAdded,
  onClose,
}: Props) {
  const [users, setUsers] = useState<UserOption[]>([]);
  const [userId, setUserId] = useState("");
  const [role, setRole] = useState("INVESTIGATOR");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [usersLoading, setUsersLoading] = useState(true);

  useEffect(() => {
    apiFetch("/users?limit=200")
      .then((res) => {
        const dto = res as {
          users: Array<{ id: string; full_name: string; email: string; is_active: boolean }>;
        };
        const available = dto.users.filter(
          (u) => u.is_active && !existingMemberIds.has(u.id)
        );
        const opts = available.map((u) => ({
          id: u.id,
          fullName: u.full_name,
          email: u.email,
        }));
        setUsers(opts);
        if (opts.length > 0) setUserId(opts[0].id);
      })
      .catch(() => {
        setUsers([]);
      })
      .finally(() => setUsersLoading(false));
  // Run once on mount.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSubmit() {
    if (!userId) {
      setError("Please select a user.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const m = await addMember(caseId, userId, role);
      onAdded(m);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add member.");
    } finally {
      setLoading(false);
    }
  }

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
          width: "460px",
          maxWidth: "100%",
          background: "#1a1d24",
          border: "1px solid #2a2d35",
          borderRadius: "8px",
          boxShadow: "0 28px 60px rgba(0,0,0,0.6)",
          padding: "22px",
          display: "flex",
          flexDirection: "column",
          gap: "14px",
        }}
      >
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "17px", fontWeight: 600, color: "#e8eaf0" }}>
            Add member
          </span>
          <button
            type="button"
            onClick={onClose}
            style={{
              marginLeft: "auto",
              width: "28px",
              height: "28px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background: "transparent",
              border: "none",
              borderRadius: "4px",
              color: "#8b8fa8",
              cursor: "pointer",
            }}
          >
            <X size={16} />
          </button>
        </div>

        {/* User select */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <label style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>
            User
          </label>
          {usersLoading ? (
            <div style={{ fontSize: "13px", color: "#555869" }}>Loading users…</div>
          ) : users.length === 0 ? (
            <div style={{ fontSize: "13px", color: "#8b8fa8" }}>
              No available users to add. All active users may already be members.
            </div>
          ) : (
            <select
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              style={{
                height: "34px",
                padding: "0 8px",
                background: "#1e2028",
                border: "1px solid #2a2d35",
                borderRadius: "6px",
                color: "#e8eaf0",
                fontSize: "13px",
              }}
            >
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.fullName} — {u.email}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Role select */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "6px",
            maxWidth: "200px",
          }}
        >
          <label style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>
            Role
          </label>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            style={{
              height: "34px",
              padding: "0 8px",
              background: "#1e2028",
              border: "1px solid #2a2d35",
              borderRadius: "6px",
              color: "#e8eaf0",
              fontSize: "13px",
            }}
          >
            {ASSIGNABLE_ROLES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </div>

        {error && (
          <div style={{ fontSize: "13px", color: "#ef4444" }}>{error}</div>
        )}

        {/* Actions */}
        <div
          style={{
            display: "flex",
            gap: "8px",
            borderTop: "1px solid #2a2d35",
            paddingTop: "16px",
          }}
        >
          <button
            type="button"
            onClick={handleSubmit}
            disabled={loading || usersLoading || users.length === 0}
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
              opacity: loading || users.length === 0 ? 0.7 : 1,
            }}
          >
            {loading ? "Adding…" : "Add Member"}
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
