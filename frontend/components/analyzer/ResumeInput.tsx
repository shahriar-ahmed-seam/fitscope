"use client";

import { FileText, Trash2, Upload } from "lucide-react";
import { useCallback, useRef, useState } from "react";

import { cn } from "@/components/ui/Primitives";

const ACCEPTED = ".pdf,.docx,.doc,.txt,.md";

export type ResumeMode = "upload" | "paste";

export function ResumeInput({
  mode,
  onModeChange,
  file,
  onFileChange,
  text,
  onTextChange,
  disabled,
}: {
  mode: ResumeMode;
  onModeChange: (mode: ResumeMode) => void;
  file: File | null;
  onFileChange: (file: File | null) => void;
  text: string;
  onTextChange: (text: string) => void;
  disabled?: boolean;
}) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      setDragging(false);
      if (disabled) return;
      const dropped = event.dataTransfer.files?.[0];
      if (dropped) {
        onFileChange(dropped);
        onModeChange("upload");
      }
    },
    [disabled, onFileChange, onModeChange],
  );

  return (
    <div>
      <div className="mb-2.5 flex items-center justify-between">
        <label className="label" htmlFor={mode === "paste" ? "resume-text" : undefined}>
          Your resume
        </label>
        <div className="flex gap-1 rounded-lg border border-white/10 p-0.5" role="tablist">
          {(["upload", "paste"] as ResumeMode[]).map((option) => (
            <button
              key={option}
              type="button"
              role="tab"
              aria-selected={mode === option}
              onClick={() => onModeChange(option)}
              disabled={disabled}
              className={cn(
                "rounded-md px-2.5 py-1 text-xs font-medium capitalize transition",
                mode === option ? "bg-accent/15 text-accent" : "text-slate-500 hover:text-slate-300",
              )}
            >
              {option}
            </button>
          ))}
        </div>
      </div>

      {mode === "upload" ? (
        <div
          onDragOver={(event) => {
            event.preventDefault();
            if (!disabled) setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          className={cn(
            "flex flex-col items-center justify-center rounded-xl border border-dashed px-4 py-8 text-center transition",
            dragging ? "border-accent/60 bg-accent/[0.06]" : "border-white/12 bg-ink-950/50",
            disabled && "opacity-60",
          )}
        >
          {file ? (
            <>
              <FileText className="h-6 w-6 text-accent" aria-hidden="true" />
              <p className="mt-2 max-w-full truncate text-sm font-medium text-slate-100">
                {file.name}
              </p>
              <p className="mt-0.5 text-xs text-slate-500">{(file.size / 1024).toFixed(0)} KB</p>
              <button
                type="button"
                onClick={() => onFileChange(null)}
                disabled={disabled}
                className="mt-3 inline-flex items-center gap-1.5 text-xs text-slate-500 transition hover:text-rose-300"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Remove
              </button>
            </>
          ) : (
            <>
              <Upload className="h-6 w-6 text-slate-500" aria-hidden="true" />
              <p className="mt-2 text-sm text-slate-300">Drop a PDF or DOCX here</p>
              <button
                type="button"
                onClick={() => inputRef.current?.click()}
                disabled={disabled}
                className="mt-2 text-xs font-medium text-accent underline-offset-4 hover:underline"
              >
                or browse files
              </button>
              <p className="mt-3 text-[11px] text-slate-600">
                PDF, DOCX, TXT up to 2.5 MB. The file is parsed and discarded, never stored.
              </p>
            </>
          )}
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED}
            className="sr-only"
            aria-label="Resume file"
            onChange={(event) => onFileChange(event.target.files?.[0] ?? null)}
          />
        </div>
      ) : (
        <textarea
          id="resume-text"
          value={text}
          onChange={(event) => onTextChange(event.target.value)}
          disabled={disabled}
          rows={12}
          spellCheck={false}
          placeholder="Paste the full text of your resume, including bullet points and dates."
          className="field resize-y font-mono text-[13px] leading-relaxed"
        />
      )}
    </div>
  );
}
