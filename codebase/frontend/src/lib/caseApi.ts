/**
 * caseApi.ts — typed apiFetch wrappers for every case endpoint.
 *
 * All snake_case → camelCase mapping happens here; consumers work with camelCase types.
 * withStepUp() handles the MFA_REQUIRED → step-up retry flow transparently.
 */

import { apiFetch } from "./apiClient";
export { ApiError } from "./apiClient";
import type {
  CaseDetail,
  CaseListResponse,
  CaseMember,
  CasePriority,
  CaseStatus,
  TimelineResponse,
  TransferOptions,
} from "../types";

// ── DTO shapes (raw snake_case from API) ───────────────────────────────────────

interface UserBriefDto {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

interface DeptDto {
  id: string;
  name: string;
}

interface CaseMemberDto {
  user_id: string;
  email: string;
  full_name: string;
  role: string;
  department: string;
  added_at: string;
}

interface CaseDetailDto {
  id: string;
  case_number: string;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  category: string | null;
  created_by: UserBriefDto;
  lead_officer: UserBriefDto | null;
  department: DeptDto;
  members: CaseMemberDto[];
  document_summary: { total: number; by_status: Record<string, number> };
  created_at: string;
  updated_at: string;
  closed_at: string | null;
  archived_at: string | null;
}

interface CaseSummaryDto {
  id: string;
  case_number: string;
  title: string;
  status: string;
  priority: string;
  category: string | null;
  document_count: number;
  member_count: number;
  created_at: string;
  updated_at: string;
}

interface TimelineEventDto {
  id: number;
  event_type: string;
  actor: UserBriefDto | null;
  target_type: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

// ── Converters ─────────────────────────────────────────────────────────────────

function toUserBrief(dto: UserBriefDto) {
  return { id: dto.id, email: dto.email, fullName: dto.full_name, role: dto.role as never };
}

function toCaseSummary(dto: CaseSummaryDto) {
  return {
    id: dto.id,
    caseNumber: dto.case_number,
    title: dto.title,
    status: dto.status as CaseStatus,
    priority: dto.priority as CasePriority,
    category: dto.category,
    documentCount: dto.document_count,
    memberCount: dto.member_count,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

function toCaseDetail(dto: CaseDetailDto): CaseDetail {
  return {
    id: dto.id,
    caseNumber: dto.case_number,
    title: dto.title,
    description: dto.description,
    status: dto.status as CaseStatus,
    priority: dto.priority as CasePriority,
    category: dto.category,
    createdBy: toUserBrief(dto.created_by),
    leadOfficer: dto.lead_officer ? toUserBrief(dto.lead_officer) : null,
    department: { id: dto.department.id, name: dto.department.name },
    members: dto.members.map(
      (m): CaseMember => ({
        userId: m.user_id,
        email: m.email,
        fullName: m.full_name,
        role: m.role as CaseMember["role"],
        department: m.department,
        addedAt: m.added_at,
      })
    ),
    documentSummary: {
      total: dto.document_summary.total,
      byStatus: dto.document_summary.by_status ?? {},
    },
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
    closedAt: dto.closed_at,
    archivedAt: dto.archived_at,
  };
}

// ── Step-up helper ─────────────────────────────────────────────────────────────

/**
 * Wraps a sensitive API call. If the server returns 401 MFA_REQUIRED, the caller
 * must catch ApiError with code "MFA_REQUIRED" and open StepUpMfaModal.
 * After step-up succeeds (new token stored), retry by calling the fn again.
 *
 * Usage in components:
 *   try {
 *     await fn();
 *   } catch (err) {
 *     if (err instanceof ApiError && err.code === "MFA_REQUIRED") {
 *       openStepUpModal(() => fn());  // retry after step-up
 *     }
 *   }
 *
 * The step-up modal calls stepUp(totp) which hits POST /auth/mfa/step-up
 * and saves the new token via AuthContext.setSession().
 */
export async function stepUp(totp: string): Promise<string> {
  const res = (await apiFetch("/auth/mfa/step-up", {
    method: "POST",
    body: JSON.stringify({ totp_code: totp }),
  })) as { access_token: string };
  return res.access_token;
}

// ── Case CRUD ──────────────────────────────────────────────────────────────────

export async function createCase(payload: {
  caseNumber: string;
  title: string;
  description?: string;
  priority?: string;
  category?: string;
}): Promise<CaseDetail> {
  const dto = (await apiFetch("/cases", {
    method: "POST",
    body: JSON.stringify({
      case_number: payload.caseNumber,
      title: payload.title,
      description: payload.description,
      priority: payload.priority,
      category: payload.category,
    }),
  })) as CaseDetailDto;
  return toCaseDetail(dto);
}

export async function listCases(params: {
  status?: string;
  priority?: string;
  search?: string;
  mine?: boolean;
  page?: number;
  limit?: number;
}): Promise<CaseListResponse> {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.priority) qs.set("priority", params.priority);
  if (params.search) qs.set("search", params.search);
  if (params.mine) qs.set("mine", "true");
  if (params.page) qs.set("page", String(params.page));
  if (params.limit) qs.set("limit", String(params.limit));

  const res = (await apiFetch(`/cases?${qs}`)) as {
    cases: CaseSummaryDto[];
    total: number;
    page: number;
    limit: number;
  };
  return {
    items: res.cases.map(toCaseSummary),
    total: res.total,
    page: res.page,
    limit: res.limit,
  };
}

export async function getCase(id: string): Promise<CaseDetail> {
  const dto = (await apiFetch(`/cases/${id}`)) as CaseDetailDto;
  return toCaseDetail(dto);
}

export async function patchCase(
  id: string,
  data: { title?: string; description?: string; priority?: string; category?: string; status?: string }
): Promise<CaseDetail> {
  const dto = (await apiFetch(`/cases/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })) as CaseDetailDto;
  return toCaseDetail(dto);
}

// ── Members ────────────────────────────────────────────────────────────────────

export async function addMember(
  caseId: string,
  userId: string,
  role: string
): Promise<CaseMember> {
  const m = (await apiFetch(`/cases/${caseId}/members`, {
    method: "POST",
    body: JSON.stringify({ user_id: userId, role }),
  })) as CaseMemberDto;
  return {
    userId: m.user_id,
    email: m.email,
    fullName: m.full_name,
    role: m.role as CaseMember["role"],
    department: m.department,
    addedAt: m.added_at,
  };
}

export async function removeMember(caseId: string, userId: string): Promise<void> {
  await apiFetch(`/cases/${caseId}/members/${userId}`, { method: "DELETE" });
}

// ── Transfer ───────────────────────────────────────────────────────────────────

export async function getTransferOptions(caseId: string): Promise<TransferOptions> {
  const res = (await apiFetch(`/cases/${caseId}/transfer-options`)) as {
    departments: Array<{ id: string; name: string }>;
    officers: Array<{ id: string; full_name: string; email: string; department_id: string }>;
  };
  return {
    departments: res.departments,
    officers: res.officers.map((o) => ({
      id: o.id,
      fullName: o.full_name,
      email: o.email,
      departmentId: o.department_id,
    })),
  };
}

export async function transferCase(
  caseId: string,
  toDepartmentId: string,
  newLeadOfficerId: string
): Promise<CaseDetail> {
  const dto = (await apiFetch(`/cases/${caseId}/transfer`, {
    method: "POST",
    body: JSON.stringify({
      to_department_id: toDepartmentId,
      new_lead_officer_id: newLeadOfficerId,
    }),
  })) as CaseDetailDto;
  return toCaseDetail(dto);
}

// ── Timeline ───────────────────────────────────────────────────────────────────

export async function getTimeline(
  caseId: string,
  limit = 50,
  beforeId?: number
): Promise<TimelineResponse> {
  const qs = new URLSearchParams({ limit: String(limit) });
  if (beforeId) qs.set("before_id", String(beforeId));
  const res = (await apiFetch(`/cases/${caseId}/timeline?${qs}`)) as {
    events: TimelineEventDto[];
    next_before_id: number | null;
  };
  return {
    events: res.events.map((e) => ({
      id: e.id,
      eventType: e.event_type,
      actor: e.actor ? toUserBrief(e.actor) : null,
      targetType: e.target_type,
      metadata: e.metadata,
      createdAt: e.created_at,
    })),
    nextBeforeId: res.next_before_id,
  };
}
