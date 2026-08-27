// DESIGN REFERENCE — match this layout exactly when building src/components/CreateUserModal.tsx (or inline in UserAdminPage)

import { X, Copy } from 'lucide-react';

/**
 * Props:
 *   hasTempPassword {boolean}  — newly created user: show temp password block
 *   tempPassword    {string}
 *   copiedTemp      {string}   — "Copy" or "Copied!"
 *   onSubmit        {fn}
 *   onCopyTemp      {fn}
 *   onClose         {fn}
 */
export default function CreateUserModal({
  hasTempPassword = false,
  tempPassword = "",
  copiedTemp = "Copy",
  onSubmit,
  onCopyTemp,
  onClose,
}) {
  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 90,
      background: "rgba(0,0,0,0.6)",
      display: "flex", alignItems: "center", justifyContent: "center",
      padding: "24px", animation: "fadein 120ms ease-out"
    }}>
      <div style={{
        width: "480px", maxWidth: "100%",
        background: "#1a1d24", border: "1px solid #2a2d35", borderRadius: "8px",
        boxShadow: "0 28px 60px rgba(0,0,0,0.6)",
        padding: "22px", display: "flex", flexDirection: "column", gap: "14px"
      }}>

        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "17px", fontWeight: 600, color: "#e8eaf0" }}>Create user</span>
          <button
            type="button"
            title="Close"
            aria-label="Close"
            onClick={onClose}
            style={{
              marginLeft: "auto", width: "28px", height: "28px",
              display: "flex", alignItems: "center", justifyContent: "center",
              background: "transparent", border: "none", borderRadius: "4px",
              color: "#8b8fa8", cursor: "pointer"
            }}
            /* hover: color #e8eaf0; background #1e2028 */
          >
            <X size={16} />
          </button>
        </div>

        {/* Full name */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <label htmlFor="cu-name" style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>Full name</label>
          <input
            id="cu-name"
            placeholder="SI A. Kulkarni"
            style={{
              height: "34px", padding: "0 10px",
              background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px",
              color: "#e8eaf0", fontSize: "13px"
            }}
          />
        </div>

        {/* Email */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <label htmlFor="cu-email" style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>Email</label>
          <input
            id="cu-email"
            type="email"
            placeholder="a.kulkarni@mah.police.gov.in"
            style={{
              height: "34px", padding: "0 10px",
              background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px",
              color: "#e8eaf0", fontSize: "13px"
            }}
          />
        </div>

        {/* Role + Department */}
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px", flex: 1, minWidth: "150px" }}>
            <label htmlFor="cu-role" style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>Role</label>
            <select
              id="cu-role"
              style={{
                height: "34px", padding: "0 8px",
                background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px",
                color: "#e8eaf0", fontSize: "13px"
              }}
            >
              <option>INVESTIGATOR</option>
              <option>CASE_OFFICER</option>
              <option>PROSECUTOR</option>
              <option>AUDITOR</option>
              <option>SUPER_ADMIN</option>
            </select>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px", flex: 1, minWidth: "150px" }}>
            <label htmlFor="cu-dept" style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>Department</label>
            <select
              id="cu-dept"
              style={{
                height: "34px", padding: "0 8px",
                background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px",
                color: "#e8eaf0", fontSize: "13px"
              }}
            >
              <option>Cybercrime Unit</option>
              <option>Sessions Court</option>
              <option>Forensic Lab</option>
            </select>
          </div>
        </div>

        {/* Temp password (shown after creation) */}
        {hasTempPassword && (
          <div style={{
            display: "flex", flexDirection: "column", gap: "8px",
            background: "#3d1010", border: "1px solid #ef4444",
            borderRadius: "6px", padding: "12px"
          }}>
            <div style={{ fontSize: "12px", color: "#e8eaf0" }}>Temporary password — copy it now.</div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <code style={{
                flex: 1, fontFamily: "'JetBrains Mono', monospace", fontSize: "13px", color: "#e8eaf0",
                background: "#14161c", border: "1px solid #2a2d35", borderRadius: "4px",
                padding: "8px 10px"
              }}>
                {tempPassword}
              </code>
              <button
                type="button"
                onClick={onCopyTemp}
                style={{
                  height: "32px", padding: "0 10px",
                  display: "flex", alignItems: "center", gap: "6px",
                  background: "#1a1d24", border: "1px solid #2a2d35", borderRadius: "4px",
                  color: "#e8eaf0", fontSize: "12px", cursor: "pointer"
                }}
                /* hover: background #14161c */
              >
                <Copy size={14} /> {copiedTemp}
              </button>
            </div>
            <div style={{ fontSize: "11px", color: "#8b8fa8" }}>This password will not be shown again.</div>
          </div>
        )}

        {/* Actions */}
        <div style={{ display: "flex", gap: "8px", borderTop: "1px solid #2a2d35", paddingTop: "16px" }}>
          <button
            type="button"
            onClick={onSubmit}
            style={{
              height: "34px", padding: "0 16px",
              background: "#3b82f6", color: "#ffffff",
              border: "none", borderRadius: "4px",
              fontSize: "14px", fontWeight: 500, cursor: "pointer"
            }}
            /* hover: background #2563eb */
          >
            Create User
          </button>
          <button
            type="button"
            onClick={onClose}
            style={{
              height: "34px", padding: "0 14px",
              background: "transparent", border: "1px solid #2a2d35", borderRadius: "4px",
              color: "#8b8fa8", fontSize: "14px", cursor: "pointer"
            }}
            /* hover: color #e8eaf0 */
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
