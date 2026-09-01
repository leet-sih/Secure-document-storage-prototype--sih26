import { useEffect, useRef, useState, type DragEvent, type FormEvent } from "react";
import { Camera, CheckCircle } from "lucide-react";

import { toDocumentMeta, type DocumentDto } from "../lib/documentApi";
import type { DocType, DocumentMeta } from "../types";

const TOKEN_KEY = "dms_access_token";
const MAX_BYTES = 500 * 1024 * 1024;

const ALLOWED_EXT = new Set([
  ".pdf",
  ".docx",
  ".xlsx",
  ".jpg",
  ".jpeg",
  ".png",
  ".tiff",
  ".tif",
  ".mp4",
  ".wav",
]);

const OCR_EXT = new Set([".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif"]);

const DOC_TYPES: { value: DocType; label: string }[] = [
  { value: "EVIDENCE_RECORD", label: "Evidence record" },
  { value: "FIR", label: "FIR" },
  { value: "FORENSIC_REPORT", label: "Forensic report" },
  { value: "WITNESS_STATEMENT", label: "Witness statement" },
  { value: "CHARGE_SHEET", label: "Charge sheet" },
  { value: "COURT_FILING", label: "Court filing" },
  { value: "POLICE_REPORT", label: "Police report" },
  { value: "INVESTIGATION_RECORD", label: "Investigation record" },
  { value: "LEGAL_NOTICE", label: "Legal notice" },
  { value: "JUDGMENT", label: "Judgment" },
  { value: "OTHER", label: "Other" },
];

type Phase = "idle" | "uploading" | "done" | "error";

export interface DocumentUploaderProps {
  uploadUrl?: string;
  caseId?: string;
  onUploaded?: (doc: DocumentMeta) => void;
}

function extOf(name: string): string {
  const i = name.lastIndexOf(".");
  return i >= 0 ? name.slice(i).toLowerCase() : "";
}

function fmtBytes(n: number): string {
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export default function DocumentUploader({ uploadUrl, caseId, onUploaded }: DocumentUploaderProps) {
  const resolvedUrl = uploadUrl ?? `/api/v1/cases/${caseId}/documents`;
  const browseRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);
  const xhrRef = useRef<XMLHttpRequest | null>(null);

  const [file, setFile] = useState<File | null>(null);
  const [docType, setDocType] = useState<DocType>("EVIDENCE_RECORD");
  const [tags, setTags] = useState("");
  const [autoOcr, setAutoOcr] = useState(false);
  const [phase, setPhase] = useState<Phase>("idle");
  const [pct, setPct] = useState(0);
  const [error, setError] = useState("");
  const [uploadedName, setUploadedName] = useState("");
  const [dragOver, setDragOver] = useState(false);

  const fileSupportsOcr = file ? OCR_EXT.has(extOf(file.name)) : false;

  // Auto-reset to idle 5 s after a successful upload
  useEffect(() => {
    if (phase !== "done") return;
    const t = setTimeout(resetForm, 5000);
    return () => clearTimeout(t);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  function resetForm() {
    setPhase("idle");
    setFile(null);
    setAutoOcr(false);
    setPct(0);
    setError("");
    setUploadedName("");
    if (browseRef.current) browseRef.current.value = "";
    if (cameraRef.current) cameraRef.current.value = "";
  }

  function pick(next: File | null, fromCamera = false) {
    setError("");
    setPhase("idle");
    if (!next) { setFile(null); setAutoOcr(false); return; }
    if (next.size > MAX_BYTES) { setError("Maximum 500 MB per file"); setFile(null); return; }
    const ext = extOf(next.name);
    if (!ALLOWED_EXT.has(ext)) { setError("PDF, DOCX, XLSX, JPG, PNG, TIFF, MP4, WAV only"); setFile(null); return; }
    setFile(next);
    // Camera captures are always images — pre-enable OCR since that's the intent
    if (fromCamera && OCR_EXT.has(ext)) setAutoOcr(true);
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragOver(false);
    pick(e.dataTransfer.files[0] ?? null);
  }

  function cancel() {
    xhrRef.current?.abort();
    xhrRef.current = null;
    setPhase("idle");
    setPct(0);
  }

  function start(e: FormEvent) {
    e.preventDefault();
    if (!file) { setError("Choose a file"); return; }
    const token = localStorage.getItem(TOKEN_KEY);
    const body = new FormData();
    body.append("file", file);
    body.append("doc_type", docType);
    for (const tag of tags.split(",").map((t) => t.trim().toLowerCase()).filter(Boolean)) {
      body.append("tags", tag);
    }
    if (autoOcr && fileSupportsOcr) body.append("auto_ocr", "true");

    const xhr = new XMLHttpRequest();
    xhrRef.current = xhr;
    setPhase("uploading");
    setPct(0);
    setError("");

    xhr.upload.onprogress = (ev) => {
      if (ev.lengthComputable) setPct(Math.round((ev.loaded / ev.total) * 100));
    };
    xhr.onerror = () => { setPhase("error"); setError("Upload failed"); };
    xhr.onabort = () => { setPhase("idle"); };
    xhr.onload = () => {
      if (xhr.status === 201) {
        setUploadedName(file.name);
        setPhase("done");
        setPct(100);
        try {
          const dto = JSON.parse(xhr.responseText) as DocumentDto;
          onUploaded?.(toDocumentMeta(dto));
        } catch { /* metadata optional */ }
        return;
      }
      setPhase("error");
      try {
        const parsed = JSON.parse(xhr.responseText) as { error?: { message?: string } };
        setError(parsed.error?.message ?? "Upload failed");
      } catch { setError("Upload failed"); }
    };

    xhr.open("POST", resolvedUrl);
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.send(body);
  }

  // ── Success banner (replaces entire form content) ──────────────────────────
  if (phase === "done") {
    return (
      <div className="flex items-center gap-3 rounded-lg border border-[#22c55e] bg-[#14391f] px-4 py-3.5">
        <CheckCircle size={20} className="shrink-0 text-[#22c55e]" />
        <div className="min-w-0 flex-1">
          <div className="text-[13px] font-medium text-[#22c55e]">Uploaded successfully</div>
          <div className="truncate font-mono text-[11px] text-[#8b8fa8]">{uploadedName}</div>
        </div>
        <button
          type="button"
          onClick={resetForm}
          className="shrink-0 whitespace-nowrap text-[12px] text-[#3b82f6] hover:text-[#93c5fd]"
        >
          Upload another
        </button>
      </div>
    );
  }

  // ── Normal form ────────────────────────────────────────────────────────────
  const zoneActive = dragOver || !!file;

  return (
    <form
      onSubmit={start}
      className="flex flex-col gap-4 rounded-lg border border-[#2a2d35] bg-[#111318] p-5"
    >
      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => !file && browseRef.current?.click()}
        style={{ cursor: file ? "default" : "pointer" }}
        className={[
          "flex flex-col items-center gap-2 rounded-lg border px-4 py-6 text-center transition-colors",
          zoneActive
            ? "border-[#3b82f6] bg-[#0d1929]"
            : "border-dashed border-[#3a3d47] bg-[#14161c]",
        ].join(" ")}
      >
        {file ? (
          /* Selected file indicator */
          <div className="flex w-full items-center gap-3 rounded-md border border-[#2a2d35] bg-[#1a1d24] px-3 py-2.5">
            <div className="min-w-0 flex-1 text-left">
              <div className="truncate font-mono text-[12px] text-[#e8eaf0]">{file.name}</div>
              <div className="mt-0.5 text-[11px] text-[#555869]">{fmtBytes(file.size)} · ready to upload</div>
            </div>
            <button
              type="button"
              aria-label="Remove file"
              onClick={(e) => { e.stopPropagation(); pick(null); }}
              className="shrink-0 text-[#555869] hover:text-[#e8eaf0]"
            >
              ×
            </button>
          </div>
        ) : (
          <>
            <div className="text-2xl text-[#3b82f6]" aria-hidden>↑</div>
            <div className="text-sm text-[#e8eaf0]">Drag & drop files here</div>
            <div className="text-xs text-[#8b8fa8]">PDF, DOCX, XLSX, JPG, PNG, TIFF, MP4, WAV</div>
            <div className="text-[11px] text-[#555869]">Maximum 500 MB per file</div>
            <div className="mt-1 flex gap-2">
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); browseRef.current?.click(); }}
                className="h-[30px] rounded border border-[#2a2d35] bg-[#1a1d24] px-3 text-[12px] text-[#e8eaf0] hover:border-[#3b82f6] hover:text-[#3b82f6]"
              >
                Browse Files
              </button>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); cameraRef.current?.click(); }}
                className="flex h-[30px] items-center gap-1.5 rounded border border-[#2a2d35] bg-[#1a1d24] px-3 text-[12px] text-[#8b8fa8] hover:border-[#3b82f6] hover:text-[#3b82f6]"
              >
                <Camera size={13} />
                Scan Document
              </button>
            </div>
          </>
        )}

        {/* Hidden file inputs */}
        <input
          ref={browseRef}
          type="file"
          className="hidden"
          onChange={(ev) => pick(ev.target.files?.[0] ?? null)}
        />
        <input
          ref={cameraRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={(ev) => pick(ev.target.files?.[0] ?? null, true)}
        />
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-end gap-2.5">
        <label className="flex flex-col gap-1.5 text-xs text-[#8b8fa8]">
          Document type <span className="text-[#ef4444]">*</span>
          <select
            value={docType}
            onChange={(ev) => setDocType(ev.target.value as DocType)}
            className="h-[34px] min-w-[190px] rounded-md border border-[#2a2d35] bg-[#1e2028] px-2 text-[13px] text-[#e8eaf0]"
          >
            {DOC_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex min-w-[200px] flex-1 flex-col gap-1.5 text-xs text-[#8b8fa8]">
          Tags <span className="text-[#555869]">(optional)</span>
          <input
            value={tags}
            onChange={(ev) => setTags(ev.target.value)}
            placeholder="seizure, devices"
            className="h-[34px] rounded-md border border-[#2a2d35] bg-[#1e2028] px-2.5 text-[13px] text-[#e8eaf0]"
          />
        </label>
        {fileSupportsOcr && (
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: "7px",
              cursor: "pointer",
              fontSize: "13px",
              color: "#8b8fa8",
              userSelect: "none",
              paddingBottom: "2px",
            }}
          >
            <input
              type="checkbox"
              checked={autoOcr}
              onChange={(e) => setAutoOcr(e.target.checked)}
              style={{ accentColor: "#3b82f6", width: "15px", height: "15px" }}
            />
            Auto-OCR
          </label>
        )}
        <button
          type="submit"
          disabled={phase === "uploading" || !file}
          className="h-[34px] rounded bg-[#3b82f6] px-3.5 text-sm font-medium text-white hover:bg-[#2563eb] disabled:opacity-50"
        >
          Upload
        </button>
      </div>

      {/* Upload progress */}
      {phase === "uploading" && file ? (
        <div className="flex flex-col gap-2 rounded-md border border-[#2a2d35] bg-[#1a1d24] p-3">
          <div className="flex items-center gap-2 text-[13px] text-[#e8eaf0]">
            <span className="min-w-0 flex-1 truncate font-mono text-xs">{file.name}</span>
            <span className="shrink-0 text-xs text-[#8b8fa8]">{pct}%</span>
            <button
              type="button"
              title="Cancel upload"
              aria-label="Cancel upload"
              onClick={cancel}
              className="flex h-6 w-6 shrink-0 items-center justify-center rounded text-[#8b8fa8] hover:bg-[#1e2028] hover:text-[#e8eaf0]"
            >
              ×
            </button>
          </div>
          <div className="h-1 overflow-hidden rounded-sm bg-[#2a2d35]">
            <div className="h-1 bg-[#3b82f6] transition-[width] duration-150" style={{ width: `${pct}%` }} />
          </div>
        </div>
      ) : null}

      {/* Error */}
      {(phase === "error" || error) && phase !== "uploading" ? (
        <div className="rounded-md border border-[#ef4444] bg-[#3d1010] px-3 py-2.5 text-[13px] text-[#e8eaf0]">
          {error || "Upload failed"}
        </div>
      ) : null}
    </form>
  );
}
