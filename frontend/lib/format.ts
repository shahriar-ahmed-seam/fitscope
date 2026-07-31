import type { Category, CheckStatus, Coverage } from "./types";

export const COVERAGE_STYLES: Record<Coverage, { chip: string; dot: string; label: string }> = {
  covered: {
    chip: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
    dot: "bg-emerald-400",
    label: "Covered",
  },
  partial: {
    chip: "border-amber-500/30 bg-amber-500/10 text-amber-300",
    dot: "bg-amber-400",
    label: "Partial",
  },
  missing: {
    chip: "border-rose-500/30 bg-rose-500/10 text-rose-300",
    dot: "bg-rose-400",
    label: "Missing",
  },
};

export const STATUS_STYLES: Record<CheckStatus, { chip: string; label: string }> = {
  pass: { chip: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300", label: "Pass" },
  warn: { chip: "border-amber-500/30 bg-amber-500/10 text-amber-300", label: "Fix" },
  fail: { chip: "border-rose-500/30 bg-rose-500/10 text-rose-300", label: "Blocker" },
};

export const CATEGORY_LABELS: Record<Category, string> = {
  must_have: "Must have",
  nice_to_have: "Nice to have",
  responsibility: "Responsibility",
};

export const CATEGORY_STYLES: Record<Category, string> = {
  must_have: "border-sky-500/25 bg-sky-500/10 text-sky-300",
  nice_to_have: "border-violet-500/25 bg-violet-500/10 text-violet-300",
  responsibility: "border-slate-500/25 bg-slate-500/10 text-slate-300",
};

export function scoreTone(score: number) {
  if (score >= 80) return { text: "text-emerald-300", stroke: "#34d399", bar: "bg-emerald-400" };
  if (score >= 60) return { text: "text-accent", stroke: "#38e8b0", bar: "bg-accent" };
  if (score >= 40) return { text: "text-amber-300", stroke: "#fbbf24", bar: "bg-amber-400" };
  return { text: "text-rose-300", stroke: "#fb7185", bar: "bg-rose-400" };
}

export function formatDuration(ms: number) {
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

export function formatDate(iso: string | null) {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function sectionLabel(section: string | null) {
  if (!section) return "resume";
  if (section === "header") return "header";
  if (section.startsWith("sec_")) return section.slice(4);
  return section;
}
