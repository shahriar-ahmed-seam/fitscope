"use client";

import { AlertCircle, Gauge, Sparkles, Wand2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, analyzeFile, analyzeText, fetchQuota } from "@/lib/api";
import { SAMPLE_COMPANY, SAMPLE_JD, SAMPLE_RESUME, SAMPLE_ROLE } from "@/lib/samples";
import type { AnalysisReport, QuotaResponse } from "@/lib/types";
import { ReportView } from "@/components/report/ReportView";
import { cn } from "@/components/ui/Primitives";

import { ResumeInput, type ResumeMode } from "./ResumeInput";
import { RunProgress } from "./RunProgress";

const MIN_RESUME_CHARS = 80;
const MIN_JD_CHARS = 60;

export function AnalyzerPanel() {
  const [mode, setMode] = useState<ResumeMode>("paste");
  const [file, setFile] = useState<File | null>(null);
  const [resumeText, setResumeText] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [roleTitle, setRoleTitle] = useState("");
  const [company, setCompany] = useState("");
  const [fastMode, setFastMode] = useState(false);

  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [quota, setQuota] = useState<QuotaResponse | null>(null);

  const resultRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const loadQuota = useCallback(() => {
    fetchQuota()
      .then(setQuota)
      .catch(() => setQuota(null));
  }, []);

  useEffect(() => {
    loadQuota();
    return () => abortRef.current?.abort();
  }, [loadQuota]);

  const resumeReady = mode === "upload" ? Boolean(file) : resumeText.trim().length >= MIN_RESUME_CHARS;
  const jdReady = jobDescription.trim().length >= MIN_JD_CHARS;
  const canRun = resumeReady && jdReady && !running;

  function loadSample() {
    setMode("paste");
    setFile(null);
    setResumeText(SAMPLE_RESUME);
    setJobDescription(SAMPLE_JD);
    setRoleTitle(SAMPLE_ROLE);
    setCompany(SAMPLE_COMPANY);
    setError(null);
  }

  function reset() {
    setReport(null);
    setError(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!canRun) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setRunning(true);
    setError(null);
    setReport(null);

    try {
      const shared = {
        jobDescription: jobDescription.trim(),
        roleTitle: roleTitle.trim() || undefined,
        company: company.trim() || undefined,
        fastMode,
      };
      const result =
        mode === "upload" && file
          ? await analyzeFile({ ...shared, file }, controller.signal)
          : await analyzeText({ ...shared, resumeText: resumeText.trim() }, controller.signal);

      setReport(result);
      window.setTimeout(
        () => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }),
        80,
      );
    } catch (caught) {
      if (caught instanceof DOMException && caught.name === "AbortError") return;
      if (caught instanceof ApiError) {
        setError(caught.message);
      } else {
        setError(
          "Could not reach the analysis API. If you are running locally, start the backend on the port in NEXT_PUBLIC_API_BASE_URL.",
        );
      }
    } finally {
      setRunning(false);
      loadQuota();
    }
  }

  return (
    <div className="space-y-6">
      {!report ? (
        <form onSubmit={handleSubmit} className="panel p-6 lg:p-8">
          <div className="grid gap-6 lg:grid-cols-2">
            <ResumeInput
              mode={mode}
              onModeChange={setMode}
              file={file}
              onFileChange={setFile}
              text={resumeText}
              onTextChange={setResumeText}
              disabled={running}
            />

            <div>
              <div className="mb-2.5 flex items-center justify-between">
                <label className="label" htmlFor="job-description">
                  Job description
                </label>
                <button
                  type="button"
                  onClick={loadSample}
                  disabled={running}
                  className="inline-flex items-center gap-1.5 text-xs font-medium text-accent underline-offset-4 hover:underline"
                >
                  <Wand2 className="h-3.5 w-3.5" />
                  Load a sample pair
                </button>
              </div>
              <textarea
                id="job-description"
                value={jobDescription}
                onChange={(event) => setJobDescription(event.target.value)}
                disabled={running}
                rows={12}
                spellCheck={false}
                placeholder="Paste the full job posting: requirements, responsibilities, nice-to-haves."
                className="field resize-y font-mono text-[13px] leading-relaxed"
              />
            </div>
          </div>

          <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <label className="label mb-1.5 block" htmlFor="role-title">
                Role title (optional)
              </label>
              <input
                id="role-title"
                value={roleTitle}
                onChange={(event) => setRoleTitle(event.target.value)}
                disabled={running}
                placeholder="Senior Backend Engineer"
                className="field py-2.5"
              />
            </div>
            <div>
              <label className="label mb-1.5 block" htmlFor="company">
                Company (optional)
              </label>
              <input
                id="company"
                value={company}
                onChange={(event) => setCompany(event.target.value)}
                disabled={running}
                placeholder="Northwind Intelligence"
                className="field py-2.5"
              />
            </div>

            <label
              className={cn(
                "flex cursor-pointer items-start gap-2.5 rounded-xl border border-white/10 bg-ink-950/50 px-3.5 py-3 transition hover:border-white/20",
                running && "cursor-not-allowed opacity-60",
              )}
            >
              <input
                type="checkbox"
                checked={fastMode}
                onChange={(event) => setFastMode(event.target.checked)}
                disabled={running}
                className="mt-0.5 h-4 w-4 rounded border-white/20 bg-transparent accent-accent"
              />
              <span>
                <span className="flex items-center gap-1.5 text-sm font-medium text-slate-200">
                  <Gauge className="h-3.5 w-3.5 text-accent" />
                  Fast mode
                </span>
                <span className="mt-0.5 block text-xs text-slate-500">
                  Skip rewrite drafting. Scores and evidence only.
                </span>
              </span>
            </label>

            <div className="flex flex-col justify-end gap-2">
              <button type="submit" disabled={!canRun} className="btn-primary w-full py-3">
                <Sparkles className="h-4 w-4" />
                {running ? "Analysing..." : "Analyse fit"}
              </button>
              <p className="text-center text-[11px] text-slate-600">
                {quota && !quota.unlimited
                  ? `${quota.remaining ?? 0} of ${quota.limit} free runs left today`
                  : "No sign-up required"}
              </p>
            </div>
          </div>

          {!resumeReady || !jdReady ? (
            <p className="mt-4 text-xs text-slate-600">
              {mode === "upload" && !file
                ? "Add a resume file to continue."
                : !resumeReady
                  ? "Paste at least a few lines of your resume."
                  : "Paste the job description to continue."}
            </p>
          ) : null}
        </form>
      ) : null}

      {error ? (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-xl border border-rose-500/25 bg-rose-500/[0.07] px-4 py-3.5"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" aria-hidden="true" />
          <p className="text-sm leading-relaxed text-rose-100">{error}</p>
        </div>
      ) : null}

      {running ? <RunProgress fastMode={fastMode} /> : null}

      <div ref={resultRef}>
        {report ? <ReportView report={report} onReset={reset} /> : null}
      </div>
    </div>
  );
}
