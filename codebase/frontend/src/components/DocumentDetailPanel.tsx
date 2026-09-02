/**
 * DocumentDetailPanel — case Documents tab slide-in (design §6.5 / §7.6).
 *
 * Unmounted until CaseDetailPage exists. Fetches metadata + server preview.
 * Download / Sign / Share are disabled (other branches). Text preview is a <pre>.
 */

import { useEffect } from "react";

import { useDocumentPreview } from "../hooks/useDocumentPreview";

export interface DocumentDetailPanelProps {
  documentId: string;
  onClose: () => void;
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DocumentDetailPanel({ documentId, onClose }: DocumentDetailPanelProps) {
  const { meta, preview, loading, error } = useDocumentPreview(documentId);

  useEffect(() => {
    function onKey(ev: KeyboardEvent) {
      if (ev.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-40 flex justify-end bg-black/60">
      <aside
        className="flex h-full w-full max-w-[400px] flex-col border-l border-[#2a2d35] bg-[#111318]"
        role="dialog"
        aria-modal="true"
        aria-label={meta?.filename ?? "Document"}
      >
        <header className="flex items-center gap-2 border-b border-[#2a2d35] px-4 py-3">
          <button
            type="button"
            title="Close"
            aria-label="Close"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded text-[#8b8fa8] hover:bg-[#1a1d24] hover:text-[#e8eaf0]"
          >
            ×
          </button>
          <div className="truncate font-mono text-[13px] text-[#e8eaf0]" title={meta?.filename}>
            {meta?.filename ?? "Document"}
          </div>
        </header>

        <div className="flex-1 overflow-y-auto px-4 py-4 text-[13px] text-[#e8eaf0]">
          {loading ? <div className="text-[#8b8fa8]">Loading…</div> : null}

          {meta ? (
            <dl className="grid grid-cols-[88px_1fr] gap-y-2 text-[#8b8fa8]">
              <dt>Type</dt>
              <dd className="text-[#e8eaf0]">{meta.doc_type}</dd>
              <dt>Size</dt>
              <dd className="text-[#e8eaf0]">{formatBytes(meta.file_size_bytes)}</dd>
              <dt>Chunks</dt>
              <dd className="text-[#e8eaf0]">{meta.total_chunks}</dd>
              <dt>Status</dt>
              <dd className="text-[#e8eaf0]">{meta.status}</dd>
              <dt>Tags</dt>
              <dd className="text-[#e8eaf0]">
                {meta.tags?.length ? meta.tags.map((t) => `[${t}]`).join(" ") : "—"}
              </dd>
              <dt>Uploaded by</dt>
              <dd className="truncate font-mono text-xs text-[#e8eaf0]" title={meta.uploaded_by}>
                {meta.uploaded_by}
              </dd>
              <dt>Uploaded</dt>
              <dd className="text-[#e8eaf0]">{meta.created_at}</dd>
            </dl>
          ) : null}

          <div className="mt-5 border-t border-[#2a2d35] pt-4">
            <div className="mb-2 text-xs uppercase tracking-wide text-[#555869]">Preview</div>
            {error ? (
              <div className="rounded-md border border-[#ef4444] bg-[#3d1010] px-3 py-2.5 text-[#e8eaf0]">
                {error}
              </div>
            ) : null}
            {preview?.mode === "text" && preview.text != null ? (
              <pre className="max-h-[360px] overflow-auto whitespace-pre-wrap break-words rounded-md border border-[#2a2d35] bg-[#1e2028] p-3 font-mono text-xs text-[#e8eaf0]">
                {preview.text}
              </pre>
            ) : null}
            {preview?.mode === "pages"
              ? preview.pages_png_base64.map((b64, i) => (
                  <img
                    key={i}
                    alt={`Page ${i + 1}`}
                    src={`data:image/png;base64,${b64}`}
                    className="mb-2 w-full rounded-md border border-[#2a2d35]"
                  />
                ))
              : null}
            {preview?.truncated ? (
              <div className="mt-2 text-xs text-[#8b8fa8]">Preview truncated.</div>
            ) : null}
          </div>
        </div>

        <footer className="flex gap-2 border-t border-[#2a2d35] px-4 py-3">
          <button
            type="button"
            disabled
            className="h-[34px] rounded bg-[#3b82f6] px-3 text-sm text-white opacity-50"
          >
            Download
          </button>
          <button
            type="button"
            disabled
            className="h-[34px] rounded border border-[#2a2d35] bg-[#1a1d24] px-3 text-sm text-[#e8eaf0] opacity-50"
          >
            Sign
          </button>
          <button
            type="button"
            disabled
            className="h-[34px] rounded border border-[#2a2d35] bg-[#1a1d24] px-3 text-sm text-[#e8eaf0] opacity-50"
          >
            Share
          </button>
        </footer>
      </aside>
    </div>
  );
}
