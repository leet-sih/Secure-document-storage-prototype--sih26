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

export type CaseStatus = "OPEN" | "UNDER_INVESTIGATION" | "CLOSED" | "ARCHIVED";
export type CasePriority = "LOW" | "NORMAL" | "HIGH" | "CRITICAL";

export interface CaseSummary {
  id: string;
  caseNumber: string;
  title: string;
  status: CaseStatus;
  priority: CasePriority;
  documentCount: number;
  memberCount: number;
  createdAt: string;
}

export type DocType =
  | "FIR" | "POLICE_REPORT" | "INVESTIGATION_RECORD" | "WITNESS_STATEMENT"
  | "CHARGE_SHEET" | "COURT_FILING" | "EVIDENCE_RECORD" | "FORENSIC_REPORT"
  | "LEGAL_NOTICE" | "JUDGMENT" | "OTHER";

export interface DocumentMeta {
  id: string;
  caseId: string;
  filename: string;
  docType: DocType;
  fileSizeBytes: number;
  tags: string[];
  status: string;
  createdAt: string;
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
