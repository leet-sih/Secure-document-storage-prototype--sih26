/**
 * useSignatures — API calls for document digital signatures.
 *
 * sign(docId)               POST /documents/{id}/sign
 * listSignatures(docId)     GET  /documents/{id}/signatures
 * verifySignatures(docId)   POST /documents/{id}/signatures/verify
 * revokeSignature(docId, sigId)  DELETE /documents/{id}/signatures/{sig_id}
 */

import { useState, useCallback } from "react";
import { apiFetch } from "../lib/apiClient";

export interface SignerBrief {
  id: string;
  full_name: string;
  role: string;
  email: string;
}

export interface Signature {
  id: string;
  document_id: string;
  signer: SignerBrief;
  signed_at: string;
  is_valid: boolean | null;
  last_verified_at: string | null;
  revoked_at: string | null;
}

export interface VerifyResult {
  signature_id: string;
  signer_email: string;
  is_valid: boolean;
  reason?: string;
}

export interface VerifyResponse {
  document_id: string;
  verified_at: string;
  results: VerifyResult[];
}

export function useSignatures(docId: string) {
  const [signatures, setSignatures] = useState<Signature[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clearError = () => setError(null);

  const listSignatures = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = (await apiFetch(`/documents/${docId}/signatures`)) as {
        document_id: string;
        signatures: Signature[];
      };
      setSignatures(data.signatures);
      return data.signatures;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to load signatures";
      setError(msg);
      return [];
    } finally {
      setLoading(false);
    }
  }, [docId]);

  const sign = useCallback(async (): Promise<Signature | null> => {
    setLoading(true);
    setError(null);
    try {
      const sig = (await apiFetch(`/documents/${docId}/sign`, {
        method: "POST",
      })) as Signature;
      setSignatures((prev) => [sig, ...prev]);
      return sig;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to sign document";
      setError(msg);
      return null;
    } finally {
      setLoading(false);
    }
  }, [docId]);

  const verifySignatures = useCallback(async (): Promise<VerifyResponse | null> => {
    setLoading(true);
    setError(null);
    try {
      const result = (await apiFetch(`/documents/${docId}/signatures/verify`, {
        method: "POST",
      })) as VerifyResponse;
      // Refresh list to pick up updated is_valid values
      await listSignatures();
      return result;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Failed to verify signatures";
      setError(msg);
      return null;
    } finally {
      setLoading(false);
    }
  }, [docId, listSignatures]);

  const revokeSignature = useCallback(
    async (sigId: string): Promise<boolean> => {
      setLoading(true);
      setError(null);
      try {
        await apiFetch(`/documents/${docId}/signatures/${sigId}`, {
          method: "DELETE",
        });
        setSignatures((prev) =>
          prev.map((s) =>
            s.id === sigId ? { ...s, revoked_at: new Date().toISOString(), is_valid: false } : s
          )
        );
        return true;
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : "Failed to revoke signature";
        setError(msg);
        return false;
      } finally {
        setLoading(false);
      }
    },
    [docId]
  );

  return {
    signatures,
    loading,
    error,
    clearError,
    listSignatures,
    sign,
    verifySignatures,
    revokeSignature,
  };
}
