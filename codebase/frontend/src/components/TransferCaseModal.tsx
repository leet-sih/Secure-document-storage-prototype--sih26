import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { ApiError } from "../lib/apiClient";
import { getTransferOptions, stepUp, transferCase } from "../lib/caseApi";
import { useAuth } from "../store/AuthContext";
import StepUpMfaModal from "./StepUpMfaModal";
import type { CaseDetail, DeptBrief, OfficerOption } from "../types";

interface Props {
  caseId: string;
  onTransferred: (c: CaseDetail) => void;
  onClose: () => void;
}

export default function TransferCaseModal({ caseId, onTransferred, onClose }: Props) {
  const { user, setSession } = useAuth();
  const [depts, setDepts] = useState<DeptBrief[]>([]);
  const [officers, setOfficers] = useState<OfficerOption[]>([]);
  const [deptId, setDeptId] = useState("");
  const [officerId, setOfficerId] = useState("");
  const [loading, setLoading] = useState(false);
  const [optLoading, setOptLoading] = useState(true);
  const [error, setError] = useState("");
  const [showStepUp, setShowStepUp] = useState(false);
  const [otp, setOtp] = useState("");
  const [otpError, setOtpError] = useState("");

  useEffect(() => {
    getTransferOptions(caseId)
      .then((opts) => {
        setDepts(opts.departments);
        setOfficers(opts.officers);
        // Pre-select the first eligible officer and derive their department.
        if (opts.officers.length > 0) {
          const first = opts.officers[0];
          setOfficerId(first.id);
          setDeptId(first.departmentId);
        } else if (opts.departments.length > 0) {
          setDeptId(opts.departments[0].id);
        }
      })
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Failed to load transfer options.")
      )
      .finally(() => setOptLoading(false));
  // Run once on mount.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function doTransfer(skipMfaCheck = false) {
    if (!deptId || !officerId) {
      setError("Please select a department and an officer.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const c = await transferCase(caseId, deptId, officerId);
      onTransferred(c);
    } catch (err) {
      if (!skipMfaCheck && err instanceof ApiError && err.code === "MFA_REQUIRED") {
        setShowStepUp(true);
      } else {
        setError(err instanceof Error ? err.message : "Transfer failed.");
      }
    } finally {
      setLoading(false);
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
      setSession(newToken, user!);
      setShowStepUp(false);
      setOtp("");
      await doTransfer(true);
    } catch (err) {
      setOtpError(err instanceof Error ? err.message : "Verification failed.");
    }
  }

  if (showStepUp) {
    return (
      <StepUpMfaModal
        label="Transfer case — requires MFA re-verification"
        otp={otp}
        error={otpError}
        onOtpChange={setOtp}
        onVerify={handleStepUpVerify}
        onClose={() => {
          setShowStepUp(false);
          setOtp("");
          setOtpError("");
        }}
      />
    );
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
          width: "512px",
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
            Transfer case
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

        <div style={{ fontSize: "13px", color: "#8b8fa8", lineHeight: 1.55 }}>
          Moves the case to a new department and assigns a new lead officer. Requires
          MFA re-verification.
        </div>

        {optLoading ? (
          <div style={{ fontSize: "13px", color: "#555869" }}>Loading options…</div>
        ) : (
          <>
            {/* New lead officer — selecting an officer also sets the target department */}
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <label style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>
                New lead officer
              </label>
              {officers.length === 0 ? (
                <div style={{ fontSize: "13px", color: "#555869" }}>
                  No active case officers found in the system.
                </div>
              ) : (
                <select
                  value={officerId}
                  onChange={(e) => {
                    const selected = officers.find((o) => o.id === e.target.value);
                    if (selected) {
                      setOfficerId(selected.id);
                      setDeptId(selected.departmentId);
                    }
                  }}
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
                  {officers.map((o) => {
                    const dept = depts.find((d) => d.id === o.departmentId);
                    return (
                      <option key={o.id} value={o.id}>
                        {o.fullName} — {dept?.name ?? "Unknown dept"} ({o.email})
                      </option>
                    );
                  })}
                </select>
              )}
            </div>

            {/* Show the resolved target department as read-only context */}
            {deptId && (
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                <span style={{ fontSize: "13px", fontWeight: 500, color: "#e8eaf0" }}>
                  Target department
                </span>
                <span style={{ fontSize: "13px", color: "#8b8fa8" }}>
                  {depts.find((d) => d.id === deptId)?.name ?? "—"}
                </span>
              </div>
            )}
          </>
        )}

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
            onClick={() => doTransfer(false)}
            disabled={loading || optLoading || !deptId || !officerId}
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
              opacity: loading || !officerId ? 0.7 : 1,
            }}
          >
            {loading ? "Transferring…" : "Transfer Case"}
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
