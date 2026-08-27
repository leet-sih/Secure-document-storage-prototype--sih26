// DESIGN REFERENCE — match this layout exactly when building src/components/EditRoleModal.tsx (or inline in UserAdminPage)

/**
 * Props:
 *   modalName       {string}   — user's full name displayed in the title
 *   modalCurrentRole {string}  — current role label
 *   newRoleValue    {string}   — controlled select value
 *   onSetNewRole    {fn}
 *   onSubmit        {fn}
 *   onClose         {fn}
 */
export default function EditRoleModal({
  modalName = "",
  modalCurrentRole = "",
  newRoleValue = "INVESTIGATOR",
  onSetNewRole,
  onSubmit,
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
        width: "420px", maxWidth: "100%",
        background: "#1a1d24", border: "1px solid #2a2d35", borderRadius: "8px",
        boxShadow: "0 28px 60px rgba(0,0,0,0.6)",
        padding: "22px", display: "flex", flexDirection: "column", gap: "14px"
      }}>

        {/* Title */}
        <div style={{ fontSize: "17px", fontWeight: 600, color: "#e8eaf0" }}>
          Change role — {modalName}
        </div>

        {/* Current role */}
        <div style={{ fontSize: "13px", color: "#8b8fa8" }}>
          Current role <span style={{ color: "#e8eaf0" }}>{modalCurrentRole}</span>
        </div>

        {/* New role select */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <label htmlFor="er-role" style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>New role</label>
          <select
            id="er-role"
            value={newRoleValue}
            onChange={onSetNewRole}
            style={{
              height: "34px", padding: "0 8px",
              background: "#1e2028", border: "1px solid #2a2d35", borderRadius: "6px",
              color: "#e8eaf0", fontSize: "13px"
            }}
          >
            <option value="INVESTIGATOR">INVESTIGATOR</option>
            <option value="CASE_OFFICER">CASE_OFFICER</option>
            <option value="PROSECUTOR">PROSECUTOR</option>
            <option value="AUDITOR">AUDITOR</option>
            <option value="SUPER_ADMIN">SUPER_ADMIN</option>
          </select>
        </div>

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
            Save role
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
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
