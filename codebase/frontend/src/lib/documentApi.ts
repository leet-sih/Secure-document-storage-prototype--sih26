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
  tags: string[];
  status: string;
  uploaded_by: string;
  created_at: string;
}

// ── Converter ─────────────────────────────────────────────────────────────────

export function toDocumentMeta(dto: DocumentDto): DocumentMeta {
  return {
    id: dto.id,
    caseId: dto.case_id,
    filename: dto.filename,
    docType: dto.doc_type as DocType,
    fileSizeBytes: dto.file_size_bytes,
    tags: dto.tags ?? [],
    status: dto.status,
    createdAt: dto.created_at,
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
