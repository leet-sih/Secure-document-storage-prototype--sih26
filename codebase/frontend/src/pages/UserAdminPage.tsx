/**
 * UserAdminPage.tsx — /admin/users (auth, SUPER_ADMIN)
 *
 * Lists users and provides admin-only account creation ("signup is by admin"). Creating a
 * user returns a one-time temporary password, shown once in the modal. The new account is
 * is_first_login=True and must change password + enrol TOTP on first login.
 *
 * Row actions (edit role / deactivate) are deferred — see docs/TODO.md.
 */
import { useEffect, useMemo, useState } from "react";
import type { CSSProperties, FormEvent, ReactNode } from "react";

import { ApiError, apiFetch } from "../lib/apiClient";
import { stepUp } from "../lib/caseApi";
import StepUpMfaModal from "../components/StepUpMfaModal";
import { useAuth } from "../store/AuthContext";
import type { AdminUser, Department, Role } from "../types";

const CREATE_ROLES: Role[] = ["INVESTIGATOR", "CASE_OFFICER", "PROSECUTOR", "AUDITOR", "SUPER_ADMIN"];

interface UserDto {
  id: string;
  email: string;
  full_name: string;
  employee_id: string | null;
  role: Role;
  department_id: string;
  is_active: boolean;
  is_first_login: boolean;
  mfa_enabled: boolean;
  last_login_at: string | null;
}
interface DeptDto {
  id: string;
  name: string;
  dept_type: string;
}

function toAdminUser(d: UserDto): AdminUser {
  return {
    id: d.id,
    email: d.email,
    fullName: d.full_name,
    employeeId: d.employee_id,
    role: d.role,
    departmentId: d.department_id,
    isActive: d.is_active,
    isFirstLogin: d.is_first_login,
    mfaEnabled: d.mfa_enabled,
    lastLoginAt: d.last_login_at,
  };
}

const th: CSSProperties = {
  textAlign: "left",
  padding: "10px 12px",
  borderBottom: "1px solid #2a2d35",
  fontSize: 12,
  fontWeight: 500,
  color: "#8b8fa8",
  letterSpacing: "0.04em",
};
const td: CSSProperties = {
  padding: "12px",
  borderBottom: "1px solid #1e2028",
  fontSize: 13,
  color: "#e8eaf0",
};
const fieldInput: CSSProperties = {
  height: 34,
  padding: "0 10px",
  background: "#1e2028",
  border: "1px solid #2a2d35",
  borderRadius: 6,
  color: "#e8eaf0",
  fontSize: 13,
};

export default function UserAdminPage() {

  const [users, setUsers] = useState<AdminUser[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<AdminUser | null>(null);
  const { user: currentUser, setSession } = useAuth();
  const [showStepUp, setShowStepUp] = useState(false);
  const [otp, setOtp] = useState("");
  const [otpError, setOtpError] = useState("");
  const [pendingAction, setPendingAction] = useState<(() => Promise<void>) | null>(null);

  const deptName = useMemo(() => {
    const map = new Map(departments.map((d) => [d.id, d.name]));
    return (id: string) => map.get(id) ?? "—";
  }, [departments]);

  async function loadUsers() {
    const res = (await apiFetch("/users")) as { users: UserDto[] };
    setUsers(res.users.map(toAdminUser));
  }

  function requireStepUp(action: () => Promise<void>) {
    setPendingAction(() => action);
    setOtp("");
    setOtpError("");
    setShowStepUp(true);
  }

  async function toggleUserActive(user: AdminUser, skipMfaCheck = false) {
    try {
      if (user.isActive) {
        await apiFetch(`/users/${user.id}`, {
           method: "DELETE",
        });
      } else {
        await apiFetch(`/users/${user.id}/activate`, {
          method: "POST",
        });
      }

      await loadUsers();
    } catch (err) {
      if (!skipMfaCheck && err instanceof ApiError && err.code === "MFA_REQUIRED") {
        requireStepUp(() => toggleUserActive(user, true));
        return;
      }

      setLoadError(
        err instanceof Error ? err.message : "Could not update user status"
      );
    }
  }

  async function handleStepUpVerify() {
    if (!otp || otp.length < 6) {
      setOtpError("Enter the 6-digit code from your authenticator app.");
      return;
    }

    setOtpError("");

    try {
      const newToken = await stepUp(otp);
      setSession(newToken, currentUser!);

      setShowStepUp(false);
      setOtp("");

      const action = pendingAction;
      setPendingAction(null);

      if (action) {
        await action();
      }
    } catch (err) {
      setOtpError(
        err instanceof Error ? err.message : "Verification failed."
      );
    }
  }
  
  useEffect(() => {
    Promise.all([
      loadUsers(),
      apiFetch("/users/departments").then((r) =>
        setDepartments((r as { departments: DeptDto[] }).departments.map((d) => ({
          id: d.id,
          name: d.name,
          deptType: d.dept_type,
        }))),
      ),
    ]).catch((err) => setLoadError(err instanceof Error ? err.message : "Failed to load users"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <h1 style={{ margin: 0, fontSize: 24, fontWeight: 700 }}>Users</h1>
          <button
            type="button"
            onClick={() => setModalOpen(true)}
            style={{
              marginLeft: "auto",
              height: 34,
              padding: "0 14px",
              background: "#3b82f6",
              color: "#fff",
              border: "none",
              borderRadius: 4,
              fontSize: 14,
              fontWeight: 500,
              cursor: "pointer",
            }}
          >
            + Create User
          </button>
        </div>

        {loadError && (
          <div
            style={{
              background: "#3d1010",
              border: "1px solid #ef4444",
              borderRadius: 6,
              padding: "10px 12px",
              fontSize: 13,
            }}
          >
            {loadError}
          </div>
        )}

        <div
          style={{
            background: "#111318",
            border: "1px solid #2a2d35",
            borderRadius: 8,
            overflow: "hidden",
          }}
        >
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", minWidth: 860, borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "#14161c" }}>
                  <th style={th}>NAME</th>
                  <th style={th}>EMAIL</th>
                  <th style={th}>ROLE</th>
                  <th style={th}>DEPARTMENT</th>
                  <th style={th}>STATUS</th>
                  <th style={th}>MFA</th>
                  <th style={{ ...th, textAlign: "right" }}>ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td style={{ ...td, whiteSpace: "nowrap" }}>{u.fullName}</td>
                    <td
                      style={{
                        ...td,
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 12,
                        color: "#8b8fa8",
                      }}
                    >
                      {u.email}
                    </td>
                    <td style={td}>
                      <span
                        style={{
                          fontSize: 11,
                          fontWeight: 500,
                          letterSpacing: "0.05em",
                          padding: "3px 7px",
                          borderRadius: 4,
                          color: "#93c5fd",
                          background: "#172554",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {u.role}
                      </span>
                    </td>
                    <td style={{ ...td, color: "#8b8fa8", whiteSpace: "nowrap" }}>
                      {deptName(u.departmentId)}
                    </td>
                    <td style={{ ...td, color: "#8b8fa8" }}>
                      {u.isActive ? (u.isFirstLogin ? "Pending first login" : "Active") : "Inactive"}
                    </td>
                    <td style={{ ...td, color: u.mfaEnabled ? "#22c55e" : "#8b8fa8" }}>
                      {u.mfaEnabled ? "Enabled" : "—"}
                    </td>
                    <td style={{ ...td, textAlign: "right" }}>

                      <button
                        type="button"
                        onClick={() => setEditingUser(u)}
                        style={{
                          height: 28,
                          padding: "0 10px",
                          marginRight: 6,
                          background: "transparent",
                          border: "1px solid #2a2d35",
                          borderRadius: 4,
                          color: "#e8eaf0",
                          fontSize: 12,
                          cursor: "pointer",
                        }}
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => void toggleUserActive(u)}
                        style={{
                          height: 28,
                          padding: "0 10px",
                          background: "transparent",
                          border: "1px solid #2a2d35",
                          borderRadius: 4,
                          color: u.isActive ? "#ef4444" : "#22c55e",
                          fontSize: 12,
                          cursor: "pointer",
                        }}
                      >
                        {u.isActive ? "Deactivate" : "Activate"}
                      </button>
                    </td>
                  </tr>
                ))}
                {users.length === 0 && !loadError && (
                  <tr>
                    <td style={{ ...td, color: "#8b8fa8" }} colSpan={7}>
                      No users yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      {modalOpen && (
        <CreateUserModal
          departments={departments}
          onClose={() => setModalOpen(false)}
          onCreated={loadUsers}
        />
      )}
      
      {editingUser && (
        <EditUserModal
          user={editingUser}
          departments={departments}
          onClose={() => setEditingUser(null)}
          onSaved={async () => {
            await loadUsers();
            setEditingUser(null);
          }}
        />
      )}
      {showStepUp && (
        <StepUpMfaModal
          label="User administration — requires MFA re-verification"
          otp={otp}
          error={otpError}
          onOtpChange={setOtp}
          onVerify={() => void handleStepUpVerify()}
          onClose={() => {
            setShowStepUp(false);
            setOtp("");
            setOtpError("");
            setPendingAction(null);
          }}
        />
      )}
    </div>
  );
}

function CreateUserModal({
  departments,
  onClose,
  onCreated,
}: {
  departments: Department[];
  onClose: () => void;
  onCreated: () => Promise<void>;
}) {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>("INVESTIGATOR");
  const [departmentId, setDepartmentId] = useState("");
  const [tempPassword, setTempPassword] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!departmentId && departments.length) setDepartmentId(departments[0].id);
  }, [departments, departmentId]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const res = (await apiFetch("/users", {
        method: "POST",
        body: JSON.stringify({
          full_name: fullName.trim(),
          email: email.trim(),
          role,
          department_id: departmentId,
        }),
      })) as { temp_password: string };
      setTempPassword(res.temp_password);
      await onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create user");
    } finally {
      setBusy(false);
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
        padding: 24,
      }}
    >
      <div
        style={{
          width: 480,
          maxWidth: "100%",
          background: "#1a1d24",
          border: "1px solid #2a2d35",
          borderRadius: 8,
          boxShadow: "0 28px 60px rgba(0,0,0,0.6)",
          padding: 22,
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 17, fontWeight: 600 }}>Create user</span>
          <button
            type="button"
            aria-label="Close"
            onClick={onClose}
            style={{
              marginLeft: "auto",
              width: 28,
              height: 28,
              background: "transparent",
              border: "none",
              borderRadius: 4,
              color: "#8b8fa8",
              fontSize: 18,
              cursor: "pointer",
            }}
          >
            ×
          </button>
        </div>

        {tempPassword ? (
          <>
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 8,
                background: "#3d1010",
                border: "1px solid #ef4444",
                borderRadius: 6,
                padding: 12,
              }}
            >
              <div style={{ fontSize: 12, color: "#e8eaf0" }}>Temporary password — copy it now.</div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <code
                  style={{
                    flex: 1,
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 13,
                    color: "#e8eaf0",
                    background: "#14161c",
                    border: "1px solid #2a2d35",
                    borderRadius: 4,
                    padding: "8px 10px",
                    wordBreak: "break-all",
                  }}
                >
                  {tempPassword}
                </code>
                <button
                  type="button"
                  onClick={() => {
                    navigator.clipboard?.writeText(tempPassword);
                    setCopied(true);
                  }}
                  style={{
                    height: 32,
                    padding: "0 10px",
                    background: "#1a1d24",
                    border: "1px solid #2a2d35",
                    borderRadius: 4,
                    color: "#e8eaf0",
                    fontSize: 12,
                    cursor: "pointer",
                  }}
                >
                  {copied ? "Copied" : "Copy"}
                </button>
              </div>
              <div style={{ fontSize: 11, color: "#8b8fa8" }}>This password will not be shown again.</div>
            </div>
            <button
              type="button"
              onClick={onClose}
              style={{
                height: 34,
                padding: "0 16px",
                background: "#3b82f6",
                color: "#fff",
                border: "none",
                borderRadius: 4,
                fontSize: 14,
                fontWeight: 500,
                cursor: "pointer",
              }}
            >
              Done
            </button>
          </>
        ) : (
          <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <ModalField id="cu-name" text="Full name">
              <input
                id="cu-name"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="SI A. Kulkarni"
                style={fieldInput}
              />
            </ModalField>
            <ModalField id="cu-email" text="Email">
              <input
                id="cu-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="a.kulkarni@mah.police.gov.in"
                style={fieldInput}
              />
            </ModalField>
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
              <ModalField id="cu-role" text="Role" grow>
                <select
                  id="cu-role"
                  value={role}
                  onChange={(e) => setRole(e.target.value as Role)}
                  style={fieldInput}
                >
                  {CREATE_ROLES.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </ModalField>
              <ModalField id="cu-dept" text="Department" grow>
                <select
                  id="cu-dept"
                  value={departmentId}
                  onChange={(e) => setDepartmentId(e.target.value)}
                  style={fieldInput}
                >
                  {departments.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </ModalField>
            </div>

            {error && (
              <div
                style={{
                  background: "#3d1010",
                  border: "1px solid #ef4444",
                  borderRadius: 6,
                  padding: "10px 12px",
                  fontSize: 13,
                }}
              >
                {error}
              </div>
            )}

            <div style={{ display: "flex", gap: 8, borderTop: "1px solid #2a2d35", paddingTop: 16 }}>
              <button
                type="submit"
                disabled={busy || !departmentId}
                style={{
                  height: 34,
                  padding: "0 16px",
                  background: "#3b82f6",
                  color: "#fff",
                  border: "none",
                  borderRadius: 4,
                  fontSize: 14,
                  fontWeight: 500,
                  cursor: "pointer",
                  opacity: busy || !departmentId ? 0.6 : 1,
                }}
              >
                {busy ? "Creating…" : "Create User"}
              </button>
              <button
                type="button"
                onClick={onClose}
                style={{
                  height: 34,
                  padding: "0 14px",
                  background: "transparent",
                  border: "1px solid #2a2d35",
                  borderRadius: 4,
                  color: "#8b8fa8",
                  fontSize: 14,
                  cursor: "pointer",
                }}
              >
                Close
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

function EditUserModal({
  user,
  departments,
  onClose,
  onSaved,
}: {
  user: AdminUser;
  departments: Department[];
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const [role, setRole] = useState<Role>(user.role);
  const [departmentId, setDepartmentId] = useState(user.departmentId);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);

    try {
      await apiFetch(`/users/${user.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          role,
          department_id: departmentId,
        }),
      });

      await onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update user");
    } finally {
      setBusy(false);
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
        padding: 24,
      }}
    >
      <div
        style={{
          width: 440,
          maxWidth: "100%",
          background: "#1a1d24",
          border: "1px solid #2a2d35",
          borderRadius: 8,
          padding: 22,
          display: "flex",
          flexDirection: "column",
          gap: 14,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 17, fontWeight: 600 }}>Edit user</span>
          <button
            type="button"
            onClick={onClose}
            style={{
              marginLeft: "auto",
              background: "transparent",
              border: "none",
              color: "#8b8fa8",
              fontSize: 18,
              cursor: "pointer",
            }}
          >
            ×
          </button>
        </div>

        <div style={{ fontSize: 13, color: "#8b8fa8" }}>
          {user.fullName} · {user.email}
        </div>

        <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <ModalField id="eu-role" text="Role">
            <select
              id="eu-role"
              value={role}
              onChange={(e) => setRole(e.target.value as Role)}
              style={fieldInput}
            >
              {CREATE_ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </ModalField>

          <ModalField id="eu-dept" text="Department">
            <select
              id="eu-dept"
              value={departmentId}
              onChange={(e) => setDepartmentId(e.target.value)}
              style={fieldInput}
            >
              {departments.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </ModalField>

          {error && (
            <div style={{ fontSize: 13, color: "#ef4444" }}>
              {error}
            </div>
          )}

          <div style={{ display: "flex", gap: 8 }}>
            <button
              type="submit"
              disabled={busy}
              style={{
                height: 34,
                padding: "0 16px",
                background: "#3b82f6",
                color: "#fff",
                border: "none",
                borderRadius: 4,
                fontSize: 14,
                cursor: busy ? "not-allowed" : "pointer",
                opacity: busy ? 0.6 : 1,
              }}
            >
              {busy ? "Saving…" : "Save"}
            </button>

            <button
              type="button"
              onClick={onClose}
              style={{
                height: 34,
                padding: "0 14px",
                background: "transparent",
                border: "1px solid #2a2d35",
                borderRadius: 4,
                color: "#8b8fa8",
                fontSize: 14,
                cursor: "pointer",
              }}
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function ModalField({
  id,
  text,
  grow,
  children,
}: {
  id: string;
  text: string;
  grow?: boolean;
  children: ReactNode;
}) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 6,
        flex: grow ? 1 : undefined,
        minWidth: grow ? 150 : undefined,
      }}
    >
      <label htmlFor={id} style={{ fontSize: 13, fontWeight: 500, color: "#e8eaf0" }}>
        {text}
      </label>
      {children}
    </div>
  );
}
