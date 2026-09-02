/**
 * useDocumentPreview — GET /documents/:id + GET /documents/:id/preview.
 * State is dropped when documentId changes or the consumer unmounts.
 */

import { useCallback, useEffect, useState } from "react";

import { apiFetch } from "../lib/apiClient";
import type { DocumentMetaApi, DocumentPreview } from "../types";

export function useDocumentPreview(documentId: string | null) {
  const [meta, setMeta] = useState<DocumentMetaApi | null>(null);
  const [preview, setPreview] = useState<DocumentPreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const reload = useCallback(async () => {
    if (!documentId) {
      setMeta(null);
      setPreview(null);
      setError("");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    setPreview(null);
    try {
      const nextMeta = (await apiFetch(`/documents/${documentId}`)) as DocumentMetaApi;
      setMeta(nextMeta);
      try {
        const nextPreview = (await apiFetch(`/documents/${documentId}/preview`)) as DocumentPreview;
        setPreview(nextPreview);
      } catch (previewErr) {
        setError(previewErr instanceof Error ? previewErr.message : "Preview failed");
      }
    } catch (metaErr) {
      setMeta(null);
      setError(metaErr instanceof Error ? metaErr.message : "Not found");
    } finally {
      setLoading(false);
    }
  }, [documentId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { meta, preview, loading, error, reload };
}
