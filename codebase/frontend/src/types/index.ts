/**
 * types/index.ts — shared TypeScript interfaces mirroring the API's JSON shapes.
 *
 * Keep these in sync with the backend marshmallow *ResponseSchema classes. These are the
 * contract between frontend and backend — if the API changes, update here first.
 */

export type Role =
  | "SUPER_ADMIN"
  | "CASE_OFFICER"
  | "INVESTIGATOR"
  | "PROSECUTOR"
  | "AUDITOR"
  | "VIEWER";

export interface CurrentUser {
  id: string;
  email: string;
  fullName: string;
  role: Role;
  mfaEnabled: boolean;
  isFirstLogin: boolean;
}

export interface Department {
  id: string;
  name: string;
  deptType: string;
}

/** A row in the User Admin table. */
export interface AdminUser {
  id: string;
  email: string;
  fullName: string;
  employeeId: string | null;
  role: Role;
  departmentId: string;
  isActive: boolean;
  isFirstLogin: boolean;
  mfaEnabled: boolean;
  lastLoginAt: string | null;
}

/** Result of POST /auth/login, normalised for the LoginPage state machine. */
export interface LoginResult {
  /** Existing MFA user — a 6-digit TOTP step is required next. */
  mfaRequired: boolean;
  /** Brand-new / not-yet-enrolled user — session issued, must set up MFA. */
  mfaSetupRequired: boolean;
  /** Short-lived token to pass to verifyMfa(), present only when mfaRequired. */
  tempToken?: string;
}

export interface MfaSetupResult {
  otpauthUri: string;
  qrCodeBase64: string;
}

export interface CreateUserResult {
  user: AdminUser;
  tempPassword: string;
}

export type CaseStatus = "OPEN" | "UNDER_INVESTIGATION" | "CLOSED" | "ARCHIVED";
export type CasePriority = "LOW" | "NORMAL" | "HIGH" | "CRITICAL";
export type CaseMemberRole = "CASE_OFFICER" | "INVESTIGATOR" | "PROSECUTOR" | "VIEWER";

export interface UserBrief {
  id: string;
  email: string;
  fullName: string;
  role: Role;
}

export interface DeptBrief {
  id: string;
  name: string;
}

export interface CaseMember {
  userId: string;
  email: string;
  fullName: string;
  role: CaseMemberRole;
  department: string | null;
  addedAt: string;
}

export interface CaseSummary {
  id: string;
  caseNumber: string;
  title: string;
  status: CaseStatus;
  priority: CasePriority;
  category: string | null;
  documentCount: number;
  memberCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface CaseDetail {
  id: string;
  caseNumber: string;
  title: string;
  description: string | null;
  status: CaseStatus;
  priority: CasePriority;
  category: string | null;
  createdBy: UserBrief;
  leadOfficer: UserBrief | null;
  department: DeptBrief;
  members: CaseMember[];
  documentSummary: { total: number; byStatus: Record<string, number> };
  createdAt: string;
  updatedAt: string;
  closedAt: string | null;
  archivedAt: string | null;
}

export interface CaseListResponse {
  items: CaseSummary[];
  total: number;
  page: number;
  limit: number;
}

export interface TimelineEvent {
  id: number;
  eventType: string;
  actor: UserBrief | null;
  targetType: string | null;
  metadata: Record<string, unknown>;
  createdAt: string;
}

export interface TimelineResponse {
  events: TimelineEvent[];
  nextBeforeId: number | null;
}

export interface OfficerOption {
  id: string;
  fullName: string;
  email: string;
  departmentId: string;
}

export interface TransferOptions {
  departments: DeptBrief[];
  officers: OfficerOption[];
}

export type DocType =
  | "FIR" | "POLICE_REPORT" | "INVESTIGATION_RECORD" | "WITNESS_STATEMENT"
  | "CHARGE_SHEET" | "COURT_FILING" | "EVIDENCE_RECORD" | "FORENSIC_REPORT"
  | "LEGAL_NOTICE" | "JUDGMENT" | "OTHER";

export interface DocumentMeta {
  id: string;
  caseId: string | null;
  filename: string;
  docType: DocType;
  fileSizeBytes: number;
  tags: string[];
  status: string;
  createdAt: string;
  ocrStatus?: string;
  ocrConfidence?: number | null;
  ocrRawText?: string | null;
  ocrFormattedText?: string | null;
  ocrPageCount?: number | null;
  ocrDetail?: string | null;
}

export interface AuditEventRow {
  id: number;
  eventType: string;
  actorUserId: string | null;
  targetType: string | null;
  caseId: string | null;
  ipAddress: string | null;
  metadata: Record<string, unknown>;
  createdAt: string;
}
