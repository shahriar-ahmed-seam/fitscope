"use client";

import { Building2, Clock, FileText, MapPin } from "lucide-react";

import { formatDuration, scoreTone } from "@/lib/format";
import type { AnalysisReport } from "@/lib/types";
import { Meter } from "@/components/ui/Primitives";

import { ScoreDial } from "./ScoreDial";

function CoverageRow({ label, value }: { label: string; value: number }) {
  const tone = scoreTone(value);
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between text-sm">
        <span className="text-slate-400 print-text">{label}</span>
        <span className={`font-mono text-xs ${tone.text}`}>{value.toFixed(0)}%</span>
      </div>
      <Meter value={value} tone={tone.bar} />
    </div>
  );
}

export function ScoreSummary({ report }: { report: AnalysisReport }) {
  const { scores, job } = report;
  const tone = scoreTone(scores.overall);

  return (
    <section className="panel overflow-hidden">
      <div className="grid gap-8 p-6 lg:grid-cols-[auto,1fr] lg:p-8">
        <div className="flex flex-col items-center gap-6 lg:border-r lg:border-white/[0.06] lg:pr-8">
          <ScoreDial score={scores.overall} label="Overall readiness" />
          <div className="flex gap-6">
            <ScoreDial score={scores.semantic_fit} label="Semantic fit" size={92} />
            <ScoreDial score={scores.ats_readiness} label="ATS readiness" size={92} />
          </div>
        </div>

        <div className="flex flex-col justify-between gap-6">
          <div>
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
              {job.role_title ? (
                <span className="inline-flex items-center gap-1.5">
                  <FileText className="h-3.5 w-3.5" />
                  {job.role_title}
                </span>
              ) : null}
              {job.company ? (
                <span className="inline-flex items-center gap-1.5">
                  <Building2 className="h-3.5 w-3.5" />
                  {job.company}
                </span>
              ) : null}
              {job.location ? (
                <span className="inline-flex items-center gap-1.5">
                  <MapPin className="h-3.5 w-3.5" />
                  {job.location}
                </span>
              ) : null}
              <span className="inline-flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5" />
                {formatDuration(report.duration_ms)}
              </span>
            </div>

            <h2 className={`mt-3 text-2xl font-semibold ${tone.text}`}>{scores.verdict}</h2>
            <p className="mt-2 max-w-xl text-sm leading-relaxed text-slate-400 print-text">
              {scores.verdict_detail}
            </p>

            <div className="mt-4 flex flex-wrap gap-2 text-xs">
              <span className="chip border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
                {scores.covered} covered
              </span>
              <span className="chip border-amber-500/30 bg-amber-500/10 text-amber-300">
                {scores.partial} partial
              </span>
              <span className="chip border-rose-500/30 bg-rose-500/10 text-rose-300">
                {scores.missing} missing
              </span>
              {job.seniority ? (
                <span className="chip border-white/10 bg-white/[0.03] text-slate-400">
                  {job.seniority} level
                </span>
              ) : null}
              {job.years_required ? (
                <span className="chip border-white/10 bg-white/[0.03] text-slate-400">
                  asks for {job.years_required}+ yrs
                </span>
              ) : null}
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <CoverageRow label="Must-have coverage" value={scores.must_have_coverage} />
            <CoverageRow label="Responsibilities" value={scores.responsibility_coverage} />
            <CoverageRow label="Nice-to-haves" value={scores.nice_to_have_coverage} />
          </div>
        </div>
      </div>
    </section>
  );
}
