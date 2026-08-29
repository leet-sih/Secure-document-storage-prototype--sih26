// DESIGN REFERENCE — shared design tokens, colors, and constants

export const C = {
  base: "#0a0c10", surf: "#111318", elev: "#1a1d24", inp: "#1e2028",
  bsub: "#2a2d35", bact: "#3a3d47", tp: "#e8eaf0", ts: "#8b8fa8", tm: "#555869",
  acc: "#3b82f6", accH: "#2563eb", accS: "#1e3a5f",
  succ: "#22c55e", succS: "#14391f", warn: "#f59e0b", warnS: "#3d2c08",
  dang: "#ef4444", dangS: "#3d1010", info: "#6366f1", infoS: "#1e1e4a"
};

export const ROLE_LABEL = {
  SUPER_ADMIN: "System Admin", CASE_OFFICER: "Case Officer", INVESTIGATOR: "Investigator",
  PROSECUTOR: "Prosecutor", AUDITOR: "Auditor", VIEWER: "Viewer"
};

export const ROLE_COLOR = {
  SUPER_ADMIN: C.acc, CASE_OFFICER: C.info, INVESTIGATOR: C.warn,
  PROSECUTOR: C.succ, AUDITOR: C.ts, VIEWER: C.tm
};

export const STATUS_COLOR = {
  OPEN: C.info, UNDER_INVESTIGATION: C.warn, CLOSED: C.succ, ARCHIVED: C.tm
};

export const PRIORITY_COLOR = {
  LOW: C.tm, NORMAL: C.info, HIGH: C.warn, CRITICAL: C.dang
};

export const DOCTYPE_ICON = {
  FIR: "FileWarning", POLICE_REPORT: "FileText", INVESTIGATION_RECORD: "File",
  WITNESS_STATEMENT: "FileSignature", CHARGE_SHEET: "FileCheck2", COURT_FILING: "Building2",
  EVIDENCE_RECORD: "FolderLock", FORENSIC_REPORT: "Microscope", LEGAL_NOTICE: "FileText",
  JUDGMENT: "FileCheck2", OTHER: "File"
};

// Audit event severity colors
export const SEV = {
  LOGIN: C.succ, LOGOUT: C.succ, DOCUMENT_UPLOADED: C.succ, CASE_CREATED: C.succ,
  MFA_VERIFIED: C.succ, MFA_STEP_UP_VERIFIED: C.succ,
  DOCUMENT_DOWNLOADED: C.warn, DOCUMENT_PREVIEWED: C.warn, SHARE_LINK_ACCESSED: C.warn, CASE_ACCESSED: C.warn,
  DOCUMENT_DELETED: "#fb923c", ROLE_CHANGED: "#fb923c", ACCOUNT_LOCKED: "#fb923c",
  DOCUMENT_SHARED: "#fb923c", SHARE_LINK_REVOKED: "#fb923c",
  UNAUTHORIZED_ACCESS_ATTEMPT: C.dang, INTEGRITY_VIOLATION: C.dang, AUDIT_CHAIN_BROKEN: C.dang,
  LOGIN_FAILED: C.dang, MFA_STEP_UP_FAILED: C.dang
};

// Icon name map — keys are dc-runtime identifiers, values are Lucide component names
export const ICON_SET = {
  shield: "Shield", shieldCheck: "ShieldCheck", shieldX: "ShieldX", shieldAlert: "ShieldAlert",
  keyRound: "KeyRound", layoutDashboard: "LayoutDashboard", folderOpen: "FolderOpen",
  fileText: "FileText", upload: "Upload", download: "Download", search: "Search",
  clipboardList: "ClipboardList", users: "Users", userCircle: "UserCircle", settings: "Settings",
  penLine: "PenLine", share2: "Share2", trash2: "Trash2", alertTriangle: "AlertTriangle",
  alertCircle: "AlertCircle", info: "Info", checkCircle: "CheckCircle2", xCircle: "XCircle",
  loader: "Loader2", refresh: "RefreshCw", copy: "Copy", x: "X", moreVertical: "MoreVertical",
  externalLink: "ExternalLink", film: "Film", file: "File", folderLock: "FolderLock",
  chevronDown: "ChevronDown", chevronRight: "ChevronRight", arrowUpDown: "ArrowUpDown",
  filter: "Filter", badgeCheck: "BadgeCheck", logOut: "LogOut", microscope: "Microscope",
  fileWarning: "FileWarning", fileCheck: "FileCheck2", fileSignature: "FileSignature",
  building: "Building2", plus: "Plus", arrowRight: "ArrowRight", arrowLeft: "ArrowLeft",
  clock: "Clock", menu: "Menu", image: "Image", lock: "Lock", eye: "Eye", check: "Check",
  chevronLeft: "ChevronLeft", tag: "Tag", calendar: "Calendar", pencil: "Pencil", userX: "UserX"
};

// Lucide icon alias fallbacks (some Lucide versions rename icons)
export const ALIAS = {
  CheckCircle2: ["CheckCircle2", "CircleCheckBig", "CheckCircle"],
  XCircle: ["XCircle", "CircleX"],
  AlertCircle: ["AlertCircle", "CircleAlert"],
  Loader2: ["Loader2", "LoaderCircle"],
  MoreVertical: ["MoreVertical", "EllipsisVertical"],
  UserCircle: ["UserCircle", "CircleUser"],
  FileCheck2: ["FileCheck2", "FileCheck"],
  Image: ["Image", "ImageIcon"]
};

// Global CSS animations (define in index.css or a <style> block)
// @keyframes spin    { to { transform: rotate(360deg); } }
// @keyframes slidein { from { transform: translateX(24px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
// @keyframes fadein  { from { opacity: 0; } to { opacity: 1; } }
// @keyframes rise    { from { transform: translateY(8px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
// @keyframes pulseborder { 0%, 100% { border-color: #ef4444; } 50% { border-color: #7f1d1d; } }
