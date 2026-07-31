"use client";

import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";

import { STATUS_STYLES, scoreTone } from "@/lib/format";
import type { AtsResult } from "@/lib/types";
import { Chip, Meter, SectionHeading } from "@/components/ui/Primitives";

const ICONS = {
  pass: CheckCircle2,
  warn: AlertTriangle,
  fail: XCircle,
} as const;

export function AtsPanel({ ats }: { ats: AtsResult }) {
  const tone = scoreTone(ats.score);

  return (
    <section>
      <SectionHeading
        eyebrow="Document mechanics"
        title="ATS readiness"
        description="Rule-based checks on whether a parser and a 20-second human skim survive this document. Scored independently of your qualifications."
        right={
          <div className="text-right">
            <p className={`font-mono text-2xl font-semibold ${tone.text}`}>
              {ats.score.toFixed(0)}
              <span className="text-sm text-slate-600">/100</span>
            </p>
            <p className="text-xs text-slate-500">{ats.keyword_coverage.toFixed(0)}% keyword coverage</p>
          </div>
        }
      />

      <ul className="grid gap-3 sm:grid-cols-2">
        {ats.checks.map((check) => {
          const style = STATUS_STYLES[check.status];
          const Icon = ICONS[check.status];
          const ratio = (check.points / check.max_points) * 100;
          return (
            <li key={check.id} className="panel-tight p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-2.5">
                  <Icon
                    className={`mt-0.5 h-4 w-4 shrink-0 ${
                      check.status === "pass"
                        ? "text-emerald-400"
                        : check.status === "warn"
                          ? "text-amber-400"
                          : "text-rose-400"
                    }`}
                    aria-hidden="true"
                  />
                  <div>
                    <p className="text-sm font-medium text-slate-100 print-text">{check.label}</p>
                    <p className="mt-1 text-xs leading-relaxed text-slate-400 print-text">
                      {check.detail}
                    </p>
                  </div>
                </div>
                <Chip className={style.chip}>{style.label}</Chip>
              </div>

              {check.fix ? (
                <p className="mt-2.5 rounded-lg bg-white/[0.03] px-3 py-2 text-xs leading-relaxed text-slate-300 print-text">
                  <span className="font-medium text-accent">Fix </span>
                  {check.fix}
                </p>
              ) : null}

              <div className="mt-3 flex items-center gap-3">
                <Meter value={ratio} tone={scoreTone(ratio).bar} />
                <span className="shrink-0 font-mono text-[11px] text-slate-500">
                  {check.points}/{check.max_points}
                </span>
              </div>
            </li>
          );
        })}
      </ul>

      {ats.missing_keywords.length > 0 ? (
        <div className="panel-tight mt-3 p-4">
          <p className="label mb-2">Job terms absent from the resume</p>
          <div className="flex flex-wrap gap-1.5">
            {ats.missing_keywords.map((keyword) => (
              <Chip key={keyword} className="border-rose-500/25 bg-rose-500/[0.07] text-rose-200/90">
                {keyword}
              </Chip>
            ))}
          </div>
          <p className="mt-3 text-xs text-slate-500">
            Only add terms you have genuinely used. Keyword stuffing is easy for a human reviewer to
            spot in the interview.
          </p>
        </div>
      ) : null}
    </section>
  );
}
