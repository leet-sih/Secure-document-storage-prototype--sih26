/**
 * documentApi.ts — typed fetch wrappers for document endpoints.
 * Mirrors the pattern in caseApi.ts: raw snake_case DTOs are converted
 * to camelCase DocumentMeta before being returned to components.
 */

import { apiFetch } from "./apiClient";
import type { DocType, DocumentMeta } from "../types";

const TOKEN_KEY = "dms_access_token";
const BASE = "/api/v1";

// ── Raw API response shape (snake_case from Flask/marshmallow) ─────────────────

export interface DocumentDto {
  id: string;
  case_id: string | null;
  filename: string;
  title: string | null;
  mime_type: string;
  doc_type: string;
  file_size_bytes: number;
  total_chunks: number;
  integrity_hash?: string | null;
  tags: string[];
  status: string;
  uploaded_by: string;
  uploaded_by_name?: string | null;
  created_at: string;
  ocr_status?: string;
  ocr_confidence?: number | null;
  ocr_raw_text?: string | null;
  ocr_formatted_text?: string | null;
  ocr_page_count?: number | null;
  ocr_detail?: string | null;
}

// ── Converter ─────────────────────────────────────────────────────────────────

export function toDocumentMeta(dto: DocumentDto): DocumentMeta {
  return {
    id: dto.id,
    caseId: dto.case_id,
    filename: dto.filename,
    docType: dto.doc_type as DocType,
    fileSizeBytes: dto.file_size_bytes,
    totalChunks: dto.total_chunks,
    integrityHash: dto.integrity_hash ?? null,
    tags: dto.tags ?? [],
    status: dto.status,
    createdAt: dto.created_at,
    uploadedByName: dto.uploaded_by_name ?? null,
    ocrStatus: dto.ocr_status,
    ocrConfidence: dto.ocr_confidence ?? null,
    ocrRawText: dto.ocr_raw_text ?? null,
    ocrFormattedText: dto.ocr_formatted_text ?? null,
    ocrPageCount: dto.ocr_page_count ?? null,
    ocrDetail: dto.ocr_detail ?? null,
  };
}

// ── API helpers ───────────────────────────────────────────────────────────────

export async function fetchCaseDocs(caseId: string): Promise<DocumentMeta[]> {
  const dtos = (await apiFetch(`/cases/${caseId}/documents`)) as DocumentDto[];
  return dtos.map(toDocumentMeta);
}

export async function fetchPersonalDocs(): Promise<DocumentMeta[]> {
  const dtos = (await apiFetch("/me/documents")) as DocumentDto[];
  return dtos.map(toDocumentMeta);
}

export async function generateOcr(docId: string, force = false): Promise<DocumentMeta> {
  const dto = (await apiFetch(`/documents/${docId}/ocr`, {
    method: "POST",
    body: JSON.stringify({ force }),
  })) as DocumentDto;
  return toDocumentMeta(dto);
}

export async function approveOcr(docId: string, action: "approve" | "dismiss"): Promise<DocumentMeta> {
  const dto = (await apiFetch(`/documents/${docId}/ocr/approve`, {
    method: "POST",
    body: JSON.stringify({ action }),
  })) as DocumentDto;
  return toDocumentMeta(dto);
}

export async function deleteDocument(docId: string, totpCode: string): Promise<void> {
  await apiFetch(`/documents/${docId}`, {
    method: "DELETE",
    body: JSON.stringify({ totp_code: totpCode }),
  });
}

/** Verify chunk hashes + GCM tags server-side without downloading the file. */
export async function checkDocumentIntegrity(docId: string): Promise<void> {
  await apiFetch(`/documents/${docId}/check-integrity`, { method: "POST" });
}

/** Fetch a document's decrypted bytes with auth and trigger a browser save-as. */
export async function downloadDocument(docId: string, filename: string): Promise<void> {
  const token = localStorage.getItem(TOKEN_KEY);
  const res = await fetch(`${BASE}/documents/${docId}/download`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { error?: { message?: string } };
    throw new Error(body.error?.message ?? "Download failed");
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
