"""
DocumentUploader — case Documents tab ingest UI (design/PRAMAAN Prototype.dc.html).

Unmounted until CaseDetailPage exists. POST multipart to /cases/:id/documents via XHR
(progress). Client checks type + 500 MB before send. Does not decrypt.
"""

import { useRef, useState, type DragEvent, type FormEvent } from "react";

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
  caseId: string;
  onUploaded?: (doc: DocumentMeta) => void;
}

function extOf(name: string): string {
  const i = name.lastIndexOf(".");
  return i >= 0 ? name.slice(i).toLowerCase() : "";
}

export default function DocumentUploader({ caseId, onUploaded }: DocumentUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const xhrRef = useRef<XMLHttpRequest | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [docType, setDocType] = useState<DocType>("EVIDENCE_RECORD");
  const [tags, setTags] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [pct, setPct] = useState(0);
  const [error, setError] = useState("");

  function pick(next: File | null) {
    setError("");
    setPhase("idle");
    if (!next) {
      setFile(null);
      return;
    }
    if (next.size > MAX_BYTES) {
      setError("Maximum 500 MB per file");
      setFile(null);
      return;
    }
    if (!ALLOWED_EXT.has(extOf(next.name))) {
      setError("PDF, DOCX, XLSX, JPG, PNG, TIFF, MP4, WAV only");
      setFile(null);
      return;
    }
    setFile(next);
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
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
    if (!file) {
      setError("Choose a file");
      return;
    }
    const token = localStorage.getItem(TOKEN_KEY);
    const body = new FormData();
    body.append("file", file);
    body.append("doc_type", docType);
    for (const tag of tags.split(",").map((t) => t.trim().toLowerCase()).filter(Boolean)) {
      body.append("tags", tag);
    }

    const xhr = new XMLHttpRequest();
    xhrRef.current = xhr;
    setPhase("uploading");
    setPct(0);
    setError("");

    xhr.upload.onprogress = (ev) => {
      if (ev.lengthComputable) setPct(Math.round((ev.loaded / ev.total) * 100));
    };
    xhr.onerror = () => {
      setPhase("error");
      setError("Upload failed");
    };
    xhr.onabort = () => {
      setPhase("idle");
    };
    xhr.onload = () => {
      if (xhr.status === 201) {
        setPhase("done");
        setPct(100);
        try {
          onUploaded?.(JSON.parse(xhr.responseText) as DocumentMeta);
        } catch {
          /* metadata optional for parent */
        }
        return;
      }
      setPhase("error");
      try {
        const parsed = JSON.parse(xhr.responseText) as { error?: { message?: string } };
        setError(parsed.error?.message ?? "Upload failed");
      } catch {
        setError("Upload failed");
      }
    };

    xhr.open("POST", `/api/v1/cases/${caseId}/documents`);
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.send(body);
  }

  return (
    <form
      onSubmit={start}
      className="flex flex-col gap-4 rounded-lg border border-[#2a2d35] bg-[#111318] p-5"
    >
      <div
        role="button"
        tabIndex={0}
        onKeyDown={(ev) => {
          if (ev.key === "Enter" || ev.key === " ") inputRef.current?.click();
        }}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={onDrop}
        className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-[#3a3d47] bg-[#14161c] px-4 py-7 text-center"
      >
        <div className="text-[#3b82f6]" aria-hidden>
          ↑
        </div>
        <div className="text-sm text-[#e8eaf0]">Drag & drop files here, or click to browse</div>
        <div className="text-xs text-[#8b8fa8]">PDF, DOCX, XLSX, JPG, PNG, TIFF, MP4, WAV</div>
        <div className="text-[11px] text-[#555869]">Maximum 500 MB per file</div>
        {file ? (
          <div className="font-mono text-xs text-[#e8eaf0]">{file.name}</div>
        ) : null}
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          onChange={(ev) => pick(ev.target.files?.[0] ?? null)}
        />
      </div>

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
        <button
          type="submit"
          disabled={phase === "uploading"}
          className="h-[34px] rounded bg-[#3b82f6] px-3.5 text-sm font-medium text-white hover:bg-[#2563eb] disabled:opacity-50"
        >
          Upload
        </button>
      </div>

      {phase === "uploading" && file ? (
        <div className="flex flex-col gap-2 rounded-md border border-[#2a2d35] bg-[#1a1d24] p-3">
          <div className="flex items-center gap-2 text-[13px] text-[#e8eaf0]">
            <span className="font-mono text-xs">{file.name}</span>
            <span className="ml-auto text-xs text-[#8b8fa8]">{pct}%</span>
            <button
              type="button"
              title="Cancel upload"
              aria-label="Cancel upload"
              onClick={cancel}
              className="flex h-6 w-6 items-center justify-center rounded text-[#8b8fa8] hover:bg-[#1e2028] hover:text-[#e8eaf0]"
            >
              ×
            </button>
          </div>
          <div className="h-1 overflow-hidden rounded-sm bg-[#2a2d35]">
            <div className="h-1 bg-[#3b82f6] transition-[width] duration-150" style={{ width: `${pct}%` }} />
          </div>
        </div>
      ) : null}

      {phase === "done" ? (
        <div className="flex items-center gap-2 rounded-md border border-[#22c55e] bg-[#14391f] px-3 py-2.5 text-[13px] text-[#e8eaf0]">
          Upload complete
        </div>
      ) : null}

      {(phase === "error" || error) && phase !== "uploading" ? (
        <div className="rounded-md border border-[#ef4444] bg-[#3d1010] px-3 py-2.5 text-[13px] text-[#e8eaf0]">
          {error || "Upload failed"}
        </div>
      ) : null}
    </form>
  );
}
