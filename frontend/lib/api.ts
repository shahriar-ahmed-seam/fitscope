import type { AnalysisReport, HealthResponse, QuotaResponse, ReportSummary } from "./types";

/** Browser-facing base URL. */
export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

/** Server-side base URL (can point at an internal address on the same network). */
export const SERVER_API_BASE = (
  process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? API_BASE
).replace(/\/$/, "");

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function unwrap<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") {
        detail = body.detail;
      } else if (Array.isArray(body?.detail) && body.detail[0]?.msg) {
        detail = body.detail.map((d: { msg: string }) => d.msg).join("; ");
      }
    } catch {
      // keep the generic message
    }
    throw new ApiError(detail, response.status);
  }
  return (await response.json()) as T;
}

export interface AnalyzeTextInput {
  resumeText: string;
  jobDescription: string;
  roleTitle?: string;
  company?: string;
  fastMode?: boolean;
}

export async function analyzeText(input: AnalyzeTextInput, signal?: AbortSignal) {
  const response = await fetch(`${API_BASE}/api/v1/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      resume_text: input.resumeText,
      job_description: input.jobDescription,
      role_title: input.roleTitle || null,
      company: input.company || null,
      fast_mode: input.fastMode ?? false,
      save: true,
    }),
    signal,
  });
  return unwrap<AnalysisReport>(response);
}

export interface AnalyzeFileInput extends Omit<AnalyzeTextInput, "resumeText"> {
  file: File;
}

export async function analyzeFile(input: AnalyzeFileInput, signal?: AbortSignal) {
  const form = new FormData();
  form.append("resume", input.file);
  form.append("job_description", input.jobDescription);
  if (input.roleTitle) form.append("role_title", input.roleTitle);
  if (input.company) form.append("company", input.company);
  form.append("fast_mode", String(input.fastMode ?? false));
  form.append("save", "true");

  const response = await fetch(`${API_BASE}/api/v1/analyze/upload`, {
    method: "POST",
    body: form,
    signal,
  });
  return unwrap<AnalysisReport>(response);
}

export async function fetchQuota() {
  return unwrap<QuotaResponse>(await fetch(`${API_BASE}/api/v1/quota`, { cache: "no-store" }));
}

export async function fetchHealth() {
  return unwrap<HealthResponse>(await fetch(`${API_BASE}/health`, { cache: "no-store" }));
}

export async function fetchRecentReports(limit = 6) {
  return unwrap<ReportSummary[]>(
    await fetch(`${API_BASE}/api/v1/reports?limit=${limit}`, { cache: "no-store" }),
  );
}

/** Server component helper for the shareable report route. */
export async function fetchReportServerSide(publicId: string): Promise<AnalysisReport | null> {
  try {
    const response = await fetch(`${SERVER_API_BASE}/api/v1/reports/${publicId}`, {
      cache: "no-store",
    });
    if (!response.ok) return null;
    return (await response.json()) as AnalysisReport;
  } catch {
    return null;
  }
}

export function markdownUrl(publicId: string) {
  return `${API_BASE}/api/v1/reports/${publicId}/markdown`;
}
