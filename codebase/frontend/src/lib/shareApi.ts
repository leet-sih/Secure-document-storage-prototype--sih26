/**
 * shareApi.ts — API calls for share link creation (authenticated) and public access.
 *
 * Public endpoints do NOT send an Authorization header (no apiFetch — use raw fetch).
 * Authenticated endpoints use apiFetch.
 */

import { apiFetch } from "./apiClient";
export { ApiError } from "./apiClient";
import type {
  ShareCreateResult,
  ShareInfo,
  ShareLink,
  SharedCaseDetail,
  SharedDocMeta,
} from "../types";

const BASE = "/api/v1";

// ── Authenticated — document share ──────────────────────────────────────────────

export async function createDocumentShare(
  documentId: string,
  opts: {
    expiresInHours: number;
    maxUses: number;
    allowedEmail: string;
    note?: string;
    totpCode: string;
    allowDownload?: boolean;
  }
): Promise<ShareCreateResult> {
  const res = (await apiFetch(`/documents/${documentId}/share`, {
    method: "POST",
    body: JSON.stringify({
      expires_in_hours: opts.expiresInHours,
      max_uses: opts.maxUses,
      allowed_email: opts.allowedEmail,
      note: opts.note,
      totp_code: opts.totpCode,
      allow_download: opts.allowDownload ?? true,
    }),
  })) as { share_id: string; share_url: string; expires_at: string; max_uses: number };
  return {
    shareId: res.share_id,
    shareUrl: res.share_url,
    expiresAt: res.expires_at,
    maxUses: res.max_uses,
  };
}

export async function listDocumentShares(documentId: string): Promise<ShareLink[]> {
  const res = (await apiFetch(`/documents/${documentId}/shares`)) as { shares: ShareLinkDto[] };
  return res.shares.map(toShareLink);
}

export async function revokeDocumentShare(documentId: string, shareId: string): Promise<void> {
  await apiFetch(`/documents/${documentId}/shares/${shareId}`, { method: "DELETE" });
}

// ── Authenticated — case share ───────────────────────────────────────────────────

export async function createCaseShare(
  caseId: string,
  opts: {
    shareScope: "CASE_DOCUMENTS" | "CASE_FULL";
    expiresInHours: number;
    maxUses: number;
    allowedEmail: string;
    note?: string;
    totpCode: string;
    allowDownload?: boolean;
  }
): Promise<ShareCreateResult> {
  const res = (await apiFetch(`/cases/${caseId}/share`, {
    method: "POST",
    body: JSON.stringify({
      share_scope: opts.shareScope,
      expires_in_hours: opts.expiresInHours,
      max_uses: opts.maxUses,
      allowed_email: opts.allowedEmail,
      note: opts.note,
      totp_code: opts.totpCode,
      allow_download: opts.allowDownload ?? true,
    }),
  })) as {
    share_id: string;
    share_url: string;
    expires_at: string;
    max_uses: number;
    share_scope: string;
  };
  return {
    shareId: res.share_id,
    shareUrl: res.share_url,
    expiresAt: res.expires_at,
    maxUses: res.max_uses,
    shareScope: res.share_scope as "CASE_DOCUMENTS" | "CASE_FULL",
  };
}

export async function listCaseShares(caseId: string): Promise<ShareLink[]> {
  const res = (await apiFetch(`/cases/${caseId}/shares`)) as { shares: ShareLinkDto[] };
  return res.shares.map(toShareLink);
}

export async function revokeCaseShare(caseId: string, shareId: string): Promise<void> {
  await apiFetch(`/cases/${caseId}/shares/${shareId}`, { method: "DELETE" });
}

// ── Public — no auth ─────────────────────────────────────────────────────────────

export async function getShareInfo(token: string): Promise<ShareInfo> {
  const res = await fetch(`${BASE}/share/${token}/info`);
  if (res.status === 410) {
    return {
      scope: "DOCUMENT",
      filename: null,
      caseTitle: null,
      caseNumber: null,
      docCount: null,
      fileSizeBytes: null,
      expiresAt: "",
      requiresEmail: false,
      isValid: false,
    };
  }
  if (!res.ok) throw new Error("Failed to load share info");
  const data = (await res.json()) as {
    scope: string;
    filename: string | null;
    case_title: string | null;
    case_number: string | null;
    doc_count: number | null;
    file_size_bytes: number | null;
    expires_at: string;
    requires_email: boolean;
    is_valid: boolean;
    allow_download: boolean;
  };
  return {
    scope: data.scope as ShareInfo["scope"],
    filename: data.filename,
    caseTitle: data.case_title,
    caseNumber: data.case_number,
    docCount: data.doc_count,
    fileSizeBytes: data.file_size_bytes,
    expiresAt: data.expires_at,
    requiresEmail: data.requires_email,
    isValid: data.is_valid,
    allowDownload: data.allow_download ?? true,
  };
}

/** Download for DOCUMENT scope — returns a Blob for the browser to save. */
export async function downloadShareDocument(token: string, email: string): Promise<Blob> {
  const res = await fetch(`${BASE}/share/${token}/download`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (res.status === 403) throw new Error("EMAIL_MISMATCH");
  if (res.status === 410) throw new Error("LINK_EXPIRED");
  if (!res.ok) throw new Error("Download failed");
  return res.blob();
}

/** Access for CASE_DOCUMENTS scope — returns doc list. */
export async function accessCaseDocuments(
  token: string,
  email: string
): Promise<{ caseId: string; documents: SharedDocMeta[] }> {
  const res = await fetch(`${BASE}/share/${token}/download`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (res.status === 403) throw new Error("EMAIL_MISMATCH");
  if (res.status === 410) throw new Error("LINK_EXPIRED");
  if (!res.ok) throw new Error("Access failed");
  const data = (await res.json()) as {
    scope: string;
    case_id: string;
    documents: SharedDocMetaDto[];
  };
  return {
    caseId: data.case_id,
    documents: data.documents.map(toSharedDoc),
  };
}

/** Access for CASE_FULL scope — returns case detail + docs. */
export async function accessCaseFull(
  token: string,
  email: string
): Promise<{ case: SharedCaseDetail; documents: SharedDocMeta[] }> {
  const res = await fetch(`${BASE}/share/${token}/download`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (res.status === 403) throw new Error("EMAIL_MISMATCH");
  if (res.status === 410) throw new Error("LINK_EXPIRED");
  if (!res.ok) throw new Error("Access failed");
  const data = (await res.json()) as {
    scope: string;
    case: {
      id: string; case_number: string; title: string; description: string | null;
      status: string; priority: string; category: string | null;
      member_count: number;
      members: Array<{ full_name: string; role: string; department: string | null }>;
      created_at: string;
    };
    documents: SharedDocMetaDto[];
  };
  return {
    case: {
      id: data.case.id,
      caseNumber: data.case.case_number,
      title: data.case.title,
      description: data.case.description,
      status: data.case.status,
      priority: data.case.priority,
      category: data.case.category,
      memberCount: data.case.member_count,
      members: data.case.members.map((m) => ({
        fullName: m.full_name,
        role: m.role,
        department: m.department,
      })),
      createdAt: data.case.created_at,
    },
    documents: data.documents.map(toSharedDoc),
  };
}

/** Download an individual file from a CASE scope share. Returns Blob. */
export async function downloadShareFile(
  token: string,
  docId: string,
  email: string
): Promise<{ blob: Blob; filename: string }> {
  const res = await fetch(`${BASE}/share/${token}/file/${docId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (res.status === 403) throw new Error("EMAIL_MISMATCH");
  if (res.status === 410) throw new Error("LINK_EXPIRED");
  if (!res.ok) throw new Error("Download failed");
  const cd = res.headers.get("Content-Disposition") ?? "";
  const filenameMatch = cd.match(/filename="([^"]+)"/);
  const filename = filenameMatch ? filenameMatch[1] : "document";
  return { blob: await res.blob(), filename };
}

// ── Preview (public, no auth) ─────────────────────────────────────────────────────

export interface SharePreview {
  document_id: string;
  mode: "pages" | "text";
  pages_png_base64: string[];
  text: string | null;
  page_count: number;
  truncated: boolean;
  filename: string;
  mime_type: string;
}

/** Preview a DOCUMENT-scope share link. Does not consume a use. */
export async function previewShareDocument(token: string, email: string | null): Promise<SharePreview> {
  const res = await fetch(`${BASE}/share/${token}/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (res.status === 403) throw new Error("EMAIL_MISMATCH");
  if (res.status === 410) throw new Error("LINK_EXPIRED");
  if (!res.ok) throw new Error("Preview failed");
  return res.json() as Promise<SharePreview>;
}

/** Preview one file from a CASE-scope share link. Does not consume a use. */
export async function previewShareFile(token: string, docId: string, email: string | null): Promise<SharePreview> {
  const res = await fetch(`${BASE}/share/${token}/file/${docId}/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (res.status === 403) throw new Error("EMAIL_MISMATCH");
  if (res.status === 410) throw new Error("LINK_EXPIRED");
  if (!res.ok) throw new Error("Preview failed");
  return res.json() as Promise<SharePreview>;
}

// ── DTO converters ───────────────────────────────────────────────────────────────

interface ShareLinkDto {
  id: string;
  share_scope: string;
  document_id: string | null;
  case_id: string | null;
  allowed_email: string | null;
  expires_at: string;
  max_uses: number;
  use_count: number;
  is_revoked: boolean;
  is_expired: boolean;
  note: string | null;
  created_at: string;
}

function toShareLink(dto: ShareLinkDto): ShareLink {
  return {
    id: dto.id,
    shareScope: dto.share_scope as ShareLink["shareScope"],
    documentId: dto.document_id,
    caseId: dto.case_id,
    allowedEmail: dto.allowed_email,
    expiresAt: dto.expires_at,
    maxUses: dto.max_uses,
    useCount: dto.use_count,
    isRevoked: dto.is_revoked,
    isExpired: dto.is_expired,
    note: dto.note,
    createdAt: dto.created_at,
  };
}

interface SharedDocMetaDto {
  id: string;
  filename: string;
  doc_type: string;
  file_size_bytes: number;
  mime_type: string;
  tags: string[];
  ocr_status: string;
  ocr_confidence: number | null;
  ocr_page_count: number | null;
  ocr_formatted_text: string | null;
  created_at: string;
}

function toSharedDoc(dto: SharedDocMetaDto): SharedDocMeta {
  return {
    id: dto.id,
    filename: dto.filename,
    docType: dto.doc_type,
    fileSizeBytes: dto.file_size_bytes,
    mimeType: dto.mime_type,
    tags: dto.tags,
    ocrStatus: dto.ocr_status,
    ocrConfidence: dto.ocr_confidence,
    ocrPageCount: dto.ocr_page_count,
    ocrFormattedText: dto.ocr_formatted_text ?? null,
    createdAt: dto.created_at,
  };
}
